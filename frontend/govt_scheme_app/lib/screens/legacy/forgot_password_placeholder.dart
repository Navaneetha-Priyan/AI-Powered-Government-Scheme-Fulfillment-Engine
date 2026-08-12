import 'package:flutter/material.dart';

import '../../core/widgets/app_buttons.dart';
import '../../routes/app_routes.dart';

// LEGACY: password recovery UI is a placeholder because backend lacks recovery API.
// Moved to `screens/legacy` to keep legacy flows separate for cleanup.
class ForgotPasswordPlaceholder extends StatelessWidget {
  const ForgotPasswordPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Forgot Password')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.lock_reset_rounded,
                    size: 56,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Password recovery is not available yet.',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'The backend currently exposes login, registration, profile, and token management only. Add a recovery API later to enable this flow.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 20),
                  PrimaryButton(
                    label: 'Back to login',
                    onPressed: () =>
                        Navigator.of(context).pushNamedAndRemoveUntil(
                      AppRoutes.login,
                      (route) => false,
                    ),
                    icon: Icons.arrow_back_rounded,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
