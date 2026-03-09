import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/repositories/user_repository.dart';
import '../../../data/repositories/connection_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/user_model.dart';
import '../../../data/models/trust_edge_model.dart';

class ConnectionsScreen extends StatefulWidget {
  const ConnectionsScreen({super.key});

  @override
  State<ConnectionsScreen> createState() => _ConnectionsScreenState();
}

class _ConnectionsScreenState extends State<ConnectionsScreen>
    with SingleTickerProviderStateMixin {
  final _apiClient = ApiClient();
  late final _authRepository = AuthRepository(_apiClient);
  late final _userRepository = UserRepository(_apiClient);
  late final _connectionRepository = ConnectionRepository(_apiClient);
  late final TabController _tabController;

  List<UserModel> _connections = [];
  List<UserModel> _filtered = [];
  List<TrustEdgeModel> _pendingRequests = [];
  bool _isLoading = true;
  bool _isPendingLoading = true;
  String? _currentUserId;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.indexIsChanging) return;
      if (_tabController.index == 1 && _isPendingLoading) {
        _loadPendingRequests();
      }
    });
    _loadConnections();
    _searchController.addListener(_applyFilter);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadConnections() async {
    setState(() => _isLoading = true);
    try {
      final user = await _authRepository.getCurrentUser();
      if (user != null) {
        _currentUserId = user.userId;
        final connections = await _userRepository.getConnections(user.userId);
        setState(() {
          _connections = connections;
          _filtered = connections;
          _isLoading = false;
        });
        // Also load pending in background
        _loadPendingRequests();
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
        );
      }
    }
  }

  Future<void> _loadPendingRequests() async {
    if (_currentUserId == null) return;
    setState(() => _isPendingLoading = true);
    try {
      final pending =
          await _connectionRepository.getPendingRequests(_currentUserId!);
      setState(() {
        _pendingRequests = pending;
        _isPendingLoading = false;
      });
    } catch (e) {
      setState(() => _isPendingLoading = false);
    }
  }

  Future<void> _acceptRequest(TrustEdgeModel edge) async {
    final success = await _connectionRepository.acceptConnection(
      fromUserId: edge.fromUserId,
      toUserId: edge.toUserId,
    );
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Connection accepted!'),
          backgroundColor: Colors.green,
        ),
      );
      _loadPendingRequests();
      _loadConnections();
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to accept connection'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _rejectRequest(TrustEdgeModel edge) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reject Connection?'),
        content: const Text(
            'Are you sure you want to reject this connection request?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: TextButton.styleFrom(foregroundColor: Colors.red),
              child: const Text('Reject')),
        ],
      ),
    );
    if (confirmed != true) return;

    final success = await _connectionRepository.rejectConnection(
      fromUserId: edge.fromUserId,
      toUserId: edge.toUserId,
    );
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Connection rejected')),
      );
      _loadPendingRequests();
    }
  }

  Future<void> _removeConnection(UserModel user) async {
    if (_currentUserId == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove Connection?'),
        content: Text(
            'Are you sure you want to remove ${user.name} from your trust network?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: TextButton.styleFrom(foregroundColor: Colors.red),
              child: const Text('Remove')),
        ],
      ),
    );
    if (confirmed != true) return;

    final success = await _connectionRepository.deleteConnection(
      fromUserId: _currentUserId!,
      toUserId: user.userId,
    );
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Removed ${user.name} from connections')),
      );
      _loadConnections();
    }
  }

  void _applyFilter() {
    final q = _searchController.text.toLowerCase();
    setState(() {
      _filtered = q.isEmpty
          ? _connections
          : _connections.where((c) {
              return c.name.toLowerCase().contains(q) ||
                  c.rolePrimary.toLowerCase().contains(q) ||
                  c.domainTags.any((t) => t.toLowerCase().contains(q)) ||
                  (c.geography?.toLowerCase().contains(q) ?? false);
            }).toList();
    });
  }

  Color _scoreColor(double score) {
    if (score >= 0.75) return Colors.green;
    if (score >= 0.5) return Colors.blue;
    if (score >= 0.25) return Colors.orange;
    return Colors.red;
  }

  Color _roleColor(String role) {
    switch (role.toLowerCase()) {
      case 'investor':
        return Colors.purple;
      case 'founder':
        return Colors.blue;
      case 'mentor':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Connections'),
        actions: [
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            const Tab(text: 'Connections'),
            Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Pending'),
                  if (_pendingRequests.isNotEmpty) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '${_pendingRequests.length}',
                        style: const TextStyle(
                            color: Colors.white, fontSize: 11),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 2,
        onDestinationSelected: (index) {
          switch (index) {
            case 0:
              context.go('/home');
              break;
            case 1:
              context.go('/search');
              break;
            case 2:
              break; // already here
            case 3:
              context.go('/messages');
              break;
            case 4:
              context.go('/intros/pending');
              break;
            case 5:
              context.go('/profile');
              break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search),
            label: 'Search',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Connections',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Messages',
          ),
          NavigationDestination(
            icon: Icon(Icons.handshake_outlined),
            selectedIcon: Icon(Icons.handshake),
            label: 'Intros',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Tab 1: My Connections
          _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _buildConnectionsTab(),
          // Tab 2: Pending Requests
          _isPendingLoading
              ? const Center(child: CircularProgressIndicator())
              : _buildPendingTab(),
        ],
      ),
    );
  }

  Widget _buildConnectionsTab() {
    return Column(
      children: [
        // Stats banner
        if (_connections.isNotEmpty)
          Container(
            width: double.infinity,
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Theme.of(context)
                .colorScheme
                .primaryContainer
                .withOpacity(0.4),
            child: Row(
              children: [
                const Icon(Icons.people, size: 20),
                const SizedBox(width: 8),
                Text(
                  '${_connections.length} connection${_connections.length == 1 ? '' : 's'} in your trust network',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        // Search bar
        if (_connections.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search by name, role, domain…',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () => _searchController.clear(),
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 0),
              ),
            ),
          ),
        // List
        Expanded(
          child: _connections.isEmpty
              ? _buildEmpty()
              : _filtered.isEmpty
                  ? Center(
                      child: Text(
                        'No connections match "${_searchController.text}"',
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadConnections,
                      child: ListView.builder(
                        padding:
                            const EdgeInsets.fromLTRB(16, 8, 16, 16),
                        itemCount: _filtered.length,
                        itemBuilder: (context, index) =>
                            _buildConnectionCard(
                                context, _filtered[index]),
                      ),
                    ),
        ),
      ],
    );
  }

  // ── Pending Requests Tab ──

  Widget _buildPendingTab() {
    if (_pendingRequests.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.mark_email_read_outlined,
                size: 72, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'No pending requests',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Connection requests you receive will appear here',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[500],
                  ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadPendingRequests,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        itemCount: _pendingRequests.length,
        itemBuilder: (context, index) =>
            _buildPendingRequestCard(_pendingRequests[index]),
      ),
    );
  }

  Widget _buildPendingRequestCard(TrustEdgeModel edge) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: Colors.blue.withOpacity(0.15),
                  child: const Icon(Icons.person, color: Colors.blue),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        edge.fromUserName ?? edge.fromUserId,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Wants to connect with you',
                        style: TextStyle(
                            fontSize: 12, color: Colors.grey[600]),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'PENDING',
                    style: TextStyle(
                      color: Colors.orange,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),

            // Domain tags
            if (edge.domainTags.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: edge.domainTags.take(4).map(
                  (tag) => Chip(
                    label: Text(tag, style: const TextStyle(fontSize: 10)),
                    visualDensity: VisualDensity.compact,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    padding: EdgeInsets.zero,
                  ),
                ).toList(),
              ),
            ],

            const SizedBox(height: 12),

            // Accept / Reject buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _rejectRequest(edge),
                    icon: const Icon(Icons.close, size: 18),
                    label: const Text('Reject'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _acceptRequest(edge),
                    icon: const Icon(Icons.check, size: 18),
                    label: const Text('Accept'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ── Empty state ──

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.people_outline, size: 72, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'No connections yet',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Build your trust network by requesting introductions',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[500],
                ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => context.push('/search'),
            icon: const Icon(Icons.search),
            label: const Text('Find People'),
          ),
        ],
      ),
    );
  }

  // ── Connection Card (with delete action) ──

  Widget _buildConnectionCard(BuildContext context, UserModel c) {
    final scoreColor = _scoreColor(c.reputationScore);
    final roleColor = _roleColor(c.rolePrimary);

    return Dismissible(
      key: Key(c.userId),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: Colors.red,
          borderRadius: BorderRadius.circular(12),
        ),
        child:
            const Icon(Icons.person_remove, color: Colors.white, size: 28),
      ),
      confirmDismiss: (direction) async {
        return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Remove Connection?'),
            content: Text(
                'Remove ${c.name} from your trust network?'),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: const Text('Cancel')),
              TextButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  style:
                      TextButton.styleFrom(foregroundColor: Colors.red),
                  child: const Text('Remove')),
            ],
          ),
        );
      },
      onDismissed: (direction) => _removeConnection(c),
      child: Card(
        margin: const EdgeInsets.only(bottom: 12),
        elevation: 2,
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => context.push('/user/${c.userId}'),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header row: avatar + name + role badge
                Row(
                  children: [
                    CircleAvatar(
                      radius: 26,
                      backgroundColor: roleColor.withOpacity(0.15),
                      child: Text(
                        c.name[0].toUpperCase(),
                        style: TextStyle(
                          color: roleColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 20,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            c.name,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: roleColor.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  c.rolePrimary.toUpperCase(),
                                  style: TextStyle(
                                    color: roleColor,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              // Mutual badge — all connections returned by
                              // get_connections are bidirectionally accepted.
                              const SizedBox(width: 6),
                              Tooltip(
                                message: 'Mutual connection',
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.green.withOpacity(0.12),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.link,
                                          size: 11,
                                          color: Colors.green[700]),
                                      const SizedBox(width: 3),
                                      Text(
                                        'MUTUAL',
                                        style: TextStyle(
                                          color: Colors.green[700],
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              if (c.geography != null) ...[
                                const SizedBox(width: 8),
                                Icon(Icons.location_on,
                                    size: 13, color: Colors.grey[500]),
                                const SizedBox(width: 2),
                                Text(
                                  c.geography!,
                                  style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey[600]),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                    // Delete button
                    PopupMenuButton<String>(
                      icon: const Icon(Icons.more_vert,
                          size: 18, color: Colors.grey),
                      onSelected: (value) {
                        if (value == 'remove') _removeConnection(c);
                      },
                      itemBuilder: (ctx) => [
                        const PopupMenuItem(
                          value: 'remove',
                          child: Row(
                            children: [
                              Icon(Icons.person_remove,
                                  size: 18, color: Colors.red),
                              SizedBox(width: 8),
                              Text('Remove',
                                  style: TextStyle(color: Colors.red)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),

                // Bio
                if (c.bio != null && c.bio!.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    c.bio!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[700],
                        ),
                  ),
                ],

                const SizedBox(height: 10),

                // Reputation score bar
                Row(
                  children: [
                    const Icon(Icons.verified_user,
                        size: 14, color: Colors.grey),
                    const SizedBox(width: 6),
                    Text(
                      'Trust Score',
                      style:
                          TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: c.reputationScore,
                          minHeight: 6,
                          backgroundColor: Colors.grey[200],
                          color: scoreColor,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      c.reputationScore.toStringAsFixed(2),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: scoreColor,
                      ),
                    ),
                  ],
                ),

                // Domain tags + experience
                if (c.domainTags.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      ...c.domainTags.take(4).map(
                            (tag) => Chip(
                              label: Text(tag,
                                  style: const TextStyle(fontSize: 10)),
                              visualDensity: VisualDensity.compact,
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              padding: EdgeInsets.zero,
                            ),
                          ),
                      if (c.experienceYears > 0)
                        Chip(
                          label: Text('${c.experienceYears}y exp',
                              style: const TextStyle(fontSize: 10)),
                          visualDensity: VisualDensity.compact,
                          materialTapTargetSize:
                              MaterialTapTargetSize.shrinkWrap,
                          padding: EdgeInsets.zero,
                          avatar:
                              const Icon(Icons.work_outline, size: 12),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
