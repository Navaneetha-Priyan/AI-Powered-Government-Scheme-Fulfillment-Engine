import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../models/citizen_models.dart';
import '../../providers/digilocker_provider.dart';
import '../digilocker/sync_screen.dart';
import 'document_detail_screen.dart';

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<DigiLockerProvider>();
    if (provider.documents == null) {
      try {
        await provider.loadDocuments();
      } catch (_) {}
    }
  }

  Future<void> _refresh() async {
    final provider = context.read<DigiLockerProvider>();
    await provider.loadDocuments();
    if (!mounted) {
      return;
    }
    await provider.loadStatus();
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

  @override
  Widget build(BuildContext context) {
    return Consumer<DigiLockerProvider>(
      builder: (context, provider, _) {
        final summary = provider.documents;
        return Scaffold(
          appBar: AppBar(title: const Text(AppStrings.myDocuments)),
          body: provider.isLoading && summary == null
              ? const AppLoadingView(message: AppStrings.loadingDocuments)
              : summary == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => provider.loadDocuments(),
                    )
                  : RefreshIndicator(
                      onRefresh: _refresh,
                      child: summary.documents.isEmpty
                          ? EmptyStateView(
                              message: 'No documents found',
                              subtitle: 'Update your records to check again.',
                              icon: Icons.description_outlined,
                              actionLabel: AppStrings.updateRecords,
                              onAction: () => Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => const SyncScreen()),
                              ),
                            )
                          : SingleChildScrollView(
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SectionHeader(
                                    title: 'DigiLocker documents',
                                    subtitle: '${summary.documents.length} document${summary.documents.length == 1 ? '' : 's'} found',
                                  ),
                                  const SizedBox(height: 16),
                                  ..._buildGroupedDocuments(context, summary.documents),
                                ],
                              ),
                            ),
                    ),
        );
      },
    );
  }

  List<Widget> _buildGroupedDocuments(BuildContext context, List<GovernmentDocument> documents) {
    final grouped = <String, List<GovernmentDocument>>{};
    for (final document in documents) {
      final type = document.documentType.toString();
      grouped.putIfAbsent(type, () => <GovernmentDocument>[]).add(document);
    }

    return grouped.entries.expand((entry) {
      final docs = entry.value;
      return [
        SectionHeader(
          title: AppFormatters.titleCase(entry.key),
          subtitle: '${docs.length} item${docs.length == 1 ? '' : 's'}',
        ),
        const SizedBox(height: 12),
        ...docs.map((doc) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: DocumentCard(
              name: doc.documentName,
              type: AppFormatters.titleCase(doc.documentType),
              status: AppFormatters.titleCase(doc.verificationStatus),
              issueDate: doc.issueDate == null
                  ? null
                  : AppFormatters.displayDate(doc.issueDate),
              expiryDate: doc.expiryDate == null
                  ? null
                  : AppFormatters.displayDate(doc.expiryDate),
              authority: doc.verifiedBy ?? 'Government records',
              metadata: doc.metadata,
              icon: _iconFor(doc.documentType),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => DocumentDetailScreen(
                    documentId: doc.id,
                    initialDocument: doc,
                  ),
                ),
              ),
            ),
          );
        }),
        const SizedBox(height: 16),
      ];
    }).toList();
  }
}
