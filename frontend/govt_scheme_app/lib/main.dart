import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/network/api_service.dart';
import 'core/services/storage_service.dart';
import 'core/theme/app_theme.dart';
import 'providers/app_provider.dart';
import 'providers/auth_provider.dart';
import 'providers/india_location_provider.dart';
import 'providers/profile_provider.dart';
import 'repositories/auth_repository.dart';
import 'repositories/india_location_repository.dart';
import 'repositories/profile_repository.dart';
import 'routes/app_routes.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final storageService = await StorageService.create();
  final apiService = ApiService(storageService: storageService);
  final authRepository = AuthRepository(apiService);
  final indiaLocationRepository = IndiaLocationRepository(apiService);
  final profileRepository = ProfileRepository(apiService);

  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: storageService),
        Provider.value(value: apiService),
        Provider.value(value: authRepository),
        Provider.value(value: indiaLocationRepository),
        Provider.value(value: profileRepository),
        ChangeNotifierProvider(create: (_) => AppProvider(authRepository)),
        ChangeNotifierProvider(
          create: (_) => IndiaLocationProvider(indiaLocationRepository),
        ),
        ChangeNotifierProvider(
          create: (_) => AuthProvider(authRepository, profileRepository, storageService),
        ),
        ChangeNotifierProxyProvider<AuthProvider, ProfileProvider>(
          create: (_) => ProfileProvider(profileRepository),
          update: (_, authProvider, profileProvider) {
            final provider = profileProvider ?? ProfileProvider(profileRepository);
            provider.attachAuthProvider(authProvider);
            return provider;
          },
        ),
      ],
      child: const GovtSchemeApp(),
    ),
  );
}

class GovtSchemeApp extends StatelessWidget {
  const GovtSchemeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI-Powered Government Scheme Fulfillment Engine',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      initialRoute: AppRoutes.splash,
      onGenerateRoute: AppRoutes.generateRoute,
    );
  }
}
