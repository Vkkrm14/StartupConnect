import 'package:dio/dio.dart';
import '../providers/api_client.dart';
import '../models/user_model.dart';

/// Authentication Repository
class AuthRepository {
  final ApiClient _apiClient;

  AuthRepository(this._apiClient);

  /// Register new user
  Future<AuthResult> register({
    required String name,
    required String email,
    required String password,
    required String rolePrimary,
    List<String>? domainTags,
    String? geography,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/auth/register',
        data: {
          'name': name,
          'email': email,
          'password': password,
          'role_primary': rolePrimary,
          'domain_tags': domainTags ?? [],
          'geography': geography,
        },
      );

      final data = response.data;
      
      // Save tokens
      await _apiClient.saveTokens(
        accessToken: data['access_token'],
        refreshToken: data['refresh_token'],
        userId: data['user_id'],
      );

      return AuthResult(
        success: true,
        userId: data['user_id'],
        accessToken: data['access_token'],
      );
    } on DioException catch (e) {
      return AuthResult(
        success: false,
        error: ApiClient.getErrorMessage(e),
      );
    } catch (e) {
      return AuthResult(
        success: false,
        error: 'Registration failed: ${e.toString()}',
      );
    }
  }

  /// Login user
  Future<AuthResult> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/auth/login',
        data: {
          'email': email,
          'password': password,
        },
      );

      final data = response.data;
      
      // Save tokens
      await _apiClient.saveTokens(
        accessToken: data['access_token'],
        refreshToken: data['refresh_token'],
        userId: data['user_id'],
      );

      return AuthResult(
        success: true,
        userId: data['user_id'],
        accessToken: data['access_token'],
      );
    } on DioException catch (e) {
      return AuthResult(
        success: false,
        error: ApiClient.getErrorMessage(e),
      );
    } catch (e) {
      return AuthResult(
        success: false,
        error: 'Login failed: ${e.toString()}',
      );
    }
  }

  /// Logout user
  Future<void> logout() async {
    await _apiClient.clearTokens();
  }

  /// Get current user
  Future<UserModel?> getCurrentUser() async {
    try {
      final response = await _apiClient.get('/api/v1/auth/me');
      return UserModel.fromJson(response.data);
    } on DioException catch (e) {
      print('Get current user error: ${ApiClient.getErrorMessage(e)}');
      return null;
    }
  }

  /// Check if user is authenticated
  Future<bool> isAuthenticated() async {
    return await _apiClient.isAuthenticated();
  }

  /// Get current user ID
  Future<String?> getCurrentUserId() async {
    return await _apiClient.getCurrentUserId();
  }

  /// Refresh access token
  Future<bool> refreshToken() async {
    try {
      final refreshToken = await _apiClient.getRefreshToken();
      
      if (refreshToken == null) return false;

      final response = await _apiClient.post(
        '/api/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
      );

      final data = response.data;
      
      await _apiClient.saveTokens(
        accessToken: data['access_token'],
        refreshToken: data['refresh_token'],
        userId: data['user_id'],
      );

      return true;
    } catch (e) {
      return false;
    }
  }
}

/// Authentication result model
class AuthResult {
  final bool success;
  final String? userId;
  final String? accessToken;
  final String? error;

  AuthResult({
    required this.success,
    this.userId,
    this.accessToken,
    this.error,
  });
}
