import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../data/providers/api_client.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/search/screens/search_screen.dart';
import '../../features/intros/screens/intro_request_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/profile/screens/edit_profile_screen.dart';
import '../../features/profile/screens/user_detail_screen.dart';
import '../../features/profile/screens/connections_screen.dart';
import '../../features/intros/screens/pending_intros_screen.dart';
import '../../features/intros/screens/intro_detail_screen.dart';
import '../../features/intros/screens/my_requests_screen.dart';

class AppRouter {
  final ApiClient apiClient;

  AppRouter(this.apiClient);

  late final GoRouter router = GoRouter(
    initialLocation: '/login',
    redirect: (context, state) async {
      final isAuthenticated = await apiClient.isAuthenticated();
      final isAuthRoute = state.matchedLocation.startsWith('/login') ||
          state.matchedLocation.startsWith('/register');

      // If not authenticated and trying to access protected route
      if (!isAuthenticated && !isAuthRoute) {
        return '/login';
      }

      // If authenticated and trying to access auth route
      if (isAuthenticated && isAuthRoute) {
        return '/home';
      }

      // No redirect needed
      return null;
    },
    routes: [
      // Auth Routes
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        builder: (context, state) => const RegisterScreen(),
      ),

      // Main App Routes (with bottom navigation)
      GoRoute(
        path: '/home',
        name: 'home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/search',
        name: 'search',
        builder: (context, state) => const SearchScreen(),
      ),

      // Profile Routes
      GoRoute(
        path: '/profile',
        name: 'profile',
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/profile/edit',
        name: 'edit-profile',
        builder: (context, state) => const EditProfileScreen(),
      ),
      GoRoute(
        path: '/profile/connections',
        name: 'connections',
        builder: (context, state) => const ConnectionsScreen(),
      ),
      GoRoute(
        path: '/user/:userId',
        name: 'user-detail',
        builder: (context, state) {
          final userId = state.pathParameters['userId']!;
          return UserDetailScreen(userId: userId);
        },
      ),

      // Intro Routes
      GoRoute(
        path: '/intro-request/:targetUserId',
        name: 'intro-request',
        builder: (context, state) {
          final targetUserId = state.pathParameters['targetUserId']!;
          final targetUserName = state.uri.queryParameters['name'] ?? 'User';
          return IntroRequestScreen(
            targetUserId: targetUserId,
            targetUserName: targetUserName,
          );
        },
      ),
      GoRoute(
        path: '/intros/pending',
        name: 'pending-intros',
        builder: (context, state) => const PendingIntrosScreen(),
      ),
      GoRoute(
        path: '/intros/my-requests',
        name: 'my-requests',
        builder: (context, state) => const MyRequestsScreen(),
      ),
      GoRoute(
        path: '/intro/:introId',
        name: 'intro-detail',
        builder: (context, state) {
          final introId = state.pathParameters['introId']!;
          return IntroDetailScreen(introId: introId);
        },
      ),
    ],

    // Error handling
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text('Error')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              'Page not found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(state.uri.toString()),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go('/home'),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    ),
  );
}
