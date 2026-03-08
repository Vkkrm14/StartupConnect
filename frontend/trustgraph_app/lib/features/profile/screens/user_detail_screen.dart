import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../../data/repositories/user_repository.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/repositories/connection_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/user_model.dart';
import '../../../features/messaging/services/messaging_provider.dart';

class UserDetailScreen extends StatefulWidget {
  final String userId;

  const UserDetailScreen({super.key, required this.userId});

  @override
  State<UserDetailScreen> createState() => _UserDetailScreenState();
}

class _UserDetailScreenState extends State<UserDetailScreen> {
  final _apiClient = ApiClient();
  late final _userRepository = UserRepository(_apiClient);
  late final _authRepository = AuthRepository(_apiClient);
  late final _connectionRepository = ConnectionRepository(_apiClient);

  UserModel? _user;
  bool _isLoading = true;
  double? _reputationScore;
  String? _currentUserId;

  // Connection state
  bool _isConnected = false;
  bool _isPendingSent = false;      // current user sent a pending request
  bool _isPendingReceived = false;  // target user sent a pending request to us
  bool _isConnectionLoading = false;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    setState(() => _isLoading = true);

    try {
      final currentUser = await _authRepository.getCurrentUser();
      _currentUserId = currentUser?.userId;

      final user = await _userRepository.getUserById(widget.userId);
      final reputation = await _userRepository.getReputationScore(widget.userId);

      // Check connection status
      if (_currentUserId != null && _currentUserId != widget.userId) {
        await _checkConnectionStatus();
      }

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

  Future<void> _checkConnectionStatus() async {
    if (_currentUserId == null) return;
    try {
      // Check if there's a trust edge from current user to this user
      final score = await _connectionRepository.getTrustScore(
        fromUserId: _currentUserId!,
        toUserId: widget.userId,
      );
      if (score != null) {
        setState(() => _isConnected = true);
        return;
      }
    } catch (_) {}

    try {
      // Check if we have a pending request to them (by checking connections list)
      final connections = await _userRepository.getConnections(_currentUserId!);
      final isInConnections = connections.any((c) => c.userId == widget.userId);
      if (isInConnections) {
        setState(() => _isConnected = true);
      }
    } catch (_) {}
  }

  Future<void> _sendConnectionRequest() async {
    if (_currentUserId == null) return;
    setState(() => _isConnectionLoading = true);
    try {
      await _connectionRepository.sendConnectionRequest(
        fromUserId: _currentUserId!,
        toUserId: widget.userId,
      );
      setState(() {
        _isPendingSent = true;
        _isConnectionLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Connection request sent!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() => _isConnectionLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${ApiClient.getErrorMessage(e)}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _removeConnection() async {
    if (_currentUserId == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove Connection?'),
        content: Text(
            'Remove ${_user?.name ?? 'this user'} from your trust network?'),
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

    setState(() => _isConnectionLoading = true);
    final success = await _connectionRepository.deleteConnection(
      fromUserId: _currentUserId!,
      toUserId: widget.userId,
    );
    setState(() {
      _isConnectionLoading = false;
      if (success) _isConnected = false;
    });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? 'Connection removed' : 'Failed to remove'),
          backgroundColor: success ? null : Colors.red,
        ),
      );
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
                      // Connection button
                      if (_currentUserId != null &&
                          _currentUserId != widget.userId) ...[
                        _buildConnectionButton(),
                        const SizedBox(height: 16),
                      ],

                      Row(
                        children: [
                          // Message button
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () async {
                                try {
                                  final provider = context.read<MessagingProvider>();
                                  if (!provider.isInitialized) {
                                    await provider.initialize();
                                  }
                                  final conversation = await provider
                                      .getOrCreateConversation(widget.userId);
                                  conversation.participantName = _user!.name;
                                  if (mounted) {
                                    context.push(
                                      '/chat/${conversation.conversationId}',
                                      extra: conversation,
                                    );
                                  }
                                } catch (e) {
                                  if (mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Error: $e')),
                                    );
                                  }
                                }
                              },
                              icon: const Icon(Icons.chat_bubble_outline),
                              label: const Text('Message'),
                              style: OutlinedButton.styleFrom(
                                minimumSize: const Size(0, 48),
                                side: BorderSide(
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          // Intro request button
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () {
                                context.push(
                                  '/intro-request/${widget.userId}?name=${Uri.encodeComponent(_user!.name)}&role=${_user!.rolePrimary}',
                                );
                              },
                              icon: const Icon(Icons.handshake),
                              label: const Text('Intro'),
                              style: ElevatedButton.styleFrom(
                                minimumSize: const Size(0, 48),
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

  Widget _buildConnectionButton() {
    if (_isConnectionLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_isConnected) {
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: _removeConnection,
          icon: const Icon(Icons.person_remove, size: 18),
          label: const Text('Disconnect'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 48),
            foregroundColor: Colors.red,
            side: const BorderSide(color: Colors.red),
          ),
        ),
      );
    }

    if (_isPendingSent) {
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: null,
          icon: const Icon(Icons.hourglass_top, size: 18),
          label: const Text('Request Sent'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 48),
            foregroundColor: Colors.orange,
            side: const BorderSide(color: Colors.orange),
          ),
        ),
      );
    }

    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: _sendConnectionRequest,
        icon: const Icon(Icons.person_add, size: 18),
        label: const Text('Connect'),
        style: ElevatedButton.styleFrom(
          minimumSize: const Size(0, 48),
          backgroundColor: Theme.of(context).colorScheme.primary,
          foregroundColor: Colors.white,
        ),
      ),
    );
  }
}
