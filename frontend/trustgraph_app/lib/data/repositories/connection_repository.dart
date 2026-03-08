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
    double recencyScore = 1.0,
    int interactionCount = 0,
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
          'recency_score': recencyScore,
          'interaction_count': interactionCount,
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
}
