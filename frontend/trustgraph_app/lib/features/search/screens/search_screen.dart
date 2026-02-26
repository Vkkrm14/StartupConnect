import 'package:flutter/material.dart';
import 'dart:async';
import '../../../data/repositories/search_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/user_model.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _searchController = TextEditingController();
  final _searchRepo = SearchRepository(ApiClient());
  
  List<UserModel> _searchResults = [];
  bool _isLoading = false;
  String? _selectedRole;
  String? _selectedDomain;
  Timer? _debounce;

  final List<String> _roles = ['founder', 'investor', 'connector'];
  final List<String> _domains = [
    'fintech',
    'healthtech',
    'edtech',
    'e-commerce',
    'saas',
    'ai-ml',
  ];

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    // Debounce search
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    
    _debounce = Timer(const Duration(milliseconds: 500), () {
      if (query.length >= 2) {
        _performSearch(query);
      } else {
        setState(() {
          _searchResults = [];
        });
      }
    });
  }

  Future<void> _performSearch(String query) async {
    setState(() => _isLoading = true);

    final result = await _searchRepo.searchUsers(
      query: query,
      role: _selectedRole,
      domain: _selectedDomain,
      limit: 20,
    );

    setState(() {
      _searchResults = result.results;
      _isLoading = false;
    });
  }

  void _clearFilters() {
    setState(() {
      _selectedRole = null;
      _selectedDomain = null;
    });
    
    if (_searchController.text.isNotEmpty) {
      _performSearch(_searchController.text);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Search'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilters,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search founders, investors...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchResults = []);
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onChanged: _onSearchChanged,
            ),
          ),

          // Active filters
          if (_selectedRole != null || _selectedDomain != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: Wrap(
                spacing: 8,
                children: [
                  if (_selectedRole != null)
                    Chip(
                      label: Text(_selectedRole!),
                      deleteIcon: const Icon(Icons.close, size: 18),
                      onDeleted: () {
                        setState(() => _selectedRole = null);
                        if (_searchController.text.isNotEmpty) {
                          _performSearch(_searchController.text);
                        }
                      },
                    ),
                  if (_selectedDomain != null)
                    Chip(
                      label: Text(_selectedDomain!),
                      deleteIcon: const Icon(Icons.close, size: 18),
                      onDeleted: () {
                        setState(() => _selectedDomain = null);
                        if (_searchController.text.isNotEmpty) {
                          _performSearch(_searchController.text);
                        }
                      },
                    ),
                  TextButton.icon(
                    onPressed: _clearFilters,
                    icon: const Icon(Icons.close_fullscreen, size: 16),
                    label: const Text('Clear all'),
                  ),
                ],
              ),
            ),

          // Results
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _searchResults.isEmpty
                    ? _buildEmptyState()
                    : ListView.builder(
                        itemCount: _searchResults.length,
                        itemBuilder: (context, index) {
                          return _buildUserCard(_searchResults[index]);
                        },
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    if (_searchController.text.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'Search for people',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Find founders, investors, and connectors',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[500],
                  ),
            ),
          ],
        ),
      );
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'No results found',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Try different keywords or filters',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[500],
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildUserCard(UserModel user) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        leading: CircleAvatar(
          child: Text(user.name[0].toUpperCase()),
        ),
        title: Text(
          user.name,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(user.rolePrimary),
            if (user.domainTags.isNotEmpty) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 4,
                children: user.domainTags.take(3).map((tag) {
                  return Chip(
                    label: Text(tag, style: const TextStyle(fontSize: 10)),
                    padding: EdgeInsets.zero,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  );
                }).toList(),
              ),
            ],
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.star,
              color: _getTrustColor(user.reputationScore),
              size: 20,
            ),
            Text(
              user.reputationScore.toStringAsFixed(1),
              style: TextStyle(
                color: _getTrustColor(user.reputationScore),
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ],
        ),
        onTap: () {
          // Navigate to user profile
          Navigator.of(context).pushNamed('/profile', arguments: user.userId);
        },
      ),
    );
  }

  Color _getTrustColor(double score) {
    if (score >= 0.7) return Colors.green;
    if (score >= 0.4) return Colors.amber;
    return Colors.red;
  }

  void _showFilters() {
    showModalBottomSheet(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
          return Container(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Filters',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 24),
                
                // Role filter
                Text(
                  'Role',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: _roles.map((role) {
                    final isSelected = _selectedRole == role;
                    return FilterChip(
                      label: Text(role),
                      selected: isSelected,
                      onSelected: (selected) {
                        setModalState(() {
                          _selectedRole = selected ? role : null;
                        });
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),
                
                // Domain filter
                Text(
                  'Domain',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: _domains.map((domain) {
                    final isSelected = _selectedDomain == domain;
                    return FilterChip(
                      label: Text(domain),
                      selected: isSelected,
                      onSelected: (selected) {
                        setModalState(() {
                          _selectedDomain = selected ? domain : null;
                        });
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 24),
                
                // Apply button
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () {
                      setState(() {
                        // Filters already set via setModalState
                      });
                      Navigator.pop(context);
                      if (_searchController.text.isNotEmpty) {
                        _performSearch(_searchController.text);
                      }
                    },
                    child: const Text('Apply Filters'),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
