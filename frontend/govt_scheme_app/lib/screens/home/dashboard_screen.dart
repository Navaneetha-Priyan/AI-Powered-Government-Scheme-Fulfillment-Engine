import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../models/citizen_models.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/digilocker_provider.dart';
import '../../routes/app_routes.dart';
import '../digilocker/sync_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<DashboardProvider>();
    if (provider.dashboard == null) {
      try {
        await provider.loadDashboard();
      } catch (_) {}
    }
  }

  Future<void> _refresh() async {
    if (!mounted) {
      return;
    }

    final provider = context.read<DashboardProvider>();
    if (provider.isLoading) {
      return;
    }

    await provider.refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DashboardProvider>(
      builder: (context, provider, _) {
        final dashboard = provider.dashboard;
        return Scaffold(
          appBar: AppBar(
            title: const Text(AppStrings.myInformation),
            actions: [
              IconButton(
                tooltip: 'Refresh',
                onPressed: provider.isLoading ? null : _refresh,
                icon: const Icon(Icons.refresh_rounded, size: 30),
              ),
            ],
          ),
          body: provider.isLoading && dashboard == null
              ? const AppLoadingView(message: AppStrings.loadingInformation)
              : dashboard == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => provider.loadDashboard(),
                    )
                  : RefreshIndicator(
                      onRefresh: _refresh,
                      child: _DashboardContent(dashboard: dashboard),
                    ),
        );
      },
    );
  }
}

class _DashboardContent extends StatelessWidget {
  const _DashboardContent({required this.dashboard});

  final CitizenDashboard dashboard;

  void _go(BuildContext context, String route) {
    Navigator.of(context).pushNamed(route);
  }

  @override
  Widget build(BuildContext context) {
    final profile = dashboard.extendedProfile;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Hello, ${dashboard.fullName}',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${dashboard.district}, ${dashboard.state}',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Your profile is ${dashboard.profileCompletionPercentage}% complete.',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: LinearProgressIndicator(
                          minHeight: 12,
                          value: dashboard.profileCompletionPercentage / 100,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              const SectionHeader(
                title: 'What do you want to see?',
                subtitle: 'Choose one option.',
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: AppStrings.myProfile,
                subtitle: 'Name, phone, address and family details',
                icon: Icons.person_outline,
                onTap: () => _go(context, AppRoutes.profile),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: AppStrings.myDocuments,
                subtitle: '${dashboard.totalDocuments} documents linked',
                icon: Icons.description_outlined,
                onTap: () => _go(context, AppRoutes.documents),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: AppStrings.myLand,
                subtitle:
                    '${dashboard.landRecords.length} records, ${AppFormatters.number(dashboard.totalLandArea)} total area',
                icon: Icons.agriculture_outlined,
                onTap: () => _go(context, AppRoutes.landRecords),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: AppStrings.incomeDetails,
                subtitle: AppFormatters.money(profile.annualIncome),
                icon: Icons.payments_outlined,
                onTap: () => _go(context, AppRoutes.income),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: 'Community Details',
                subtitle: AppFormatters.titleCase(profile.community),
                icon: Icons.groups_outlined,
                onTap: () => _go(context, AppRoutes.caste),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: 'Discover Schemes',
                subtitle: 'Browse available government schemes',
                icon: Icons.search_rounded,
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.schemes),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: 'Recommended Schemes',
                subtitle: 'AI-powered matches for your profile',
                icon: Icons.auto_awesome_rounded,
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.recommendations),
              ),
              const SizedBox(height: 12),
              ProfileCard(
                title: AppStrings.updateRecords,
                subtitle: dashboard.digilockerSynced
                    ? 'Last updated: ${AppFormatters.displayDate(dashboard.lastSyncedAt)}'
                    : 'Get your latest government records',
                icon: Icons.cloud_sync_outlined,
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SyncScreen()),
                  );
                  if (!context.mounted) {
                    return;
                  }

                  final dashboardProvider = context.read<DashboardProvider>();
                  final digilockerProvider = context.read<DigiLockerProvider>();
                  await dashboardProvider.refresh();
                  await digilockerProvider.loadStatus();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
