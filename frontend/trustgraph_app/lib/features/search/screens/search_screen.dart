import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';
import '../../../data/repositories/search_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/user_model.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen>
    with SingleTickerProviderStateMixin {
  final _searchController = TextEditingController();
  late final SearchRepository _searchRepo;
  late final TabController _tabController;

  // All users loaded on init
  List<UserModel> _allUsers = [];
  bool _isLoadingAll = false;
  String? _allUsersError;

  // Search results
  List<UserModel> _searchResults = [];
  bool _isSearching = false;
  bool _searchActive = false;

  Timer? _debounce;
  String? _currentUserId;

  final List<String> _roles = ['founder', 'investor', 'connector'];

  @override
  void initState() {
    super.initState();
    _searchRepo = SearchRepository(ApiClient());
    _tabController = TabController(length: 4, vsync: this);
    _loadAllUsers();

    _searchController.addListener(() {
      final text = _searchController.text.trim();
      if (text.isEmpty) {
        setState(() {
          _searchActive = false;
          _searchResults = [];
        });
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _tabController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _loadAllUsers() async {
    setState(() {
      _isLoadingAll = true;
      _allUsersError = null;
    });
    try {
      _currentUserId ??= await ApiClient().getCurrentUserId();
      final users = await _searchRepo.getAllUsers();
      setState(() {
        _allUsers = users.where((u) => u.userId != _currentUserId).toList();
        _isLoadingAll = false;
      });
    } catch (e) {
      setState(() {
        _allUsersError = e.toString();
        _isLoadingAll = false;
      });
    }
  }

  List<UserModel> _usersForTab(int tabIndex) {
    final List<UserModel> source = _searchActive ? _searchResults : _allUsers;
    if (tabIndex == 0) return source;
    final role = _roles[tabIndex - 1];
    return source.where((u) => u.rolePrimary == role).toList();
  }

  void _onSearchChanged(String query) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      final q = query.trim();
      if (q.length >= 2) {
        _performSearch(q);
      } else if (q.isEmpty) {
        setState(() {
          _searchActive = false;
          _searchResults = [];
          _isSearching = false;
        });
      }
    });
  }

  Future<void> _performSearch(String query) async {
    setState(() {
      _isSearching = true;
      _searchActive = true;
    });

    // Try Elasticsearch first (fuzzy matching, ranking)
    final result = await _searchRepo.searchUsers(query: query, limit: 50);

    List<UserModel> results;
    if (result.results.isNotEmpty) {
      // ES returned results — merge with live reputation scores from _allUsers
      // (ES index may be stale; _allUsers comes from graph-service with live scores)
      final liveScores = {for (final u in _allUsers) u.userId: u.reputationScore};
      results = result.results.map((u) {
        final liveRep = liveScores[u.userId];
        if (liveRep != null) {
          return UserModel(
            userId: u.userId,
            name: u.name,
            email: u.email,
            bio: u.bio,
            rolePrimary: u.rolePrimary,
            rolesSecondary: u.rolesSecondary,
            domainTags: u.domainTags,
            geography: u.geography,
            experienceYears: u.experienceYears,
            reputationScore: liveRep,
            verificationStatus: u.verificationStatus,
            createdAt: u.createdAt,
          );
        }
        return u;
      }).toList();
    } else {
      // ES empty or unavailable — fall back to client-side filter
      final q = query.toLowerCase();
      results = _allUsers.where((user) {
        return user.name.toLowerCase().contains(q) ||
            user.domainTags.any((tag) => tag.toLowerCase().contains(q)) ||
            (user.geography?.toLowerCase().contains(q) ?? false) ||
            user.rolePrimary.toLowerCase().contains(q) ||
            (user.bio?.toLowerCase().contains(q) ?? false);
      }).toList();
    }

    setState(() {
      _searchResults = results.where((u) => u.userId != _currentUserId).toList();
      _isSearching = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('Discover People'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'All'),
            Tab(text: 'Founders'),
            Tab(text: 'Investors'),
            Tab(text: 'Connectors'),
          ],
        ),
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search by name, domain...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {
                            _searchActive = false;
                            _searchResults = [];
                          });
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
              ),
              onChanged: _onSearchChanged,
            ),
          ),

          // Searching progress indicator
          if (_isSearching)
            const LinearProgressIndicator()
          else
            const SizedBox(height: 2),

          // Tab views
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: List.generate(4, (i) => _buildTabContent(i)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabContent(int tabIndex) {
    if (_isLoadingAll && !_searchActive) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_allUsersError != null && !_searchActive) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red[300]),
            const SizedBox(height: 12),
            Text('Failed to load users',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: _loadAllUsers,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final users = _usersForTab(tabIndex);

    if (users.isEmpty) {
      return _buildEmptyState(tabIndex);
    }

    return RefreshIndicator(
      onRefresh: _loadAllUsers,
      child: ListView.builder(
        padding: const EdgeInsets.only(bottom: 16),
        itemCount: users.length,
        itemBuilder: (context, index) => _buildUserCard(users[index]),
      ),
    );
  }

  Widget _buildEmptyState(int tabIndex) {
    if (_searchActive) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 56, color: Colors.grey[400]),
            const SizedBox(height: 12),
            Text('No results found',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(color: Colors.grey[600])),
            const SizedBox(height: 6),
            Text('Try different keywords',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Colors.grey[500])),
          ],
        ),
      );
    }
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.people_outline, size: 56, color: Colors.grey[400]),
          const SizedBox(height: 12),
          Text(
            tabIndex == 0
                ? 'No users found'
                : 'No ${_roles[tabIndex - 1]}s yet',
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  Widget _buildUserCard(UserModel user) {
    final roleColor = _roleColor(user.rolePrimary);
    final roleIcon = _roleIcon(user.rolePrimary);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.push('/user/${user.userId}'),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Avatar
              CircleAvatar(
                radius: 26,
                backgroundColor: roleColor.withOpacity(0.15),
                child: Text(
                  user.name.isNotEmpty ? user.name[0].toUpperCase() : '?',
                  style: TextStyle(
                    color: roleColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 20,
                  ),
                ),
              ),
              const SizedBox(width: 12),

              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Name + verified badge
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            user.name,
                            style: const TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                        ),
                        if (user.verificationStatus == 'verified')
                          const Tooltip(
                            message: 'Verified',
                            child: Icon(Icons.verified,
                                size: 16, color: Colors.blue),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),

                    // Role chip + geography
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: roleColor.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(roleIcon, size: 12, color: roleColor),
                              const SizedBox(width: 4),
                              Text(
                                _capitalize(user.rolePrimary),
                                style: TextStyle(
                                  color: roleColor,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (user.geography != null &&
                            user.geography!.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          Icon(Icons.location_on_outlined,
                              size: 13, color: Colors.grey[500]),
                          const SizedBox(width: 2),
                          Flexible(
                            child: Text(
                              user.geography!,
                              style: TextStyle(
                                  fontSize: 12, color: Colors.grey[600]),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ],
                    ),

                    // Domain tags
                    if (user.domainTags.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 4,
                        runSpacing: 2,
                        children: user.domainTags.take(4).map((tag) {
                          return Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.grey[100],
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: Colors.grey[300]!),
                            ),
                            child: Text(tag,
                                style: TextStyle(
                                    fontSize: 10, color: Colors.grey[700])),
                          );
                        }).toList(),
                      ),
                    ],
                  ],
                ),
              ),

              // Trust score badge
              const SizedBox(width: 8),
              Column(
                children: [
                  Icon(Icons.shield_outlined,
                      color: _trustColor(user.reputationScore), size: 20),
                  const SizedBox(height: 2),
                  Text(
                    user.reputationScore > 0
                        ? user.reputationScore.toStringAsFixed(2)
                        : '—',
                    style: TextStyle(
                      color: _trustColor(user.reputationScore),
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _roleColor(String role) {
    switch (role) {
      case 'founder':
        return Colors.indigo;
      case 'investor':
        return Colors.green[700]!;
      case 'connector':
        return Colors.orange[700]!;
      default:
        return Colors.grey;
    }
  }

  IconData _roleIcon(String role) {
    switch (role) {
      case 'founder':
        return Icons.rocket_launch_outlined;
      case 'investor':
        return Icons.trending_up;
      case 'connector':
        return Icons.hub_outlined;
      default:
        return Icons.person_outline;
    }
  }

  Color _trustColor(double score) {
    if (score == 0.0) return Colors.grey[400]!;
    if (score >= 0.75) return Colors.green[700]!;
    if (score >= 0.50) return Colors.blue[600]!;
    if (score >= 0.25) return Colors.orange[600]!;
    return Colors.red[400]!;
  }

  String _capitalize(String s) =>
      s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
}

