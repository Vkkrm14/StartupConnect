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

  // Directional trust scores (only populated when mutually connected)
  double? _myTrustScore;       // current user → target
  double? _theirTrustScore;    // target → current user

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

  Future<void> _loadTrustScores() async {
    if (_currentUserId == null) return;
    try {
      final fwd = await _connectionRepository.getTrustScore(
        fromUserId: _currentUserId!,
        toUserId: widget.userId,
      );
      final rev = await _connectionRepository.getTrustScore(
        fromUserId: widget.userId,
        toUserId: _currentUserId!,
      );
      if (mounted) {
        setState(() {
          _myTrustScore =
              (fwd?['trust_score'] as num?)?.toDouble();
          _theirTrustScore =
              (rev?['trust_score'] as num?)?.toDouble();
        });
      }
    } catch (_) {}
  }

  Future<void> _checkConnectionStatus() async {
    if (_currentUserId == null) return;

    // 1. Check mutual connection via the dedicated bidirectional endpoint.
    try {
      final connection = await _connectionRepository.getConnectionStatus(
        fromUserId: _currentUserId!,
        toUserId: widget.userId,
      );
      if (connection != null && connection['is_connected'] == true) {
        setState(() => _isConnected = true);
        await _loadTrustScores();
        return;
      }
    } catch (_) {}

    // 2. Check whether the target user has sent us a pending request
    //    (so we can show "Accept" instead of "Connect").
    try {
      final pending = await _connectionRepository.getPendingRequests(_currentUserId!);
      final hasIncoming = pending.any((e) => e.fromUserId == widget.userId);
      if (hasIncoming) {
        setState(() => _isPendingReceived = true);
        return;
      }
    } catch (_) {}

    // 3. Check whether we have already sent them a pending request.
    try {
      final ourPending = await _connectionRepository.getOutgoingPendingRequests(_currentUserId!);
      final hasSent = ourPending.any((e) => e.toUserId == widget.userId);
      if (hasSent) {
        setState(() => _isPendingSent = true);
      }
    } catch (_) {}
  }

  Future<void> _sendConnectionRequest() async {
    if (_currentUserId == null) return;
    setState(() => _isConnectionLoading = true);
    try {
      final liveStatus = await _connectionRepository.getConnectionStatus(
        fromUserId: _currentUserId!,
        toUserId: widget.userId,
      );
      if (liveStatus != null && liveStatus['is_connected'] == true) {
        setState(() {
          _isConnected = true;
          _isConnectionLoading = false;
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('You are already connected with this user.'),
            ),
          );
        }
        await _loadTrustScores();
        return;
      }

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

  Future<void> _acceptIncomingRequest() async {
    if (_currentUserId == null) return;
    setState(() => _isConnectionLoading = true);
    try {
      // The edge was sent by widget.userId → _currentUserId
      final success = await _connectionRepository.acceptConnection(
        fromUserId: widget.userId,
        toUserId: _currentUserId!,
      );
      setState(() {
          _isConnectionLoading = false;
          if (success) {
            _isPendingReceived = false;
            _isConnected = true;
          }
        });
        if (success) await _loadTrustScores();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success ? 'Connection accepted!' : 'Failed to accept'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    } catch (e) {
      setState(() => _isConnectionLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
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

                      // Trust scores section — only shown when mutually connected
                      if (_isConnected &&
                          (_myTrustScore != null ||
                              _theirTrustScore != null)) ...[
                        _buildTrustScoresSection(),
                        const SizedBox(height: 16),
                      ],

                      Row(
                        children: [
                          // Message button
                           Expanded(
                             child: OutlinedButton.icon(
                               onPressed: _isConnected
                                   ? () async {
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
                                }
                                   : null,
                               icon: const Icon(Icons.chat_bubble_outline),
                               label: Text(_isConnected ? 'Message' : 'Connect to Message'),
                               style: OutlinedButton.styleFrom(
                                 minimumSize: const Size(0, 48),
                                 side: BorderSide(
                                   color: Theme.of(context).colorScheme.primary,
                                 ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          // Intro request button — only show when NOT connected
                          if (!_isConnected)
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

  Color _getTrustColor(double score) {
    if (score >= 0.7) return Colors.green;
    if (score >= 0.4) return Colors.amber;
    return Colors.red;
  }

  Widget _buildTrustScoresSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.shield_outlined, size: 16),
              const SizedBox(width: 6),
              Text(
                'Directional Trust',
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_myTrustScore != null)
            _buildTrustRow(
              label: 'You trust them',
              score: _myTrustScore!,
            ),
          if (_myTrustScore != null && _theirTrustScore != null)
            const SizedBox(height: 8),
          if (_theirTrustScore != null)
            _buildTrustRow(
              label: 'They trust you',
              score: _theirTrustScore!,
            ),
        ],
      ),
    );
  }

  Widget _buildTrustRow({required String label, required double score}) {
    final color = _getTrustColor(score);
    return Row(
      children: [
        SizedBox(
          width: 120,
          child: Text(
            label,
            style: TextStyle(fontSize: 12, color: Colors.grey[700]),
          ),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: score.clamp(0.0, 1.0),
              minHeight: 6,
              backgroundColor: Colors.grey[200],
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          score.toStringAsFixed(2),
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
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

    // They sent us a request — show Accept button
    if (_isPendingReceived) {
      return SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: _acceptIncomingRequest,
          icon: const Icon(Icons.check_circle_outline, size: 18),
          label: const Text('Accept Request'),
          style: ElevatedButton.styleFrom(
            minimumSize: const Size(0, 48),
            backgroundColor: Colors.green,
            foregroundColor: Colors.white,
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
