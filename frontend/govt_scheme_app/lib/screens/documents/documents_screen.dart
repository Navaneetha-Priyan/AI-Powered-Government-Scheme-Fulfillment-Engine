import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/constants/document_types.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_states.dart';
import '../../models/document_intelligence.dart';
import '../../providers/document_intelligence_provider.dart';
import '../../routes/app_routes.dart';

// ─── Document type descriptor ──────────────────────────────────────────────────

class _DocType {
  const _DocType(
    this.id,
    this.name,
    this.description,
    this.icon,
    this.required,
  );
  final String id, name, description;
  final IconData icon;
  final bool required;
}

// ─── Category grouping ─────────────────────────────────────────────────────────

class _Category {
  const _Category(this.label, this.icon, this.types);
  final String label;
  final IconData icon;
  final List<_DocType> types;
}

final _categories = [
  _Category('IDENTITY', Icons.badge_outlined, [
    const _DocType(
      DocumentTypes.aadhaar,
      'Aadhaar Card',
      'Verify your identity and basic details',
      Icons.badge_outlined,
      true,
    ),
    const _DocType(
      DocumentTypes.smartRation,
      'Smart Ration Card',
      'Household and family information',
      Icons.receipt_long_outlined,
      false,
    ),
  ]),
  _Category('FINANCIAL', Icons.currency_rupee_rounded, [
    const _DocType(
      DocumentTypes.incomeCertificate,
      'Income Certificate',
      'Used to determine income-based eligibility',
      Icons.currency_rupee_rounded,
      false,
    ),
  ]),
  _Category('SOCIAL', Icons.groups_outlined, [
    const _DocType(
      DocumentTypes.communityCertificate,
      'Community Certificate',
      'Used for community-specific schemes',
      Icons.groups_outlined,
      false,
    ),
  ]),
  _Category('AGRICULTURE', Icons.landscape_outlined, [
    const _DocType(
      DocumentTypes.landRecord,
      'Land Record',
      'Used for farmer and agricultural schemes',
      Icons.landscape_outlined,
      false,
    ),
    const _DocType(
      DocumentTypes.farmerDocument,
      'Farmer ID',
      'Used for agricultural benefits',
      Icons.agriculture_outlined,
      false,
    ),
  ]),
  _Category('SPECIAL CATEGORY', Icons.accessible_forward_outlined, [
    const _DocType(
      DocumentTypes.disabilityCertificate,
      'Disability Certificate',
      'For applicable support schemes',
      Icons.accessible_forward_outlined,
      false,
    ),
  ]),
  _Category('BANKING', Icons.account_balance_outlined, [
    const _DocType(
      DocumentTypes.bankPassbook,
      'Bank Passbook',
      'Saved with masked account details',
      Icons.account_balance_outlined,
      false,
    ),
  ]),
  _Category('EDUCATION', Icons.school_outlined, [
    const _DocType(
      DocumentTypes.educationCertificate,
      'Education Certificate',
      'For education and employment schemes',
      Icons.school_outlined,
      false,
    ),
  ]),
];

// All document types flattened — used for upload count progress.
final _allTypes = _categories.expand((c) => c.types).toList();

