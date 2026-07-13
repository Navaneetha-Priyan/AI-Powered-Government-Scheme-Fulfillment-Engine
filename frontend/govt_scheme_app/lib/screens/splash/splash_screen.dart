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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _bootstrap());
  }

  Future<void> _bootstrap() async {
    final appProvider = context.read<AppProvider>();
    final authProvider = context.read<AuthProvider>();

    await appProvider.initialize();
    if (!mounted) {
      return;
    }

    if (!appProvider.backendReachable) {
      setState(() {
        _bootstrapping = false;
      });
      return;
    }

    await authProvider.bootstrap();
    if (!mounted) {
      return;
    }

    final target = authProvider.isAuthenticated ? AppRoutes.home : AppRoutes.login;
    Navigator.of(context).pushReplacementNamed(target);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, _) {
        if (!_bootstrapping && appProvider.errorMessage != null) {
          return Scaffold(
            body: AppErrorView(
              message: appProvider.errorMessage!,
              onRetry: () {
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
                          appProvider.isLoading ? 'Connecting to backend...' : 'Preparing your secure session...',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.88)),
                        ),
                        const SizedBox(height: 28),
                        const CircularProgressIndicator(color: Colors.white),
                        const SizedBox(height: 20),
                        if (appProvider.errorMessage != null)
                          Text(
                            appProvider.errorMessage!,
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
