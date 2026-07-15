import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/widgets/app_buttons.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/digilocker_provider.dart';

class SyncScreen extends StatefulWidget {
  const SyncScreen({super.key});

  @override
  State<SyncScreen> createState() => _SyncScreenState();
}

class _SyncScreenState extends State<SyncScreen> {
  bool _forceRefresh = false;

  Future<void> _sync() async {
    final provider = context.read<DigiLockerProvider>();
    try {
      final result = await provider.sync(forceRefresh: _forceRefresh);
      if (!mounted) {
        return;
      }
      await context.read<DashboardProvider>().refresh();
      if (!mounted) {
        return;
      }
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Records Updated'),
          content: Text(
            'Your latest information has been checked.\n\nDocuments found: ${result.documentsSynced}\nProfile updated: ${result.profileUpdated ? 'Yes' : 'No'}',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppStrings.friendlyError(error))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DigiLockerProvider>(
      builder: (context, provider, _) {
        return Scaffold(
          appBar: AppBar(title: const Text(AppStrings.updateRecords)),
          body: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: ListView(
                padding: const EdgeInsets.all(20),
                shrinkWrap: true,
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Icon(
                            Icons.cloud_sync_rounded,
                            size: 56,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Update your government records',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 20),
                          SwitchListTile(
                            value: _forceRefresh,
                            onChanged: provider.isSyncing
                                ? null
                                : (value) => setState(() => _forceRefresh = value),
                            title: const Text('Check again from the start'),
                            secondary: const Icon(Icons.refresh_rounded),
                          ),
                          const SizedBox(height: 20),
                          PrimaryButton(
                            label: AppStrings.updateRecords,
                            icon: Icons.cloud_download_outlined,
                            isLoading: provider.isSyncing,
                            onPressed: _sync,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
