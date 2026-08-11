import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../providers/citizen_provider.dart';
import '../../routes/app_routes.dart';

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
                      child: ListView(
                        padding: const EdgeInsets.all(20),
                        children: [
                          PrimaryButton(
                            label: 'Upload Land Record',
                            icon: Icons.cloud_upload_outlined,
                            onPressed: () async {
                              final uploaded = await Navigator.of(context).pushNamed(
                                AppRoutes.landRecordUpload,
                              );
                              if (uploaded == true && context.mounted) {
                                await provider.loadLandRecords();
                              }
                            },
                          ),
                          const SizedBox(height: 20),
                          if (summary.records.isEmpty)
                            EmptyStateView(
                              message: 'No land records found',
                              subtitle: 'Upload a land record to add it here.',
                              icon: Icons.agriculture_outlined,
                              actionLabel: 'Upload Land Record',
                              onAction: () async {
                                final uploaded = await Navigator.of(context).pushNamed(
                                  AppRoutes.landRecordUpload,
                                );
                                if (uploaded == true && context.mounted) {
                                  await provider.loadLandRecords();
                                }
                              },
                            )
                          else ...[
                            Row(
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
                            ),
                            const SizedBox(height: 20),
                            ...summary.records.map(
                              (record) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: LandCard(
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
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
        );
      },
    );
  }
}
