import 'package:dio/dio.dart';
import '../providers/api_client.dart';
import '../models/trust_edge_model.dart';

/// Repository for managing trust edges (connections between users).
/// Mirrors the backend edge_service endpoints.
class ConnectionRepository {
  final ApiClient _apiClient;

  ConnectionRepository(this._apiClient);

  // ────────────────────────────────────────────
  // Create / Send connection request
  // ────────────────────────────────────────────

  /// Send a trust connection request (creates a TRUSTS edge with status='pending')
  Future<TrustEdgeModel?> sendConnectionRequest({
    required String fromUserId,
    required String toUserId,
    double strengthScore = 0.5,
    int endorsementCount = 0,
    List<String> domainTags = const [],
  }) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/edges/trusts',
        data: {
          'from_user_id': fromUserId,
          'to_user_id': toUserId,
          'strength_score': strengthScore,
          'endorsement_count': endorsementCount,
          'domain_tags': domainTags,
        },
      );
      return TrustEdgeModel.fromJson(response.data);
    } on DioException catch (e) {
      print('Send connection request error: ${ApiClient.getErrorMessage(e)}');
      rethrow;
    }
  }

  // ────────────────────────────────────────────
  // Accept / Reject connection requests
  // ────────────────────────────────────────────

  /// Accept a pending connection request
  Future<bool> acceptConnection({
    required String fromUserId,
    required String toUserId,
  }) async {
    try {
      await _apiClient.put(
        '/api/v1/edges/trusts/accept',
        queryParameters: {
          'from_user_id': fromUserId,
          'to_user_id': toUserId,
        },
      );
      return true;
    } on DioException catch (e) {
      print('Accept connection error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  /// Reject a pending connection request
  Future<bool> rejectConnection({
    required String fromUserId,
    required String toUserId,
  }) async {
    try {
      await _apiClient.put(
        '/api/v1/edges/trusts/reject',
        queryParameters: {
          'from_user_id': fromUserId,
          'to_user_id': toUserId,
        },
      );
      return true;
    } on DioException catch (e) {
      print('Reject connection error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  // ────────────────────────────────────────────
  // Get pending requests
  // ────────────────────────────────────────────

  /// Get all pending incoming connection requests for a user
  Future<List<TrustEdgeModel>> getPendingRequests(String userId) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/edges/trusts/pending/$userId',
      );
      final List<dynamic> data = response.data['pending_requests'] ?? [];
      return data.map((json) => TrustEdgeModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Get pending requests error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  /// Get all pending outgoing connection requests sent by a user.
  /// Uses the user trust-edges endpoint filtered to pending + outgoing direction.
  Future<List<TrustEdgeModel>> getOutgoingPendingRequests(String userId) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/edges/trusts/user/$userId',
        queryParameters: {
          'edge_status': 'pending',
          'direction': 'out',
        },
      );
      final List<dynamic> data = response.data['edges'] ?? [];
      return data.map((json) => TrustEdgeModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Get outgoing pending requests error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  // ────────────────────────────────────────────
  // Delete connection
  // ────────────────────────────────────────────

  /// Remove a trust connection between two users
  Future<bool> deleteConnection({
    required String fromUserId,
    required String toUserId,
  }) async {
    try {
      await _apiClient.delete(
        '/api/v1/edges/trusts',
        queryParameters: {
          'from_user_id': fromUserId,
          'to_user_id': toUserId,
        },
      );
      return true;
    } on DioException catch (e) {
      print('Delete connection error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  // ────────────────────────────────────────────
  // Trust score operations
  // ────────────────────────────────────────────

  /// Get trust score between two users
  Future<Map<String, dynamic>?> getTrustScore({
    required String fromUserId,
    required String toUserId,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/edges/trusts/score/$fromUserId/$toUserId',
      );
      return response.data;
    } on DioException catch (e) {
      print('Get trust score error: ${ApiClient.getErrorMessage(e)}');
      return null;
    }
  }

  /// Check whether two users are mutually connected.
  Future<Map<String, dynamic>?> getConnectionStatus({
    required String fromUserId,
    required String toUserId,
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/edges/trusts/connected/$fromUserId/$toUserId',
      );
      return response.data;
    } on DioException catch (e) {
      print('Get connection status error: ${ApiClient.getErrorMessage(e)}');
      return null;
    }
  }

  /// Increment interaction count (auto-recalculates trust score)
  Future<bool> incrementInteraction({
    required String fromUserId,
    required String toUserId,
  }) async {
    try {
      await _apiClient.post(
        '/api/v1/edges/trusts/increment-interaction',
        queryParameters: {
          'from_user_id': fromUserId,
          'to_user_id': toUserId,
        },
      );
      return true;
    } on DioException catch (e) {
      print('Increment interaction error: ${ApiClient.getErrorMessage(e)}');
      return false;
    }
  }

  // ────────────────────────────────────────────
  // Distrust operations
  // ────────────────────────────────────────────

  /// Get distrust reports filed by a user.
  Future<List<Map<String, dynamic>>> getDistrustsByUser(String userId) async {
    try {
      final response = await _apiClient.get('/api/v1/edges/distrusts/by/$userId');
      final List<dynamic> data = response.data['distrust_reports'] ?? [];
      return data.whereType<Map<String, dynamic>>().toList();
    } on DioException catch (e) {
      print('Get distrusts by user error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  /// Get active distrust reports targeting a user.
  Future<List<Map<String, dynamic>>> getDistrustsForUser(String userId) async {
    try {
      final response = await _apiClient.get('/api/v1/edges/distrusts/for/$userId');
      final List<dynamic> data = response.data['active_distrust_reports'] ?? [];
      return data.whereType<Map<String, dynamic>>().toList();
    } on DioException catch (e) {
      print('Get distrusts for user error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }
}
