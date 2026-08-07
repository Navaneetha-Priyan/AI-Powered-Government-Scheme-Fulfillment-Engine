import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../providers/digilocker_provider.dart';
import 'sync_screen.dart';

class DigiLockerStatusScreen extends StatefulWidget {
  const DigiLockerStatusScreen({super.key});

  @override
  State<DigiLockerStatusScreen> createState() => _DigiLockerStatusScreenState();
}

class _DigiLockerStatusScreenState extends State<DigiLockerStatusScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<DigiLockerProvider>();
    if (provider.status == null) {
      try {
        await provider.loadStatus();
      } catch (_) {}
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DigiLockerProvider>(
      builder: (context, provider, _) {
        final status = provider.status;
        return Scaffold(
          appBar: AppBar(title: const Text(AppStrings.updateRecords)),
          body: provider.isLoading && status == null
              ? const AppLoadingView(message: AppStrings.loadingInformation)
              : status == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => provider.loadStatus(),
                    )
                  : RefreshIndicator(
                      onRefresh: provider.loadStatus,
                      child: ListView(
                        padding: const EdgeInsets.all(20),
                        children: [
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(
                                    status.isActive
                                        ? Icons.verified_rounded
                                        : Icons.info_outline_rounded,
                                    color: status.isActive
                                        ? Theme.of(context).colorScheme.secondary
                                        : Theme.of(context).colorScheme.primary,
                                    size: 48,
                                  ),
                                  const SizedBox(height: 12),
                                  Text(
                                    status.isActive
                                        ? 'Your records are connected'
                                        : 'Records are not updated yet',
                                    style: Theme.of(context).textTheme.headlineSmall,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Last update: ${AppFormatters.displayDateTime(status.lastSyncAt)}',
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Connection state: ${status.isActive ? 'Connected' : 'Not connected'}',
                                    style: Theme.of(context).textTheme.bodyLarge,
                                  ),
                                  const SizedBox(height: 18),
                                  PrimaryButton(
                                    label: AppStrings.updateRecords,
                                    icon: Icons.cloud_sync_rounded,
                                    onPressed: () => Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => const SyncScreen(),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                          InfoCard(
                            label: 'Documents Found',
                            value: status.totalDocuments.toString(),
                            icon: Icons.folder_copy_outlined,
                          ),
                          const SizedBox(height: 12),
                          InfoCard(
                            label: 'Verified Documents',
                            value: status.verifiedDocuments.toString(),
                            icon: Icons.verified_outlined,
                          ),
                          const SizedBox(height: 12),
                          InfoCard(
                            label: 'Pending Documents',
                            value: status.pendingDocuments.toString(),
                            icon: Icons.pending_actions_outlined,
                          ),
                          const SizedBox(height: 12),
                          InfoCard(
                            label: 'Expired Documents',
                            value: status.expiredDocuments.toString(),
                            icon: Icons.event_busy_outlined,
                          ),
                          const SizedBox(height: 12),
                          InfoCard(
                            label: 'Connection State',
                            value: status.isActive ? 'Connected' : 'Not connected',
                            icon: Icons.link_rounded,
                          ),
                        ],
                      ),
                    ),
        );
      },
    );
  }
}
