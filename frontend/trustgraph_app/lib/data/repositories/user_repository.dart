import 'package:dio/dio.dart';
import '../providers/api_client.dart';
import '../models/user_model.dart';
import '../repositories/connection_repository.dart';

/// User Repository
class UserRepository {
  final ApiClient _apiClient;
  late final ConnectionRepository _connectionRepository;

  UserRepository(this._apiClient) {
    _connectionRepository = ConnectionRepository(_apiClient);
  }

  /// Access the connection repository for edge operations
  ConnectionRepository get connections => _connectionRepository;

  /// Get user by ID
  Future<UserModel?> getUserById(String userId) async {
    try {
      final response = await _apiClient.get('/api/v1/users/$userId');
      return UserModel.fromJson(response.data);
    } on DioException catch (e) {
      print('Get user error: ${ApiClient.getErrorMessage(e)}');
      return null;
    }
  }

  /// Update user profile
  Future<bool> updateProfile({
    required String userId,
    String? name,
    String? bio,
    List<String>? domainTags,
    String? geography,
    int? experienceYears,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (name != null) data['name'] = name;
      if (bio != null) data['bio'] = bio;
      if (domainTags != null) data['domain_tags'] = domainTags;
      if (geography != null) data['geography'] = geography;
      if (experienceYears != null) data['experience_years'] = experienceYears;

      await _apiClient.patch('/api/v1/users/$userId', data: data);
      return true;
    } on DioException catch (e) {
      print('Update profile error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Get user connections (trust network)
  Future<List<UserModel>> getConnections(String userId) async {
    try {
      final response = await _apiClient.get('/api/v1/users/$userId/connections');
      final List<dynamic> data = response.data is List
          ? response.data
          : (response.data['connections'] ?? []);
      return data.map((json) => UserModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Get connections error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  /// Create trust edge
  Future<bool> createTrustEdge({
    required String fromUserId,
    required String toUserId,
    required double trustScore,
    double strengthScore = 0.5,
  }) async {
    try {
      await _apiClient.post(
        '/api/v1/trusts',
        data: {
          'from_user_id': fromUserId,
          'to_user_id': toUserId,
          'trust_score': trustScore,
          'strength_score': strengthScore,
        },
      );
      return true;
    } on DioException catch (e) {
      print('Create trust error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Update trust score
  Future<bool> updateTrustScore({
    required String fromUserId,
    required String toUserId,
    required double trustScore,
  }) async {
    try {
      await _apiClient.patch(
        '/api/v1/trusts/$fromUserId/$toUserId',
        data: {'trust_score': trustScore},
      );
      return true;
    } on DioException catch (e) {
      print('Update trust error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Get user's reputation score
  Future<double> getReputationScore(String userId) async {
    try {
      final user = await getUserById(userId);
      return user?.reputationScore ?? 0.5;
    } catch (e) {
      return 0.5;
    }
  }
}
