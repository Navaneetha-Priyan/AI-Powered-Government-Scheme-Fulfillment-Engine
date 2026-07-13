import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/widgets/app_states.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/forgot_password_placeholder.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/profile/change_password_screen.dart';
import '../screens/profile/edit_profile_screen.dart';
import '../screens/profile/profile_screen.dart';
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
  static const String settings = '/settings';

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
      case AppRoutes.settings:
        return MaterialPageRoute(builder: (_) => const _ProtectedRoute(child: SettingsScreen()), settings: routeSettings);
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
