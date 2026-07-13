import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/cards.dart';
import '../../providers/app_provider.dart';
import '../../providers/auth_provider.dart';
import '../../routes/app_routes.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer2<AppProvider, AuthProvider>(
      builder: (context, appProvider, authProvider, _) {
        return Scaffold(
          appBar: AppBar(title: const Text('Settings')),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Application settings', style: Theme.of(context).textTheme.headlineSmall),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Backend version', value: appProvider.version ?? 'Unknown', icon: Icons.tag_rounded),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Environment', value: appProvider.backendHealth?.environment ?? 'Unknown', icon: Icons.cloud_rounded),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Signed in as', value: authProvider.currentUser?.email ?? 'Unknown', icon: Icons.email_outlined),
                            const SizedBox(height: 20),
                            const Text(
                              'This frontend only connects to the backend modules that already exist: authentication, profile management, and health/status checks.',
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    PrimaryButton(
                      label: 'Logout',
                      onPressed: () async {
                        await authProvider.logout();
                        if (context.mounted) {
                          Navigator.of(context).pushNamedAndRemoveUntil(AppRoutes.login, (route) => false);
                        }
                      },
                      icon: Icons.logout_rounded,
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
