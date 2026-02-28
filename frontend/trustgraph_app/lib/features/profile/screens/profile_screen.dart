import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/repositories/user_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/user_model.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _apiClient = ApiClient();
  late final _authRepository = AuthRepository(_apiClient);
  late final _userRepository = UserRepository(_apiClient);

  UserModel? _currentUser;
  bool _isLoading = true;
  Map<String, dynamic>? _stats;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() => _isLoading = true);

    try {
      final user = await _authRepository.getCurrentUser();
      if (user != null) {
        final connections = await _userRepository.getConnections(user.userId);
        final reputationScore = await _userRepository.getReputationScore(user.userId);

        setState(() {
          _currentUser = user;
          _stats = {
            'connections': connections.length,
            'reputation': reputationScore,
          };
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading profile: ${ApiClient.getErrorMessage(e)}')),
        );
      }
    }
  }

  Color _getReputationColor(double score) {
    if (score >= 0.8) return Colors.green;
    if (score >= 0.6) return Colors.amber;
    return Colors.orange;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('My Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () => context.push('/profile/edit'),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await _authRepository.logout();
              if (mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _currentUser == null
              ? const Center(child: Text('Failed to load profile'))
              : RefreshIndicator(
                  onRefresh: _loadProfile,
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Profile Header
                        Center(
                          child: Column(
                            children: [
                              CircleAvatar(
                                radius: 50,
                                backgroundColor: Theme.of(context).colorScheme.primary,
                                child: Text(
                                  _currentUser!.name[0].toUpperCase(),
                                  style: const TextStyle(fontSize: 36, color: Colors.white),
                                ),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                _currentUser!.name,
                                style: Theme.of(context).textTheme.headlineSmall,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                _currentUser!.email ?? 'No email',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      color: Colors.grey[600],
                                    ),
                              ),
                              const SizedBox(height: 8),
                              Chip(
                                label: Text(_currentUser!.rolePrimary.toUpperCase()),
                                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 32),

                        // Stats Cards
                        Row(
                          children: [
                            Expanded(
                              child: _StatCard(
                                icon: Icons.people,
                                label: 'Connections',
                                value: _stats?['connections']?.toString() ?? '0',
                                onTap: () => context.push('/profile/connections'),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: _StatCard(
                                icon: Icons.star,
                                label: 'Reputation',
                                value: (_stats?['reputation'] ?? 0.5).toStringAsFixed(2),
                                color: _getReputationColor(_stats?['reputation'] ?? 0.5),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 32),

                        // Bio Section
                        if (_currentUser!.bio != null) ...[
                          Text(
                            'About',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(_currentUser!.bio!),
                          const SizedBox(height: 24),
                        ],

                        // Domain Tags
                        Text(
                          'Expertise',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _currentUser!.domainTags
                              .map((tag) => Chip(
                                    label: Text(tag),
                                    backgroundColor: Colors.blue[50],
                                  ))
                              .toList(),
                        ),

                        const SizedBox(height: 24),

                        // Geography
                        if (_currentUser!.geography != null) ...[
                          Text(
                            'Location',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Icon(Icons.location_on, size: 20),
                              const SizedBox(width: 8),
                              Text(_currentUser!.geography!),
                            ],
                          ),
                          const SizedBox(height: 24),
                        ],

                        // Action Buttons
                        ElevatedButton.icon(
                          onPressed: () => context.push('/intros/pending'),
                          icon: const Icon(Icons.notifications),
                          label: const Text('Pending Intros'),
                          style: ElevatedButton.styleFrom(
                            minimumSize: const Size(double.infinity, 48),
                          ),
                        ),
                        const SizedBox(height: 12),
                        OutlinedButton.icon(
                          onPressed: () => context.push('/intros/my-requests'),
                          icon: const Icon(Icons.send),
                          label: const Text('My Requests'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(double.infinity, 48),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? color;
  final VoidCallback? onTap;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    this.color,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Icon(icon, size: 32, color: color ?? Theme.of(context).colorScheme.primary),
              const SizedBox(height: 8),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: color,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: Theme.of(context).textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
