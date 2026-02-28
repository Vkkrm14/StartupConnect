import 'package:dio/dio.dart';
import '../providers/api_client.dart';
import '../models/user_model.dart';

/// Search Repository
class SearchRepository {
  final ApiClient _apiClient;

  SearchRepository(this._apiClient);

  /// Search users
  Future<SearchResult<UserModel>> searchUsers({
    required String query,
    String? role,
    String? domain,
    String? geography,
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'q': query,
        'limit': limit,
        'offset': offset,
      };

      if (role != null) queryParams['role'] = role;
      if (domain != null) queryParams['domain'] = domain;
      if (geography != null) queryParams['geography'] = geography;

      // Add current user ID for personalized ranking
      final userId = await _apiClient.getCurrentUserId();
      if (userId != null) {
        queryParams['current_user_id'] = userId;
      }

      final response = await _apiClient.get(
        '/api/v1/search/users',
        queryParameters: queryParams,
      );

      final data = response.data;
      final List<dynamic> results = data['results'] ?? [];
      final users = results.map((json) => UserModel.fromJson(json)).toList();

      return SearchResult(
        query: query,
        total: data['total'] ?? 0,
        results: users,
        offset: offset,
        limit: limit,
      );
    } on DioException catch (e) {
      print('Search users error: ${ApiClient.getErrorMessage(e)}');
      return SearchResult(
        query: query,
        total: 0,
        results: [],
        offset: offset,
        limit: limit,
      );
    }
  }

  /// Search startups
  Future<SearchResult<Map<String, dynamic>>> searchStartups({
    required String query,
    String? stage,
    String? domain,
    String? geography,
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'q': query,
        'limit': limit,
        'offset': offset,
      };

      if (stage != null) queryParams['stage'] = stage;
      if (domain != null) queryParams['domain'] = domain;
      if (geography != null) queryParams['geography'] = geography;

      final response = await _apiClient.get(
        '/api/v1/search/startups',
        queryParameters: queryParams,
      );

      final data = response.data;
      final List<dynamic> results = data['results'] ?? [];

      return SearchResult(
        query: query,
        total: data['total'] ?? 0,
        results: results.cast<Map<String, dynamic>>(),
        offset: offset,
        limit: limit,
      );
    } on DioException catch (e) {
      print('Search startups error: ${ApiClient.getErrorMessage(e)}');
      return SearchResult(
        query: query,
        total: 0,
        results: [],
        offset: offset,
        limit: limit,
      );
    }
  }

  /// Get all users from the graph, optionally filtered by role
  Future<List<UserModel>> getAllUsers({String? role}) async {
    try {
      final queryParams = <String, dynamic>{'limit': 100};
      if (role != null) queryParams['role'] = role;

      final response = await _apiClient.get(
        '/api/v1/users',
        queryParameters: queryParams,
      );

      final List<dynamic> data =
          response.data is List ? response.data : [];
      return data.map((json) => UserModel.fromJson(json)).toList();
    } on DioException catch (e) {
      print('Get all users error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }

  /// Autocomplete suggestions
  Future<List<AutocompleteSuggestion>> autocomplete({
    required String query,
    String type = 'users',
  }) async {
    try {
      if (query.length < 2) return [];

      final response = await _apiClient.get(
        '/api/v1/search/autocomplete',
        queryParameters: {
          'q': query,
          'type': type,
          'limit': 5,
        },
      );

      final List<dynamic> suggestions = response.data['suggestions'] ?? [];
      return suggestions
          .map((json) => AutocompleteSuggestion.fromJson(json))
          .toList();
    } on DioException catch (e) {
      print('Autocomplete error: ${ApiClient.getErrorMessage(e)}');
      return [];
    }
  }
}

/// Generic search result
class SearchResult<T> {
  final String query;
  final int total;
  final List<T> results;
  final int offset;
  final int limit;

  SearchResult({
    required this.query,
    required this.total,
    required this.results,
    required this.offset,
    required this.limit,
  });

  bool get hasMore => (offset + limit) < total;
  int get nextOffset => offset + limit;
}

/// Autocomplete suggestion
class AutocompleteSuggestion {
  final String id;
  final String name;
  final String type;

  AutocompleteSuggestion({
    required this.id,
    required this.name,
    required this.type,
  });

  factory AutocompleteSuggestion.fromJson(Map<String, dynamic> json) {
    return AutocompleteSuggestion(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      type: json['type'] ?? '',
    );
  }
}
