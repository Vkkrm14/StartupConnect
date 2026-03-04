import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme/app_theme.dart';
import 'core/routing/app_router.dart';
import 'data/providers/api_client.dart';
import 'features/messaging/services/messaging_provider.dart';

class TrustGraphApp extends StatefulWidget {
  const TrustGraphApp({super.key});

  @override
  State<TrustGraphApp> createState() => _TrustGraphAppState();
}

class _TrustGraphAppState extends State<TrustGraphApp> {
  late final ApiClient _apiClient;
  late final AppRouter _appRouter;
  late final MessagingProvider _messagingProvider;

  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient();
    _appRouter = AppRouter(_apiClient);
    _messagingProvider = MessagingProvider(_apiClient);
  }

  @override
  void dispose() {
    _messagingProvider.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: _messagingProvider),
      ],
      child: MaterialApp.router(
        title: 'TrustGraph',
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        themeMode: ThemeMode.system,
        routerConfig: _appRouter.router,
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
