import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/cards.dart';
import '../../providers/app_provider.dart';
import '../../providers/auth_provider.dart';
import '../../routes/app_routes.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key, this.showBackButton = true});

  final bool showBackButton;

  @override
  Widget build(BuildContext context) {
    return Consumer2<AppProvider, AuthProvider>(
      builder: (context, appProvider, authProvider, _) {
        return Scaffold(
          appBar: AppBar(
            title: const Text(AppStrings.settings),
            automaticallyImplyLeading: showBackButton,
          ),
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
                            Text('App Settings', style: Theme.of(context).textTheme.headlineSmall),
                            const SizedBox(height: 12),
                            const InfoCard(label: 'App version', value: '1.0.0+1', icon: Icons.apps_rounded),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Service version', value: appProvider.version ?? 'Unknown', icon: Icons.tag_rounded),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Service status', value: appProvider.backendHealth?.status ?? 'Unavailable', icon: Icons.favorite_rounded),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Environment', value: appProvider.backendHealth?.environment ?? 'Unknown', icon: Icons.cloud_rounded),
                            const SizedBox(height: 12),
                            InfoCard(label: 'Signed in as', value: authProvider.currentUser?.email ?? 'Unknown', icon: Icons.email_outlined),
                            const SizedBox(height: 20),
                            SwitchListTile(
                              value: appProvider.themeMode == ThemeMode.dark,
                              onChanged: (value) {
                                appProvider.setThemeMode(
                                  value ? ThemeMode.dark : ThemeMode.light,
                                );
                              },
                              title: const Text('Dark theme'),
                              secondary: const Icon(Icons.dark_mode_outlined),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    PrimaryButton(
                      label: 'Sign Out',
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
