import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiConfig {
  // Base URL for API - platform aware
  // Android Emulator: Use 10.0.2.2 to access host machine's 100.70.53.90
  // iOS Simulator: Use 100.70.53.90 (works natively)
  // Chrome/Web: Use 100.70.53.90
  // Windows/Desktop: Use 100.70.53.90
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://100.70.53.90:8000';
    } else if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';  // Android emulator maps to host machine
    } else {
      return 'http://100.70.53.90:8000';
    }
  }
  
  // API endpoints
  static const String apiVersion = '/api/v1';
  
  // User endpoints
  static const String usersEndpoint = '$apiVersion/users';
  
  // Intro endpoints
  static const String introsEndpoint = '$apiVersion/intros';
  static const String pathsEndpoint = '$apiVersion/paths/discover';
  
  // Search endpoints
  static const String searchUsersEndpoint = '$apiVersion/search/users';
  static const String searchStartupsEndpoint = '$apiVersion/search/startups';
  
  // Trust endpoints
  static const String trustsEndpoint = '$apiVersion/trusts';
  
  // Timeout
  static const Duration timeout = Duration(seconds: 30);
}
