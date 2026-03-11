import 'package:dio/dio.dart';
import '../../../../data/providers/api_client.dart';
import '../models/post_model.dart';

class PostRepository {
  final ApiClient _apiClient;

  PostRepository(this._apiClient);

  Future<Map<String, dynamic>> getFeed({
    int page = 1,
    int pageSize = 20,
    String? startupId,
    String? tag,
  }) async {
    try {
      final params = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
      };
      if (startupId != null) params['startup_id'] = startupId;
      if (tag != null) params['tag'] = tag;

      final response = await _apiClient.get(
        '/api/v1/posts/feed',
        queryParameters: params,
      );
      final data = response.data as Map<String, dynamic>;
      final posts = (data['posts'] as List)
          .map((j) => PostModel.fromJson(j as Map<String, dynamic>))
          .toList();
      return {
        'posts': posts,
        'total': data['total'] ?? 0,
        'page': data['page'] ?? page,
        'page_size': data['page_size'] ?? pageSize,
      };
    } on DioException catch (e) {
      print('[PostRepository] getFeed error: $e');
      rethrow;
    }
  }

  Future<PostModel> getPost(String postId) async {
    try {
      final response = await _apiClient.get('/api/v1/posts/$postId');
      return PostModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('[PostRepository] getPost error: $e');
      rethrow;
    }
  }

  Future<PostModel> createPost({
    required String startupId,
    required String title,
    required String body,
    List<String> tags = const [],
    List<String> mediaUrls = const [],
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/posts/',
        data: {
          'startup_id': startupId,
          'title': title,
          'body': body,
          'tags': tags,
          'media_urls': mediaUrls,
        },
      );
      return PostModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('[PostRepository] createPost error: $e');
      rethrow;
    }
  }

  Future<PostModel> updatePost(
    String postId, {
    String? title,
    String? body,
    List<String>? tags,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (title != null) data['title'] = title;
      if (body != null) data['body'] = body;
      if (tags != null) data['tags'] = tags;

      final response = await _apiClient.put(
        '/api/v1/posts/$postId',
        data: data,
      );
      return PostModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      print('[PostRepository] updatePost error: $e');
      rethrow;
    }
  }

  Future<void> deletePost(String postId) async {
    try {
      await _apiClient.delete('/api/v1/posts/$postId');
    } on DioException catch (e) {
      print('[PostRepository] deletePost error: $e');
      rethrow;
    }
  }

  Future<void> likePost(String postId) async {
    try {
      await _apiClient.post('/api/v1/posts/$postId/like');
    } on DioException catch (e) {
      print('[PostRepository] likePost error: $e');
      rethrow;
    }
  }

  Future<void> unlikePost(String postId) async {
    try {
      await _apiClient.delete('/api/v1/posts/$postId/like');
    } on DioException catch (e) {
      print('[PostRepository] unlikePost error: $e');
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> getFoundedStartups() async {
    try {
      final userId = await _apiClient.getCurrentUserId();
      if (userId == null) return [];
      final response =
          await _apiClient.get('/api/v1/users/$userId/startups/founded');
      final list = response.data as List;
      return list.cast<Map<String, dynamic>>();
    } on DioException catch (e) {
      print('[PostRepository] getFoundedStartups error: $e');
      return [];
    }
  }
}
