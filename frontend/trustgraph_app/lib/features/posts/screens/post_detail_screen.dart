import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../../data/providers/api_client.dart';
import '../data/models/post_comment_model.dart';
import '../data/models/post_model.dart';
import '../services/post_provider.dart';
import '../widgets/like_button.dart';

class PostDetailScreen extends StatefulWidget {
  final String postId;
  const PostDetailScreen({super.key, required this.postId});

  @override
  State<PostDetailScreen> createState() => _PostDetailScreenState();
}

class _PostDetailScreenState extends State<PostDetailScreen> {
  final _apiClient = ApiClient();
  final _commentController = TextEditingController();

  PostModel? _post;
  bool _isLoading = true;
  String? _error;

  List<PostCommentModel> _comments = [];
  bool _isCommentsLoading = true;
  bool _isSubmittingComment = false;
  String? _commentsError;
  String? _currentUserId;

  @override
  void initState() {
    super.initState();
    _loadCurrentUser();
    _loadPost();
    _loadComments();
  }

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrentUser() async {
    final userId = await _apiClient.getCurrentUserId();
    if (mounted) {
      setState(() => _currentUserId = userId);
    }
  }

  Future<void> _loadPost() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final provider = context.read<PostProvider>();
      final post = await provider.repository.getPost(widget.postId);
      if (mounted) setState(() => _post = post);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadComments() async {
    if (mounted) {
      setState(() {
        _isCommentsLoading = true;
        _commentsError = null;
      });
    }

    try {
      final provider = context.read<PostProvider>();
      final comments = await provider.repository.getComments(widget.postId);
      if (mounted) {
        setState(() => _comments = comments);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _commentsError = 'Failed to load comments';
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isCommentsLoading = false);
      }
    }
  }

  Future<void> _submitComment() async {
    final body = _commentController.text.trim();
    if (body.isEmpty || _isSubmittingComment) return;

    setState(() => _isSubmittingComment = true);

    try {
      final provider = context.read<PostProvider>();
      final comment = await provider.repository.createComment(
        postId: widget.postId,
        body: body,
      );

      if (!mounted) return;
      setState(() {
        _comments = [comment, ..._comments];
        _post = _post?.copyWith(
          commentCount: (_post?.commentCount ?? 0) + 1,
        );
      });

      _commentController.clear();
      FocusScope.of(context).unfocus();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not add comment: ${ApiClient.getErrorMessage(e)}'),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingComment = false);
      }
    }
  }

  Future<void> _deleteComment(PostCommentModel comment) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Comment'),
        content: const Text('Delete this comment?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm != true || !mounted) return;

    try {
      final provider = context.read<PostProvider>();
      await provider.repository.deleteComment(
        postId: widget.postId,
        commentId: comment.commentId,
      );
      if (!mounted) return;

      setState(() {
        _comments.removeWhere((c) => c.commentId == comment.commentId);
        final currentCount = _post?.commentCount ?? 0;
        _post = _post?.copyWith(
          commentCount: currentCount > 0 ? currentCount - 1 : 0,
        );
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content:
              Text('Could not delete comment: ${ApiClient.getErrorMessage(e)}'),
        ),
      );
    }
  }

  String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inDays > 365) return '${diff.inDays ~/ 365}y ago';
    if (diff.inDays > 30) return '${diff.inDays ~/ 30}mo ago';
    if (diff.inDays > 0) return '${diff.inDays}d ago';
    if (diff.inHours > 0) return '${diff.inHours}h ago';
    if (diff.inMinutes > 0) return '${diff.inMinutes}m ago';
    return 'just now';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Post'),
        actions: [
          if (_post != null)
            LikeButton(
              isLiked: _post!.isLikedByCurrentUser,
              likeCount: _post!.likeCount,
              onToggle: () async {
                final provider = context.read<PostProvider>();
                await provider.toggleLike(_post!.postId);
                _loadPost();
              },
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text(_error!),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadPost,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_post == null) {
      return const Center(child: Text('Post not found'));
    }

    final post = _post!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Startup header
          Row(
            children: [
              CircleAvatar(
                radius: 24,
                child: Text(
                  post.startupName.isNotEmpty
                      ? post.startupName[0].toUpperCase()
                      : 'S',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      post.startupName,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    Text(
                      'by ${post.authorName} • ${_timeAgo(post.createdAt)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Title
          Text(
            post.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),

          const SizedBox(height: 16),

          // Body
          Text(
            post.body,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  height: 1.6,
                ),
          ),

          if (post.tags.isNotEmpty) ...[
            const SizedBox(height: 20),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: post.tags.map((tag) {
                return Chip(
                  label: Text(tag, style: const TextStyle(fontSize: 12)),
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  visualDensity: VisualDensity.compact,
                );
              }).toList(),
            ),
          ],

          const SizedBox(height: 24),

          // Stats
          Row(
            children: [
              Icon(Icons.favorite, size: 18, color: Colors.grey[600]),
              const SizedBox(width: 4),
              Text('${post.likeCount} likes'),
              const SizedBox(width: 16),
              Icon(Icons.comment, size: 18, color: Colors.grey[600]),
              const SizedBox(width: 4),
              Text('${post.commentCount} comments'),
            ],
          ),

          const Divider(height: 32),

          _buildCommentsSection(),
        ],
      ),
    );
  }

  Widget _buildCommentsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Comments',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _commentController,
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _submitComment(),
                decoration: const InputDecoration(
                  hintText: 'Write a comment...',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: 10),
            SizedBox(
              height: 48,
              child: ElevatedButton(
                onPressed: _isSubmittingComment ? null : _submitComment,
                child: _isSubmittingComment
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Post'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_isCommentsLoading)
          const Center(child: CircularProgressIndicator())
        else if (_commentsError != null)
          Center(
            child: Column(
              children: [
                Text(
                  _commentsError!,
                  style: TextStyle(color: Colors.grey[700]),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _loadComments,
                  child: const Text('Retry'),
                ),
              ],
            ),
          )
        else if (_comments.isEmpty)
          Center(
            child: Text(
              'No comments yet. Be the first to comment.',
              style: TextStyle(color: Colors.grey[600]),
            ),
          )
        else
          Column(
            children: _comments.map(_buildCommentTile).toList(),
          ),
      ],
    );
  }

  Widget _buildCommentTile(PostCommentModel comment) {
    final canDelete = _currentUserId != null &&
        comment.authorUserId.isNotEmpty &&
        comment.authorUserId == _currentUserId;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 14,
            child: Text(
              comment.authorName.isNotEmpty
                  ? comment.authorName[0].toUpperCase()
                  : '?',
              style: const TextStyle(fontSize: 12),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        comment.authorName,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                    Text(
                      _timeAgo(comment.createdAt),
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(comment.body),
              ],
            ),
          ),
          if (canDelete)
            IconButton(
              onPressed: () => _deleteComment(comment),
              icon: const Icon(Icons.delete_outline, size: 18),
              color: Colors.red[400],
              tooltip: 'Delete comment',
            ),
        ],
      ),
    );
  }
}