// ─── Screen ────────────────────────────────────────────────────────────────────

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<DocumentIntelligenceProvider>().load(),
    );
  }

  Future<void> _pick(_DocType type) async {
    final provider = context.read<DocumentIntelligenceProvider>();

    // Step 1: choose source
    final source = await showModalBottomSheet<_PickSource>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (ctx) => _PickSourceSheet(typeName: type.name),
    );
    if (source == null || !mounted) return;

    // Step 2: pick file
    String? path;
    String? fileName;
    if (source == _PickSource.file) {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
      );
      path = result?.files.single.path;
      fileName = result?.files.single.name;
    } else {
      final image = await ImagePicker().pickImage(
        source: source == _PickSource.camera
            ? ImageSource.camera
            : ImageSource.gallery,
        imageQuality: 85,
        maxWidth: 2048,
      );
      path = image?.path;
      fileName = image?.name;
    }
    if (path == null || !mounted) return;

    // Step 3: show preview and confirm
    final file = File(path);
    final sizeKb = (await file.length()) / 1024;
    final sizeLabel = sizeKb > 1024
        ? '${(sizeKb / 1024).toStringAsFixed(1)} MB'
        : '${sizeKb.toStringAsFixed(0)} KB';

    if (!mounted) return;
    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (ctx) => _UploadPreviewSheet(
        typeName: type.name,
        fileName: fileName ?? path!.split(Platform.pathSeparator).last,
        fileSize: sizeLabel,
        icon: type.icon,
        color: Theme.of(context).colorScheme.primary,
      ),
    );
    if (confirmed != true || !mounted) return;

    // Step 4: upload
    try {
      await provider.upload(type.id, file);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${type.name} uploaded successfully.'),
            backgroundColor: const Color(0xFF16803C),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Upload failed. Check your connection and try again.',
            ),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DocumentIntelligenceProvider>(
      builder: (context, p, _) {
        final docs = p.documents;
        final uploaded = docs?.length ?? 0;
        final total = _allTypes.length;

        return Scaffold(
          appBar: AppBar(title: const Text('Build My Profile')),
          body: docs == null && p.loading
              ? const AppLoadingView(
                  message: 'Getting your document checklist...',
                )
              : RefreshIndicator(
                  onRefresh: p.load,
                  child: CustomScrollView(
                    slivers: [
                      SliverToBoxAdapter(
                        child: _Header(
                          uploaded: uploaded,
                          total: total,
                          errorMessage: p.errorMessage,
                        ),
                      ),
                      for (final cat in _categories)
                        SliverToBoxAdapter(
                          child: _CategorySection(
                            category: cat,
                            docs: docs ?? const [],
                            uploadProgress: p.uploadProgress,
                            onUpload: _pick,
                          ),
                        ),
                      SliverToBoxAdapter(
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                          child: PrimaryButton(
                            label: 'Process Documents & Build My Profile',
                            icon: Icons.auto_awesome_rounded,
                            isLoading: p.processing,
                            onPressed: docs == null || docs.isEmpty
                                ? null
                                : () async {
                                    final nav = Navigator.of(context);
                                    if (await p.processAndPrepareProfile() &&
                                        mounted) {
                                      nav.pushNamed(AppRoutes.profileReview);
                                    }
                                  },
                          ),
                        ),
                      ),
                      if (p.errorMessage != null && docs != null)
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            child: Text(
                              p.errorMessage!,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                          ),
                        ),
                      const SliverToBoxAdapter(
                        child: Padding(
                          padding: EdgeInsets.fromLTRB(20, 8, 20, 32),
                          child: Text(
                            'Your documents are used only to build your profile and find relevant government schemes.',
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
        );
      },
    );
  }
}

// ─── Header ────────────────────────────────────────────────────────────────────

class _Header extends StatelessWidget {
  const _Header({
    required this.uploaded,
    required this.total,
    this.errorMessage,
  });
  final int uploaded, total;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final progress = total == 0 ? 0.0 : uploaded / total;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Upload once. We do the paperwork.',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 6),
          const Text(
            'Add the documents you have. You can safely complete the rest later.',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 10,
                    backgroundColor: cs.surfaceContainerHighest,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text(
                '$uploaded / $total',
                style: Theme.of(context).textTheme.labelLarge,
              ),
            ],
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

// ─── Category section ──────────────────────────────────────────────────────────

class _CategorySection extends StatelessWidget {
  const _CategorySection({
    required this.category,
    required this.docs,
    required this.uploadProgress,
    required this.onUpload,
  });
  final _Category category;
  final List<CitizenDocument> docs;
  final Map<String, double> uploadProgress;
  final Future<void> Function(_DocType) onUpload;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                category.icon,
                size: 15,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 6),
              Text(
                category.label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Theme.of(context).colorScheme.primary,
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Divider(),
          const SizedBox(height: 8),
          for (final type in category.types)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _DocumentCard(
                type: type,
                document: docs.where((d) => d.type == type.id).firstOrNull,
                progress: uploadProgress[type.id],
                onUpload: () => onUpload(type),
              ),
            ),
        ],
      ),
    );
  }
}

// ─── Document card ─────────────────────────────────────────────────────────────

