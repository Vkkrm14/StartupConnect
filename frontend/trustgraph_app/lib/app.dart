import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'core/routing/app_router.dart';
import 'data/providers/api_client.dart';

class TrustGraphApp extends StatefulWidget {
  const TrustGraphApp({super.key});

  @override
  State<TrustGraphApp> createState() => _TrustGraphAppState();
}

class _TrustGraphAppState extends State<TrustGraphApp> {
  late final ApiClient _apiClient;
  late final AppRouter _appRouter;

  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient();
    _appRouter = AppRouter(_apiClient);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'TrustGraph',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      routerConfig: _appRouter.router,
      debugShowCheckedModeBanner: false,
    );
  }
}
