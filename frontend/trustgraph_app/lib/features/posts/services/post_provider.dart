import 'package:flutter/foundation.dart';
import '../data/models/post_model.dart';
import '../data/repositories/post_repository.dart';

class PostProvider extends ChangeNotifier {
  final PostRepository _repository;

  PostProvider(this._repository);

  PostRepository get repository => _repository;

  List<PostModel> _posts = [];
  bool _isLoading = false;
  bool _hasMore = true;
  int _currentPage = 1;
  String? _error;
  String? _activeStartupFilter;
  String? _activeTagFilter;

  List<PostModel> get posts => _posts;
  bool get isLoading => _isLoading;
  bool get hasMore => _hasMore;
  String? get error => _error;
  String? get activeStartupFilter => _activeStartupFilter;
  String? get activeTagFilter => _activeTagFilter;

  void setFilters({String? startupId, String? tag}) {
    _activeStartupFilter = startupId;
    _activeTagFilter = tag;
    notifyListeners();
    loadFeed(refresh: true);
  }

  Future<void> loadFeed({bool refresh = false}) async {
    if (_isLoading) return;

    if (refresh) {
      _currentPage = 1;
      _hasMore = true;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final result = await _repository.getFeed(
        page: _currentPage,
        pageSize: 20,
        startupId: _activeStartupFilter,
        tag: _activeTagFilter,
      );
      final newPosts = result['posts'] as List<PostModel>;
      final total = result['total'] as int;

      if (refresh) {
        _posts = newPosts;
      } else {
        _posts.addAll(newPosts);
      }

      _hasMore = _posts.length < total;
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = 'Failed to load posts: ${e.toString()}';
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadMore() async {
    if (!_hasMore || _isLoading) return;
    _currentPage++;
    await loadFeed();
  }

  Future<bool> createPost({
    required String startupId,
    required String title,
    required String body,
    List<String> tags = const [],
    List<String> mediaUrls = const [],
  }) async {
    try {
      await _repository.createPost(
        startupId: startupId,
        title: title,
        body: body,
        tags: tags,
        mediaUrls: mediaUrls,
      );
      await loadFeed(refresh: true);
      return true;
    } catch (e) {
      _error = 'Failed to create post: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<bool> deletePost(String postId) async {
    try {
      await _repository.deletePost(postId);
      _posts.removeWhere((p) => p.postId == postId);
      notifyListeners();
      return true;
    } catch (e) {
      _error = 'Failed to delete post: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<void> toggleLike(String postId) async {
    final idx = _posts.indexWhere((p) => p.postId == postId);
    if (idx == -1) return;

    final post = _posts[idx];
    final wasLiked = post.isLikedByCurrentUser;

    // Optimistic update
    _posts[idx] = post.copyWith(
      isLikedByCurrentUser: !wasLiked,
      likeCount: wasLiked ? post.likeCount - 1 : post.likeCount + 1,
    );
    notifyListeners();

    try {
      if (wasLiked) {
        await _repository.unlikePost(postId);
      } else {
        await _repository.likePost(postId);
      }
    } catch (e) {
      // Revert on failure
      _posts[idx] = post;
      notifyListeners();
    }
  }
}
