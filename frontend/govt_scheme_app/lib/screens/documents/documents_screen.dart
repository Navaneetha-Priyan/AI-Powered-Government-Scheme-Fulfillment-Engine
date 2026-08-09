import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../models/citizen_models.dart';
import '../../providers/citizen_provider.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/digilocker_provider.dart';
import '../../routes/app_routes.dart';
import 'document_detail_screen.dart';

/// The single "My Documents" experience.
///
/// Shows DigiLocker connection status, a sync action, the list of government
/// documents, and the citizen's land records (with an upload entry point).
class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  bool _syncSucceeded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final digilocker = context.read<DigiLockerProvider>();
    final citizen = context.read<CitizenProvider>();
    final dashboard = context.read<DashboardProvider>();

    final futures = <Future<void>>[];
    if (digilocker.documents == null) {
      futures.add(
        Future<void>(() async {
          try {
            await digilocker.loadDocuments();
          } catch (_) {}
        }),
      );
    }
    if (digilocker.status == null) {
      futures.add(
        Future<void>(() async {
          try {
            await digilocker.loadStatus();
          } catch (_) {}
        }),
      );
    }
    if (citizen.landRecords == null) {
      futures.add(
        Future<void>(() async {
          try {
            await citizen.loadLandRecords();
          } catch (_) {}
        }),
      );
    }
    if (dashboard.dashboard == null) {
      futures.add(
        Future<void>(() async {
          try {
            await dashboard.loadDashboard();
          } catch (_) {}
        }),
      );
    }
    if (futures.isNotEmpty) {
      await Future.wait(futures);
    }
  }

  Future<void> _refresh() async {
    final digilocker = context.read<DigiLockerProvider>();
    final citizen = context.read<CitizenProvider>();
    final dashboard = context.read<DashboardProvider>();

    await Future.wait<void>([
      digilocker.loadDocuments(),
      digilocker.loadStatus(),
      citizen.loadLandRecords(),
      dashboard.refresh(),
    ]);
  }

  Future<void> _sync() async {
    final provider = context.read<DigiLockerProvider>();
    if (provider.isSyncing) {
      return;
    }

    setState(() => _syncSucceeded = false);
    try {
      await provider.sync();
      if (!mounted) {
        return;
      }
      await context.read<DashboardProvider>().refresh();
      if (!mounted) {
        return;
      }
      setState(() => _syncSucceeded = true);
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
      builder: (context, digilocker, _) {
        final summary = digilocker.documents;
        final status = digilocker.status;

        return Scaffold(
          appBar: AppBar(title: const Text(AppStrings.myDocuments)),
          body: digilocker.isLoading && summary == null
              ? const AppLoadingView(message: AppStrings.loadingDocuments)
              : summary == null
                  ? AppErrorView(
                      message: digilocker.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => digilocker.loadDocuments(),
                    )
                  : RefreshIndicator(
                      onRefresh: _refresh,
                      child: ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(20),
                      children: [
                          _buildDigiLockerSection(context, digilocker, status),
                          const SizedBox(height: 24),
                          _buildUploadSection(context),
                          const SizedBox(height: 24),
                          _buildDocumentsSection(context, summary),
                          const SizedBox(height: 24),
                          _buildLandRecordsSection(context),
                        ],
                      ),
                    ),
        );
      },
    );
  }

  Widget _buildDigiLockerSection(
    BuildContext context,
    DigiLockerProvider provider,
    DigiLockerStatus? status,
  ) {
    final isConnected = status?.isActive ?? false;
    final isSyncing = provider.isSyncing;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('DigiLocker', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  isConnected
                      ? Icons.verified_rounded
                      : Icons.link_off_rounded,
                  color: isConnected
                      ? Theme.of(context).colorScheme.secondary
                      : Theme.of(context).colorScheme.outline,
                ),
                const SizedBox(width: 10),
                Text(
                  isConnected ? 'Connected' : 'Not Connected',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (isSyncing) ...[
              const LinearProgressIndicator(minHeight: 8),
              const SizedBox(height: 12),
              const Text('Syncing your documents...'),
            ] else if (_syncSucceeded) ...[
              _buildSyncSuccess(context),
            ] else ...[
              PrimaryButton(
                label: 'Sync Documents',
                icon: Icons.cloud_sync_rounded,
                onPressed: isSyncing ? null : _sync,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSyncSuccess(BuildContext context) {
    final dashboard = context.watch<DashboardProvider>().dashboard;
    final completion = dashboard?.profileCompletionPercentage;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.check_circle_rounded,
              color: Theme.of(context).colorScheme.secondary,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Documents synced successfully',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Your profile was updated using information from your government documents.',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
        if (completion != null) ...[
          const SizedBox(height: 8),
          Text(
            'Profile completion: $completion%',
            style: Theme.of(context).textTheme.titleSmall,
          ),
        ],
        const SizedBox(height: 16),
        PrimaryButton(
          label: 'View My Profile',
          icon: Icons.person_outline,
          onPressed: () => Navigator.of(context).pushNamed(AppRoutes.profile),
        ),
      ],
    );
  }

  Widget _buildUploadSection(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Upload Government Document',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Upload a government document to update your profile automatically.',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            PrimaryButton(
              label: 'Upload Document',
              icon: Icons.cloud_upload_outlined,
              onPressed: () {
                final provider = context.read<DigiLockerProvider>();
                final citizen = context.read<CitizenProvider>();
                final dashboard = context.read<DashboardProvider>();
                Navigator.of(context).pushNamed(AppRoutes.documentUpload).then(
                  (uploaded) async {
                    if (uploaded == true) {
                      await provider.loadDocuments();
                      await citizen.loadLandRecords();
                      await dashboard.refresh();
                    }
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentsSection(BuildContext context, DocumentSummary summary) {
    final documents = summary.documents;
    final grouped = <String, List<GovernmentDocument>>{};
    for (final document in documents) {
      grouped
          .putIfAbsent(document.documentType, () => <GovernmentDocument>[])
          .add(document);
    }

    final knownTypes = <String, String>{
      'aadhaar': 'Aadhaar',
      'smart_ration_card': 'Smart Ration Card',
      'income_certificate': 'Income Certificate',
      'caste_certificate': 'Caste / Community Certificate',
      'community_certificate': 'Caste / Community Certificate',
      'residence_certificate': 'Residence Certificate',
      'farmer_id': 'Farmer ID',
      'land_record': 'Land Records',
      'disability_certificate': 'Disability Certificate',
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'Documents'),
        const SizedBox(height: 12),
        if (documents.isEmpty)
          EmptyStateView(
            message: 'No documents synced yet.',
            subtitle: 'Sync DigiLocker to access your government documents.',
            icon: Icons.description_outlined,
            actionLabel: 'Sync DigiLocker',
            onAction: _sync,
          )
        else
          ...knownTypes.entries.map((entry) {
            final typeDocs = grouped[entry.key] ?? const <GovernmentDocument>[];
            final label = entry.value;
            final statusLabel = _statusFor(typeDocs);
            final icon = _iconFor(entry.key);
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _DocumentStatusRow(
                label: label,
                status: statusLabel,
                icon: icon,
                onTap: typeDocs.isEmpty
                    ? null
                    : () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => DocumentDetailScreen(
                              documentId: typeDocs.first.id,
                              initialDocument: typeDocs.first,
                            ),
                          ),
                        ),
              ),
            );
          }),
      ],
    );
  }

  String _statusFor(List<GovernmentDocument> docs) {
    if (docs.isEmpty) {
      return 'Not available';
    }
    final statuses = docs.map((d) => d.verificationStatus.toLowerCase()).toSet();
    if (statuses.contains('verified')) {
      return docs.length == 1 ? 'Available' : '${docs.length} documents';
    }
    if (statuses.contains('pending')) {
      return 'Processing';
    }
    if (statuses.contains('missing') ||
        statuses.contains('expired') ||
        statuses.contains('rejected')) {
      return 'Error';
    }
    return 'Available';
  }

  Widget _buildLandRecordsSection(BuildContext context) {
    return Consumer<CitizenProvider>(
      builder: (context, citizen, _) {
        final summary = citizen.landRecords;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionHeader(title: 'Land Records'),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Upload Land Record',
              icon: Icons.cloud_upload_outlined,
              onPressed: () async {
                final uploaded = await Navigator.of(context).pushNamed(
                  AppRoutes.landRecordUpload,
                );
                if (uploaded == true && context.mounted) {
                  await citizen.loadLandRecords();
                }
              },
            ),
            const SizedBox(height: 16),
            if (summary == null)
              const AppLoadingView(message: AppStrings.loadingLand)
            else if (summary.records.isEmpty)
              const Text('No land records yet. Upload one to add it here.')
            else ...[
              Row(
                children: [
                  Expanded(
                    child: DashboardTile(
                      title: 'Total Land',
                      value: AppFormatters.number(summary.totalLandArea),
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
              const SizedBox(height: 16),
              ...summary.records.map(
                (record) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: LandCard(
                    surveyNumber: AppFormatters.displayValue(record.surveyNumber),
                    village: AppFormatters.displayValue(record.village),
                    district: AppFormatters.displayValue(record.district),
                    landType: AppFormatters.titleCase(record.landType),
                    area:
                        '${AppFormatters.number(record.landArea)} ${record.landAreaUnit ?? ''}',
                    ownership: AppFormatters.titleCase(record.ownershipType),
                  ),
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  IconData _iconFor(String type) {
    return switch (type) {
      'aadhaar' => Icons.badge_outlined,
      'smart_ration_card' => Icons.receipt_long_outlined,
      'income_certificate' => Icons.payments_outlined,
      'residence_certificate' => Icons.home_outlined,
      'community_certificate' || 'caste_certificate' => Icons.diversity_3_outlined,
      'farmer_id' => Icons.agriculture_outlined,
      'land_record' => Icons.landscape_outlined,
      'disability_certificate' => Icons.accessible_forward_outlined,
      _ => Icons.description_outlined,
    };
  }
}

class _DocumentStatusRow extends StatelessWidget {
  const _DocumentStatusRow({
    required this.label,
    required this.status,
    required this.icon,
    this.onTap,
  });

  final String label;
  final String status;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isAvailable = status == 'Available' || status.endsWith('documents');
    final statusColor = isAvailable
        ? const Color(0xFF16803C)
        : status == 'Processing'
            ? const Color(0xFF9A6B00)
            : status == 'Error'
                ? const Color(0xFFC62828)
                : Theme.of(context).colorScheme.outline;

    return Card(
      child: Semantics(
        button: onTap != null,
        label: '$label, $status',
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(20),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(icon, size: 30, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                const SizedBox(width: 8),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (isAvailable)
                      Icon(Icons.check_circle_rounded,
                          size: 20, color: statusColor)
                    else
                      Icon(Icons.circle_outlined, size: 20, color: statusColor),
                    const SizedBox(width: 6),
                    Text(
                      status,
                      style: TextStyle(
                        color: statusColor,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}