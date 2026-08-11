import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/widgets/app_states.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/forgot_password_placeholder.dart';
import '../screens/chat/chat_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/digilocker/digilocker_status_screen.dart';
import '../screens/digilocker/sync_screen.dart';
import '../screens/documents/document_upload_screen.dart';
import '../screens/documents/documents_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/profile/caste_screen.dart';
import '../screens/profile/change_password_screen.dart';
import '../screens/profile/edit_profile_screen.dart';
import '../screens/profile/income_screen.dart';
import '../screens/profile/land_record_upload_screen.dart';
import '../screens/profile/land_records_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/recommendations/recommendations_screen.dart';
import '../screens/schemes/schemes_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../screens/splash/splash_screen.dart';

class AppRoutes {
  AppRoutes._();

  static const String splash = '/';
  static const String login = '/login';
  static const String register = '/register';
  static const String forgotPassword = '/forgot-password';
  static const String home = '/home';
  static const String profile = '/profile';
  static const String editProfile = '/profile/edit';
  static const String changePassword = '/profile/change-password';
  static const String income = '/profile/income';
  static const String caste = '/profile/caste';
  static const String landRecords = '/profile/land-records';
  static const String landRecordUpload = '/profile/land-records/upload';
  static const String documents = '/documents';
  static const String documentUpload = '/documents/upload';
  static const String digilockerStatus = '/digilocker/status';
  static const String digilockerSync = '/digilocker/sync';
  static const String schemes = '/schemes';
  static const String recommendations = '/recommendations';
  static const String settings = '/settings';
  static const String chat = '/chat';

  static Route<dynamic> generateRoute(RouteSettings routeSettings) {
    switch (routeSettings.name) {
      case splash:
        return MaterialPageRoute(builder: (_) => const SplashScreen(), settings: routeSettings);
      case login:
        return MaterialPageRoute(builder: (_) => const LoginScreen(), settings: routeSettings);
      case register:
        return MaterialPageRoute(builder: (_) => const RegisterScreen(), settings: routeSettings);
      case forgotPassword:
        return MaterialPageRoute(builder: (_) => const ForgotPasswordPlaceholder(), settings: routeSettings);
      case home:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: HomeScreen()), settings: routeSettings);
      case profile:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: ProfileScreen()), settings: routeSettings);
      case editProfile:
        final returnToDashboardAfterSave = routeSettings.arguments == true;
        return MaterialPageRoute(
          builder: (_) => _ProtectedRoute(
            child: EditProfileScreen(returnToDashboardAfterSave: returnToDashboardAfterSave),
          ),
          settings: routeSettings,
        );
      case changePassword:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: ChangePasswordScreen()), settings: routeSettings);
      case income:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: IncomeScreen()), settings: routeSettings);
      case caste:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: CasteScreen()), settings: routeSettings);
      case landRecords:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: LandRecordsScreen()), settings: routeSettings);
      case landRecordUpload:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: LandRecordUploadScreen()), settings: routeSettings);
      case documents:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: DocumentsScreen()), settings: routeSettings);
      case documentUpload:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: DocumentUploadScreen()), settings: routeSettings);
      case digilockerStatus:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: DigiLockerStatusScreen()), settings: routeSettings);
      case digilockerSync:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: SyncScreen()), settings: routeSettings);
      case schemes:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: SchemesScreen()), settings: routeSettings);
      case recommendations:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: RecommendationsScreen()), settings: routeSettings);
      case AppRoutes.settings:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: SettingsScreen()), settings: routeSettings);
      case AppRoutes.chat:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: ChatScreen()), settings: routeSettings);
      default:
        return MaterialPageRoute(builder: (_) => const SplashScreen(), settings: routeSettings);
    }
  }
}

class _ProtectedRoute extends StatelessWidget {
  const _ProtectedRoute({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, authProvider, _) {
        if (authProvider.status == AuthStatus.unknown || authProvider.isBusy) {
          return const Scaffold(body: AppLoadingView(message: 'Checking your session...'));
        }

        if (!authProvider.isAuthenticated) {
          return const LoginScreen();
        }

        return child;
      },
    );
  }
}
