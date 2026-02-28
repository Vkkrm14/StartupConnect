import 'package:dio/dio.dart';
import '../providers/api_client.dart';
import '../models/intro_model.dart';
import '../models/path_model.dart';

/// Intro Request Repository
class IntroRepository {
  final ApiClient _apiClient;

  IntroRepository(this._apiClient);

  /// Discover intro paths
  Future<List<PathModel>> discoverPaths({
    required String founderId,
    required String investorId,
    int maxPaths = 5,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/paths/discover',
        data: {
          'founder_id': founderId,
          'investor_id': investorId,
          'max_paths': maxPaths,
        },
      );

      final List<dynamic> pathsData = response.data['paths'] ?? [];
      return pathsData.map((json) => PathModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Discover paths error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  /// Create intro request
  Future<IntroModel?> createIntroRequest({
    required String founderId,
    required String investorId,
    required List<String> pathUserIds,
    String? message,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/intros',
        data: {
          'requester_id': founderId,
          'founder_id': founderId,
          'investor_id': investorId,
          'path_nodes': pathUserIds,
          'message': message ?? '',
        },
      );

      return IntroModel.fromJson(response.data);
    } on DioException catch (e) {
      print('Create intro error: ${ApiClient.getErrorMessage(e)}');
      return null;
    }
  }

  /// Get intro request by ID
  Future<IntroModel?> getIntroRequest(String introId) async {
    try {
      final response = await _apiClient.get('/api/v1/intros/$introId');
      return IntroModel.fromJson(response.data);
    } on DioException catch (e) {
      print('Get intro error: ${ApiClient.getErrorMessage(e)}');
      return null;
    }
  }

  /// Get user's intro requests
  Future<List<IntroModel>> getUserIntroRequests(String userId) async {
    try {
      final response = await _apiClient.get('/api/v1/intros/user/$userId');
      final List<dynamic> data = response.data['intro_requests'] ?? [];
      return data.map((json) => IntroModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Get user intros error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  /// Approve intro request
  Future<bool> approveIntro({
    required String introId,
    required String userId,
    String? message,
  }) async {
    try {
      await _apiClient.post(
        '/api/v1/intros/$introId/approve',
        data: {
          'user_id': userId,
          'action': 'approve',
          'message': message ?? '',
        },
      );
      return true;
    } on DioException catch (e) {
      print('Approve intro error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Decline intro request
  Future<bool> declineIntro({
    required String introId,
    required String userId,
    String? reason,
  }) async {
    try {
      await _apiClient.post(
        '/api/v1/intros/$introId/decline',
        data: {
          'user_id': userId,
          'action': 'decline',
          'message': reason ?? '',
        },
      );
      return true;
    } on DioException catch (e) {
      print('Decline intro error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Mark intro as completed
  Future<bool> completeIntro(String introId) async {
    try {
      await _apiClient.post('/api/v1/intros/$introId/complete');
      return true;
    } on DioException catch (e) {
      print('Complete intro error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Get pending approvals for user
  Future<List<IntroModel>> getPendingApprovals(String userId) async {
    try {
      final response = await _apiClient.get('/api/v1/intros/pending/$userId');
      final List<dynamic> data = response.data['pending_intros'] ?? [];
      return data.map((json) => IntroModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Get pending approvals error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }
}
