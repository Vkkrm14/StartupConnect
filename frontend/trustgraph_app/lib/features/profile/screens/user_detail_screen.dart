import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/user_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/user_model.dart';

class UserDetailScreen extends StatefulWidget {
  final String userId;

  const UserDetailScreen({super.key, required this.userId});

  @override
  State<UserDetailScreen> createState() => _UserDetailScreenState();
}

class _UserDetailScreenState extends State<UserDetailScreen> {
  final _apiClient = ApiClient();
  late final _userRepository = UserRepository(_apiClient);

  UserModel? _user;
  bool _isLoading = true;
  double? _reputationScore;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    setState(() => _isLoading = true);

    try {
      final user = await _userRepository.getUserById(widget.userId);
      final reputation = await _userRepository.getReputationScore(widget.userId);

      setState(() {
        _user = user;
        _reputationScore = reputation;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
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
        title: const Text('User Profile'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _user == null
              ? const Center(child: Text('User not found'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // User Header
                      Center(
                        child: Column(
                          children: [
                            CircleAvatar(
                              radius: 50,
                              backgroundColor: Theme.of(context).colorScheme.primary,
                              child: Text(
                                _user!.name[0].toUpperCase(),
                                style: const TextStyle(fontSize: 36, color: Colors.white),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              _user!.name,
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Chip(
                              label: Text(_user!.rolePrimary.toUpperCase()),
                              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                            ),
                            if (_reputationScore != null) ...[
                              const SizedBox(height: 12),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                decoration: BoxDecoration(
                                  color: _getReputationColor(_reputationScore!).withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(
                                    color: _getReputationColor(_reputationScore!),
                                    width: 2,
                                  ),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.star,
                                      color: _getReputationColor(_reputationScore!),
                                      size: 20,
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      _reputationScore!.toStringAsFixed(2),
                                      style: TextStyle(
                                        color: _getReputationColor(_reputationScore!),
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),

                      const SizedBox(height: 32),

                      // Bio
                      if (_user!.bio != null) ...[
                        Text(
                          'About',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(_user!.bio!),
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
                        children: _user!.domainTags
                            .map((tag) => Chip(
                                  label: Text(tag),
                                  backgroundColor: Colors.blue[300],
                                ))
                            .toList(),
                      ),

                      const SizedBox(height: 24),

                      // Geography
                      if (_user!.geography != null) ...[
                        Text(
                          'Location',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Icon(Icons.location_on, size: 20),
                            const SizedBox(width: 8),
                            Text(_user!.geography!),
                          ],
                        ),
                        const SizedBox(height: 32),
                      ],

                      // Actions
                      ElevatedButton.icon(
                        onPressed: () {
                          context.push(
                            '/intro-request/${widget.userId}?name=${Uri.encodeComponent(_user!.name)}&role=${_user!.rolePrimary}',
                          );
                        },
                        icon: const Icon(Icons.handshake),
                        label: const Text('Request Introduction'),
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(double.infinity, 48),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}
