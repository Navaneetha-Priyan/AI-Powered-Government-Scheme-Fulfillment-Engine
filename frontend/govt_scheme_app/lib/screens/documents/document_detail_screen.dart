import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../models/citizen_models.dart';
import '../../providers/digilocker_provider.dart';

class DocumentDetailScreen extends StatefulWidget {
  const DocumentDetailScreen({
    super.key,
    required this.documentId,
    this.initialDocument,
  });

  final String documentId;
  final GovernmentDocument? initialDocument;

  @override
  State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends State<DocumentDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    try {
      await context.read<DigiLockerProvider>().loadDocument(widget.documentId);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DigiLockerProvider>(
      builder: (context, provider, _) {
        final doc = provider.selectedDocument?.id == widget.documentId
            ? provider.selectedDocument
            : widget.initialDocument;

        return Scaffold(
          appBar: AppBar(title: const Text('My Document')),
          body: provider.isLoading && doc == null
              ? const AppLoadingView(message: 'Loading your document...')
              : doc == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: _load,
                    )
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        SectionHeader(
                          title: doc.documentName,
                          subtitle: AppFormatters.titleCase(doc.documentType),
                        ),
                        const SizedBox(height: 16),
                        InfoCard(
                          label: 'Document Number',
                          value: AppFormatters.displayValue(doc.documentNumber),
                          icon: Icons.numbers_rounded,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Status',
                          value: AppFormatters.titleCase(doc.verificationStatus),
                          icon: Icons.verified_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Issue Date',
                          value: AppFormatters.displayDate(doc.issueDate),
                          icon: Icons.event_available_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Expiry Date',
                          value: AppFormatters.displayDate(doc.expiryDate),
                          icon: Icons.event_busy_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Verified By',
                          value: AppFormatters.displayValue(doc.verifiedBy),
                          icon: Icons.admin_panel_settings_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Download URL',
                          value: AppFormatters.displayValue(doc.downloadUrl),
                          icon: Icons.link_rounded,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Metadata',
                          value: AppFormatters.displayValue(doc.metadata),
                          icon: Icons.data_object_rounded,
                        ),
                      ],
                    ),
        );
      },
    );
  }
}
