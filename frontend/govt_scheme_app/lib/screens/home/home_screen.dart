import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/cards.dart';
import '../../providers/app_provider.dart';
import '../../providers/auth_provider.dart';
import '../../routes/app_routes.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  void _goTo(BuildContext context, String route) {
    Navigator.of(context).pushNamed(route);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<AuthProvider, AppProvider>(
      builder: (context, authProvider, appProvider, _) {
        final profile = authProvider.currentUser;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Citizen Dashboard'),
            actions: [
              IconButton(
                icon: const Icon(Icons.settings_outlined),
                onPressed: () => _goTo(context, AppRoutes.settings),
              ),
              const SizedBox(width: 4),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () async {
              await appProvider.initialize();
              await authProvider.refreshProfile();
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Card(
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(24),
                            gradient: const LinearGradient(
                              colors: [Color(0xFF0D47A1), Color(0xFF1B8A5A)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                          ),
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Welcome ${profile?.fullName.isNotEmpty == true ? profile!.fullName : 'Citizen'}',
                                style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: Colors.white),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                profile?.email ?? 'Signed in successfully',
                                style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.white.withValues(alpha: 0.92)),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Government Scheme modules will be available in upcoming releases.',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      GridView.count(
                        crossAxisCount: MediaQuery.sizeOf(context).width >= 900 ? 4 : MediaQuery.sizeOf(context).width >= 600 ? 2 : 1,
                        shrinkWrap: true,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                        childAspectRatio: MediaQuery.sizeOf(context).width >= 600 ? 1.9 : 2.8,
                        physics: const NeverScrollableScrollPhysics(),
                        children: [
                          ProfileCard(
                            title: 'View Profile',
                            subtitle: 'Open your citizen details',
                            icon: Icons.person_outline,
                            onTap: () => _goTo(context, AppRoutes.profile),
                          ),
                          ProfileCard(
                            title: 'Edit Profile',
                            subtitle: 'Update your details',
                            icon: Icons.edit_outlined,
                            onTap: () => _goTo(context, AppRoutes.editProfile),
                          ),
                          ProfileCard(
                            title: 'Change Password',
                            subtitle: 'Keep your account secure',
                            icon: Icons.lock_outline,
                            onTap: () => _goTo(context, AppRoutes.changePassword),
                          ),
                          ProfileCard(
                            title: 'Logout',
                            subtitle: 'End your current session',
                            icon: Icons.logout_rounded,
                            onTap: () async {
                              await authProvider.logout();
                              if (context.mounted) {
                                Navigator.of(context).pushNamedAndRemoveUntil(AppRoutes.login, (route) => false);
                              }
                            },
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Backend status', style: Theme.of(context).textTheme.titleLarge),
                              const SizedBox(height: 12),
                              InfoCard(
                                label: 'Health',
                                value: appProvider.backendHealth?.status ?? 'Unavailable',
                                icon: Icons.favorite_rounded,
                              ),
                              const SizedBox(height: 12),
                              InfoCard(
                                label: 'Version',
                                value: appProvider.version ?? 'Unavailable',
                                icon: Icons.tag_rounded,
                              ),
                              const SizedBox(height: 12),
                              InfoCard(
                                label: 'Environment',
                                value: appProvider.backendHealth?.environment ?? appProvider.backendInfo?.environment ?? 'Unknown',
                                icon: Icons.cloud_queue_rounded,
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      if (appProvider.backendInfo != null)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Service information', style: Theme.of(context).textTheme.titleLarge),
                                const SizedBox(height: 12),
                                Text(appProvider.backendInfo!.description),
                                const SizedBox(height: 8),
                                Text('Docs: ${appProvider.backendInfo!.docsUrl}'),
                                Text('OpenAPI: ${appProvider.backendInfo!.openapiUrl}'),
                              ],
                            ),
                          ),
                        ),
                    ],
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
