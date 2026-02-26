import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../data/repositories/intro_repository.dart';
import '../../../data/providers/api_client.dart';
import '../../../data/models/intro_model.dart';

class PendingIntrosScreen extends StatefulWidget {
  const PendingIntrosScreen({super.key});

  @override
  State<PendingIntrosScreen> createState() => _PendingIntrosScreenState();
}

class _PendingIntrosScreenState extends State<PendingIntrosScreen> {
  final _apiClient = ApiClient();
  late final _authRepository = AuthRepository(_apiClient);
  late final _introRepository = IntroRepository(_apiClient);

  List<IntroModel> _pendingIntros = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadPendingIntros();
  }

  Future<void> _loadPendingIntros() async {
    setState(() => _isLoading = true);

    try {
      final user = await _authRepository.getCurrentUser();
      if (user != null) {
        final intros = await _introRepository.getPendingApprovals(user.userId);
        setState(() {
          _pendingIntros = intros;
          _isLoading = false;
        });
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pending Introductions'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _pendingIntros.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.inbox,
                        size: 64,
                        color: Colors.grey[400],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No pending introductions',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: Colors.grey[600],
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Intro requests will appear here',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[500],
                            ),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadPendingIntros,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _pendingIntros.length,
                    itemBuilder: (context, index) {
                      final intro = _pendingIntros[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: () => context.push('/intro/${intro.introId}'),
                          borderRadius: BorderRadius.circular(12),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        'Introduction Request',
                                        style: Theme.of(context).textTheme.titleMedium,
                                      ),
                                    ),
                                    _StatusChip(status: intro.status),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'From: ${intro.requesterId}',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                if (intro.message != null) ...[
                                  const SizedBox(height: 8),
                                  Text(
                                    intro.message!,
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          fontStyle: FontStyle.italic,
                                          color: Colors.grey[600],
                                        ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                                const SizedBox(height: 12),
                                Row(
                                  children: [
                                    Icon(Icons.people, size: 16, color: Colors.grey[600]),
                                    const SizedBox(width: 4),
                                    Text(
                                      '${intro.pathNodes.length} hops',
                                      style: Theme.of(context).textTheme.bodySmall,
                                    ),
                                    const SizedBox(width: 16),
                                    Icon(Icons.access_time, size: 16, color: Colors.grey[600]),
                                    const SizedBox(width: 4),
                                    Text(
                                      _formatDate(intro.createdAt),
                                      style: Theme.of(context).textTheme.bodySmall,
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return '${date.month}/${date.day}/${date.year}';
    }
  }
}

class _StatusChip extends StatelessWidget {
  final String status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color color;
    switch (status.toLowerCase()) {
      case 'pending':
        color = Colors.orange;
        break;
      case 'approved':
        color = Colors.green;
        break;
      case 'declined':
        color = Colors.red;
        break;
      case 'completed':
        color = Colors.blue;
        break;
      default:
        color = Colors.grey;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Text(
        status.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