class _DocumentCard extends StatelessWidget {
  const _DocumentCard({
    required this.type,
    required this.document,
    required this.progress,
    required this.onUpload,
  });
  final _DocType type;
  final CitizenDocument? document;
  final double? progress;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isUploading = progress != null;
    final (statusLabel, statusColor, statusIcon) = _statusInfo(document, cs);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 50,
              width: 50,
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(type.icon, color: statusColor, size: 24),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          type.name,
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                      ),
                      if (type.required)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: cs.error.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'Required',
                            style: TextStyle(
                              fontSize: 11,
                              color: cs.error,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    document?.fileName ?? type.description,
                    style: Theme.of(context).textTheme.bodySmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 8),
                  if (isUploading)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        LinearProgressIndicator(
                          value: progress,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Uploading...',
                          style: TextStyle(
                            fontSize: 12,
                            color: cs.primary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    )
                  else
                    Row(
                      children: [
                        Icon(statusIcon, size: 13, color: statusColor),
                        const SizedBox(width: 4),
                        Text(
                          statusLabel,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: statusColor,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              height: 36,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  minimumSize: Size.zero,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  textStyle: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                onPressed: isUploading ? null : onUpload,
                child: Text(document == null ? 'Upload' : 'Replace'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  (String, Color, IconData) _statusInfo(CitizenDocument? doc, ColorScheme cs) {
    if (doc == null) {
      return type.required
          ? ('Required', cs.error, Icons.error_outline)
          : ('Optional', cs.outline, Icons.upload_file_outlined);
    }
    return switch (doc.uploadStatus) {
      'verified' => (
        'Verified',
        const Color(0xFF16803C),
        Icons.verified_rounded,
      ),
      'processed' => (
        'Processed',
        const Color(0xFF0D47A1),
        Icons.check_circle_outline,
      ),
      'processing' => (
        'Processing',
        const Color(0xFF9A6B00),
        Icons.hourglass_top_rounded,
      ),
      'needs_review' => (
        'Needs Review',
        const Color(0xFF9A6B00),
        Icons.rate_review_outlined,
      ),
      'failed' => ('Failed', cs.error, Icons.error_outline),
      _ => ('Uploaded', const Color(0xFF0D47A1), Icons.cloud_done_outlined),
    };
  }
}

// ─── Pick source bottom sheet ──────────────────────────────────────────────────

enum _PickSource { camera, gallery, file }

class _PickSourceSheet extends StatelessWidget {
  const _PickSourceSheet({required this.typeName});
  final String typeName;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Upload $typeName',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Choose how you want to add this document.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            _SourceTile(
              icon: Icons.camera_alt_outlined,
              label: 'Take Photo',
              subtitle: 'Use your camera to capture this document',
              onTap: () => Navigator.pop(context, _PickSource.camera),
            ),
            const SizedBox(height: 10),
            _SourceTile(
              icon: Icons.photo_library_outlined,
              label: 'Choose from Gallery',
              subtitle: 'Select a photo from your phone',
              onTap: () => Navigator.pop(context, _PickSource.gallery),
            ),
            const SizedBox(height: 10),
            _SourceTile(
              icon: Icons.insert_drive_file_outlined,
              label: 'Choose Document',
              subtitle: 'PDF, JPG, JPEG, or PNG file',
              onTap: () => Navigator.pop(context, _PickSource.file),
            ),
            const SizedBox(height: 16),
            OutlinedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
          ],
        ),
      ),
    );
  }
}

class _SourceTile extends StatelessWidget {
  const _SourceTile({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.onTap,
  });
  final IconData icon;
  final String label, subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          border: Border.all(color: cs.outlineVariant),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              height: 46,
              width: 46,
              decoration: BoxDecoration(
                color: cs.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: cs.primary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: Theme.of(context).textTheme.titleSmall),
                  Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: cs.outline),
          ],
        ),
      ),
    );
  }
}

// ─── Upload preview bottom sheet ───────────────────────────────────────────────

class _UploadPreviewSheet extends StatelessWidget {
  const _UploadPreviewSheet({
    required this.typeName,
    required this.fileName,
    required this.fileSize,
    required this.icon,
    required this.color,
  });
  final String typeName, fileName, fileSize;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  height: 50,
                  width: 50,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        typeName,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        'Ready to upload',
                        style: TextStyle(color: color, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Theme.of(
                  context,
                ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _InfoRow(label: 'File', value: fileName),
                  const SizedBox(height: 6),
                  _InfoRow(label: 'Size', value: fileSize),
                  const SizedBox(height: 6),
                  _InfoRow(label: 'Type', value: typeName),
                ],
              ),
            ),
            const SizedBox(height: 20),
            PrimaryButton(
              label: 'Upload Now',
              icon: Icons.upload_rounded,
              onPressed: () => Navigator.pop(context, true),
            ),
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label, value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 44,
          child: Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 13),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
