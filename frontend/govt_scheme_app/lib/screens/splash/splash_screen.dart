import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/app_states.dart';
import '../../providers/app_provider.dart';
import '../../providers/auth_provider.dart';
import '../../routes/app_routes.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _bootstrapping = true;
  bool _bootstrapInProgress = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _bootstrap());
  }

  Future<void> _bootstrap() async {
    if (_bootstrapInProgress) {
      return;
    }

    _bootstrapInProgress = true;
    final appProvider = context.read<AppProvider>();
    final authProvider = context.read<AuthProvider>();

    try {
      await appProvider.initialize();
      if (!mounted) {
        return;
      }

      if (!appProvider.backendReachable) {
        if (mounted) {
          setState(() {
            _bootstrapping = false;
          });
        }
        return;
      }

      await authProvider.bootstrap();
      if (!mounted) {
        return;
      }

      if (authProvider.isAuthenticated) {
        if (mounted) {
          Navigator.of(context).pushReplacementNamed(AppRoutes.home);
        }
        return;
      }

      if (authProvider.errorMessage != null) {
        if (mounted) {
          setState(() {
            _bootstrapping = false;
          });
        }
        return;
      }

      if (mounted) {
        Navigator.of(context).pushReplacementNamed(AppRoutes.login);
      }
    } finally {
      if (mounted) {
        setState(() {
          _bootstrapInProgress = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<AppProvider, AuthProvider>(
      builder: (context, appProvider, authProvider, _) {
        final errorMessage = appProvider.errorMessage ?? authProvider.errorMessage;

        if (!_bootstrapping && errorMessage != null) {
          return Scaffold(
            body: AppErrorView(
              message: errorMessage,
              onRetry: () {
                if (_bootstrapInProgress) {
                  return;
                }

                setState(() {
                  _bootstrapping = true;
                });
                _bootstrap();
              },
            ),
          );
        }

        return Scaffold(
          body: Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF0D47A1), Color(0xFF1B8A5A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Card(
                  color: Colors.white.withValues(alpha: 0.12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(32)),
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          height: 76,
                          width: 76,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(24),
                          ),
                          child: const Icon(Icons.verified_user_rounded, color: Colors.white, size: 40),
                        ),
                        const SizedBox(height: 20),
                        const Text(
                          'Government Scheme Fulfillment Engine',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          appProvider.isLoading || authProvider.isBusy
                              ? 'Verifying your secure session...'
                              : 'Preparing your secure session...',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.88)),
                        ),
                        const SizedBox(height: 28),
                        const CircularProgressIndicator(color: Colors.white),
                        const SizedBox(height: 20),
                        if (errorMessage != null)
                          Text(
                            errorMessage,
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.white.withValues(alpha: 0.9)),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
