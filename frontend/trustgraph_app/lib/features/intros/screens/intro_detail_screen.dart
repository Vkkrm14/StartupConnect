import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/intro_repository.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/intro_model.dart';

class IntroDetailScreen extends StatefulWidget {
  final String introId;

  const IntroDetailScreen({super.key, required this.introId});

  @override
  State<IntroDetailScreen> createState() => _IntroDetailScreenState();
}

class _IntroDetailScreenState extends State<IntroDetailScreen> {
  final _apiClient = ApiClient();
  late final _introRepository = IntroRepository(_apiClient);
  late final _authRepository = AuthRepository(_apiClient);

  IntroModel? _intro;
  String? _currentUserId;
  bool _isLoading = true;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      final user = await _authRepository.getCurrentUser();
      final intro = await _introRepository.getIntroRequest(widget.introId);
      setState(() {
        _currentUserId = user?.userId;
        _intro = intro;
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

  Future<void> _approveIntro() async {
    if (_intro == null || _currentUserId == null) return;

    setState(() => _isProcessing = true);

    try {
      await _introRepository.approveIntro(
        introId: widget.introId,
        userId: _currentUserId!,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Introduction approved')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isProcessing = false);
      }
    }
  }

  Future<void> _declineIntro() async {
    if (_intro == null || _currentUserId == null) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Decline Introduction'),
        content: const Text('Are you sure you want to decline this introduction request?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('DECLINE'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() => _isProcessing = true);

    try {
      await _introRepository.declineIntro(
        introId: widget.introId,
        userId: _currentUserId!,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Introduction declined')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${ApiClient.getErrorMessage(e)}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isProcessing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('Introduction Request'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _intro == null
              ? const Center(child: Text('Introduction not found'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Status
                      Center(
                        child: _StatusChip(status: _intro!.status),
                      ),

                      const SizedBox(height: 24),

                      // Introduction Path
                      Text(
                        'Introduction Path',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 16),
                      _buildPathVisualization(),

                      const SizedBox(height: 24),

                      // Message
                      if (_intro!.message.isNotEmpty) ...[
                        Text(
                          'Message',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.grey[100],
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(_intro!.message!),
                        ),
                        const SizedBox(height: 24),
                      ],

                      // Request Details
                      Text(
                        'Details',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      _DetailRow(label: 'Requested', value: _formatDate(_intro!.createdAt)),
                      _DetailRow(label: 'Status', value: _intro!.status.toUpperCase()),
                      _DetailRow(label: 'Hop Count', value: '${_intro!.pathNodes.length}'),

                      const SizedBox(height: 32),

                      // Action Buttons — only show for the node whose turn it is in the chain
                      if ((_intro!.status.toLowerCase() == 'pending') &&
                          _currentUserId != null &&
                          _intro!.currentNodeIndex > 0 &&
                          _intro!.currentNodeIndex < _intro!.pathNodes.length &&
                          _currentUserId == _intro!.pathNodes[_intro!.currentNodeIndex]) ...[
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: _isProcessing ? null : _declineIntro,
                                icon: const Icon(Icons.close),
                                label: const Text('Decline'),
                                style: OutlinedButton.styleFrom(
                                  minimumSize: const Size(0, 48),
                                  foregroundColor: Colors.red,
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: ElevatedButton.icon(
                                onPressed: _isProcessing ? null : _approveIntro,
                                icon: const Icon(Icons.check),
                                label: _isProcessing
                                    ? const SizedBox(
                                        width: 20,
                                        height: 20,
                                        child: CircularProgressIndicator(strokeWidth: 2),
                                      )
                                    : const Text('Approve'),
                                style: ElevatedButton.styleFrom(
                                  minimumSize: const Size(0, 48),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
    );
  }

  Widget _buildPathVisualization() {
    final currentIndex = _intro!.currentNodeIndex;
    final overallStatus = _intro!.status.toLowerCase();

    return Column(
      children: List.generate(_intro!.pathNodes.length, (index) {
        final node = _intro!.pathNodes[index];
        final isLast = index == _intro!.pathNodes.length - 1;
        final displayName = _intro!.pathNodeNames != null && index < _intro!.pathNodeNames!.length
            ? _intro!.pathNodeNames![index]
            : node;

        // Determine node color
        Color nodeColor;
        Color borderColor;
        Color avatarColor;
        IconData? statusIcon;

        if (index == 0) {
          // Requester — always green (they initiated)
          nodeColor = Colors.green.shade400.withOpacity(0.2);
          borderColor = Colors.green;
          avatarColor = Colors.green;
          statusIcon = Icons.check;
        } else if (index < currentIndex) {
          // Already approved
          nodeColor = Colors.green.shade500.withOpacity(0.2);
          borderColor = Colors.green;
          avatarColor = Colors.green;
          statusIcon = Icons.check;
        } else if (index == currentIndex && overallStatus == 'declined') {
          // This node declined
          nodeColor = Colors.red.shade500.withOpacity(0.2);
          borderColor = Colors.red;
          avatarColor = Colors.red;
          statusIcon = Icons.close;
        } else if (index == currentIndex) {
          // Awaiting this node's approval
          nodeColor = Colors.amber.shade500.withOpacity(0.2);
          borderColor = Colors.amber.shade700;
          avatarColor = Colors.amber.shade700;
          statusIcon = Icons.hourglass_empty;
        } else {
          // Future node — not yet reached
          nodeColor = Colors.grey.shade500.withOpacity(0.2);
          borderColor = Colors.grey.shade300;
          avatarColor = Colors.grey;
          statusIcon = null;
        }

        return Column(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: nodeColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: borderColor, width: 2),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    backgroundColor: avatarColor,
                    child: Text(
                      '${index + 1}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      displayName,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: index == currentIndex ? FontWeight.bold : null,
                      ),
                    ),
                  ),
                  if (statusIcon != null)
                    Icon(statusIcon, color: borderColor, size: 20),
                ],
              ),
            ),
            if (!isLast)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Icon(Icons.arrow_downward, color: Colors.grey[400]),
              ),
          ],
        );
      }),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }
}

class _StatusChip extends StatelessWidget {
  final String status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData icon;

    switch (status.toLowerCase()) {
      case 'pending':
        color = Colors.orange;
        icon = Icons.hourglass_empty;
        break;
      case 'approved':
        color = Colors.green;
        icon = Icons.check_circle;
        break;
      case 'declined':
        color = Colors.red;
        icon = Icons.cancel;
        break;
      case 'completed':
        color = Colors.blue;
        icon = Icons.done_all;
        break;
      default:
        color = Colors.grey;
        icon = Icons.info;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color, width: 2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 8),
          Text(
            status.toUpperCase(),
            style: TextStyle(
              color: color,
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
        ],
      ),
    );
  }
}
