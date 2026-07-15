import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../providers/citizen_provider.dart';
import '../digilocker/sync_screen.dart';

class LandRecordsScreen extends StatefulWidget {
  const LandRecordsScreen({super.key});

  @override
  State<LandRecordsScreen> createState() => _LandRecordsScreenState();
}

class _LandRecordsScreenState extends State<LandRecordsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<CitizenProvider>();
    if (provider.landRecords == null) {
      try {
        await provider.loadLandRecords();
      } catch (_) {}
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<CitizenProvider>(
      builder: (context, provider, _) {
        final summary = provider.landRecords;
        return Scaffold(
          appBar: AppBar(title: const Text(AppStrings.myLand)),
          body: provider.isLoading && summary == null
              ? const AppLoadingView(message: AppStrings.loadingLand)
              : summary == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => provider.loadLandRecords(),
                    )
                  : RefreshIndicator(
                      onRefresh: provider.loadLandRecords,
                      child: summary.records.isEmpty
                          ? EmptyStateView(
                              message: 'No land records found',
                              subtitle: 'Update your records to check again.',
                              icon: Icons.agriculture_outlined,
                              actionLabel: AppStrings.updateRecords,
                              onAction: () => Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => const SyncScreen()),
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.all(20),
                              itemCount: summary.records.length + 1,
                              separatorBuilder: (_, __) => const SizedBox(height: 12),
                              itemBuilder: (context, index) {
                                if (index == 0) {
                                  return Row(
                                    children: [
                                      Expanded(
                                        child: DashboardTile(
                                          title: 'Total Land',
                                          value: AppFormatters.number(
                                            summary.totalLandArea,
                                          ),
                                          icon: Icons.square_foot_outlined,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: DashboardTile(
                                          title: 'Land Records',
                                          value: summary.records.length.toString(),
                                          icon: Icons.list_alt_outlined,
                                        ),
                                      ),
                                    ],
                                  );
                                }

                                final record = summary.records[index - 1];
                                return LandCard(
                                  surveyNumber: AppFormatters.displayValue(
                                    record.surveyNumber,
                                  ),
                                  village: AppFormatters.displayValue(record.village),
                                  district: AppFormatters.displayValue(record.district),
                                  landType: AppFormatters.titleCase(record.landType),
                                  area:
                                      '${AppFormatters.number(record.landArea)} ${record.landAreaUnit ?? ''}',
                                  ownership:
                                      AppFormatters.titleCase(record.ownershipType),
                                );
                              },
                            ),
                    ),
        );
      },
    );
  }
}
