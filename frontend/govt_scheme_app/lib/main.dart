import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'core/network/api_service.dart';
import 'core/services/storage_service.dart';
import 'core/services/voice_api_service.dart';
import 'core/services/voice_recorder_service.dart';
import 'core/theme/app_theme.dart';
import 'providers/app_provider.dart';
import 'providers/auth_provider.dart';
import 'providers/citizen_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/digilocker_provider.dart';
import 'providers/eligibility_provider.dart';
import 'providers/india_location_provider.dart';
import 'providers/profile_provider.dart';
import 'providers/recommendation_provider.dart';
import 'providers/scheme_provider.dart';
import 'repositories/auth_repository.dart';
import 'repositories/citizen_repository.dart';
import 'repositories/dashboard_repository.dart';
import 'repositories/digilocker_repository.dart';
import 'repositories/eligibility_repository.dart';
import 'repositories/india_location_repository.dart';
import 'repositories/profile_repository.dart';
import 'repositories/recommendation_repository.dart';
import 'repositories/scheme_repository.dart';
import 'routes/app_routes.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final storageService = await StorageService.create();
  final apiService = ApiService(storageService: storageService);
  final authRepository = AuthRepository(apiService);
  final indiaLocationRepository = IndiaLocationRepository(apiService);
  final profileRepository = ProfileRepository(apiService);
  final citizenRepository = CitizenRepository(apiService);
  final dashboardRepository = DashboardRepository(apiService);
  final digiLockerRepository = DigiLockerRepository(apiService);
  final schemeRepository = SchemeRepository(apiService);
  final eligibilityRepository = EligibilityRepository(apiService);
  final recommendationRepository = RecommendationRepository(apiService);
  final voiceApiService = VoiceApiService(apiService: apiService);

  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: storageService),
        Provider.value(value: apiService),
        Provider.value(value: authRepository),
        Provider.value(value: indiaLocationRepository),
        Provider.value(value: profileRepository),
        Provider.value(value: citizenRepository),
        Provider.value(value: dashboardRepository),
        Provider.value(value: digiLockerRepository),
        Provider.value(value: schemeRepository),
        Provider.value(value: eligibilityRepository),
        Provider.value(value: recommendationRepository),
        Provider.value(value: voiceApiService),
        ChangeNotifierProvider(create: (_) => VoiceRecorderService()),
        ChangeNotifierProvider(create: (_) => AppProvider(authRepository)),
        ChangeNotifierProvider(
          create: (_) => DashboardProvider(dashboardRepository),
        ),
        ChangeNotifierProvider(
          create: (_) => EligibilityProvider(eligibilityRepository),
        ),
        ChangeNotifierProxyProvider<
          EligibilityProvider,
          RecommendationProvider
        >(
          create: (_) => RecommendationProvider(recommendationRepository),
          update: (_, eligibilityProvider, recommendationProvider) {
            final provider =
                recommendationProvider ??
                RecommendationProvider(recommendationRepository);
            eligibilityProvider.onInvalidateAll = provider.invalidateAll;
            return provider;
          },
        ),
        ChangeNotifierProvider(
          create: (context) => CitizenProvider(citizenRepository)
            ..attachEligibilityProvider(context.read<EligibilityProvider>()),
        ),
        ChangeNotifierProvider(
          create: (context) => DigiLockerProvider(digiLockerRepository)
            ..attachEligibilityProvider(context.read<EligibilityProvider>()),
        ),
        ChangeNotifierProvider(create: (_) => SchemeProvider(schemeRepository)),
        ChangeNotifierProvider(
          create: (_) => IndiaLocationProvider(indiaLocationRepository),
        ),
        ChangeNotifierProvider(
          create: (_) =>
              AuthProvider(authRepository, profileRepository, storageService),
        ),
        ChangeNotifierProxyProvider2<
          AuthProvider,
          EligibilityProvider,
          ProfileProvider
        >(
          create: (_) => ProfileProvider(profileRepository),
          update: (_, authProvider, eligibilityProvider, profileProvider) {
            final provider =
                profileProvider ?? ProfileProvider(profileRepository);
            provider.attachAuthProvider(authProvider);
            provider.attachEligibilityProvider(eligibilityProvider);
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
    return Consumer<AppProvider>(
      builder: (context, appProvider, _) {
        return MaterialApp(
          title: 'AI-Powered Government Scheme Fulfillment Engine',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: appProvider.themeMode,
          supportedLocales: const [Locale('en'), Locale('ta'), Locale('hi')],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          initialRoute: AppRoutes.splash,
          onGenerateRoute: AppRoutes.generateRoute,
        );
      },
    );
  }
}
