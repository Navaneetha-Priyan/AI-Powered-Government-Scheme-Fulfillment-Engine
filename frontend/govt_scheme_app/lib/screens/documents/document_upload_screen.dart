import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/widgets/app_buttons.dart';
import '../../models/citizen_models.dart';
import '../../providers/citizen_provider.dart';
import '../../routes/app_routes.dart';

/// The document types the backend supports for real document processing.
///
/// The UI uses human-readable labels, NOT backend enum names.
class DocumentTypeOption {
  const DocumentTypeOption({
    required this.value,
    required this.label,
    required this.icon,
    this.description,
  });

  /// Backend enum value (e.g. 'aadhaar', 'income_certificate').
  final String value;

  /// Human-readable label shown to the user.
  final String label;

  final IconData icon;
  final String? description;
}

const List<DocumentTypeOption> kDocumentTypeOptions = [
  DocumentTypeOption(
    value: 'aadhaar',
    label: 'Aadhaar',
    icon: Icons.badge_outlined,
    description: 'Identity and address details',
  ),
  DocumentTypeOption(
    value: 'income_certificate',
    label: 'Income Certificate',
    icon: Icons.payments_outlined,
    description: 'Annual income and income category',
  ),
  DocumentTypeOption(
    value: 'caste_certificate',
    label: 'Caste / Community Certificate',
    icon: Icons.diversity_3_outlined,
    description: 'Caste, community, sub-caste, religion',
  ),
  DocumentTypeOption(
    value: 'smart_ration_card',
    label: 'Smart Ration Card',
    icon: Icons.receipt_long_outlined,
    description: 'Card number, family size, card type',
  ),
  DocumentTypeOption(
    value: 'residence_certificate',
    label: 'Residence Certificate',
    icon: Icons.home_outlined,
    description: 'Village, taluk, district, state',
  ),
  DocumentTypeOption(
    value: 'farmer_id',
    label: 'Farmer ID',
    icon: Icons.agriculture_outlined,
    description: 'Farmer ID, farmer status, occupation',
  ),
  DocumentTypeOption(
    value: 'land_record',
    label: 'Land Record',
    icon: Icons.landscape_outlined,
    description: 'Survey number, area, land type',
  ),
  DocumentTypeOption(
    value: 'disability_certificate',
    label: 'Disability Certificate',
    icon: Icons.accessible_forward_outlined,
    description: 'Disability status and percentage',
  ),
];

/// Reusable "Upload Government Document" experience.
///
/// One screen for ALL supported document types. The user:
/// 1. selects the document type
/// 2. selects a PDF/image file
/// 3. uploads
/// 4. watches processing status
/// 5. sees the extracted field summary
/// 6. can view profile or documents
class DocumentUploadScreen extends StatefulWidget {
  const DocumentUploadScreen({super.key});

  @override
  State<DocumentUploadScreen> createState() => _DocumentUploadScreenState();
}

enum _UploadPhase { form, uploading, success, failed }

class _DocumentUploadScreenState extends State<DocumentUploadScreen> {
  String? _selectedDocumentType;
  String? _selectedFilePath;
  String? _selectedFileName;
  bool _isPickingFile = false;
  _UploadPhase _phase = _UploadPhase.form;
  DocumentUploadResult? _result;
  bool _processingFailed = false;
  String? _processingErrorMessage;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload Government Document')),
      body: switch (_phase) {
        _UploadPhase.form => _buildForm(context),
        _UploadPhase.uploading => _buildUploading(context),
        _UploadPhase.success => _buildSuccess(context),
        _UploadPhase.failed => _buildFailed(context),
      },
    );
  }

  // ─── Form ────────────────────────────────────────────────────────────────

  Widget _buildForm(BuildContext context) {
    final provider = context.watch<CitizenProvider>();
    final isUploading = provider.isUploadingDocument;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Document Type',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Select the type of government document you want to upload.',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 16),
                      _buildDocumentTypeDropdown(context, isUploading),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('File', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                        'Choose a PDF or image file (JPG, PNG). The app will read it to update your details automatically.',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: isUploading ? null : _pickFile,
                        icon: _isPickingFile
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.attach_file_rounded),
                        label: Text(
                          _selectedFileName ?? 'Choose a file (PDF or image)',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (_selectedFilePath != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          'File selected. Your profile will be updated using the information in this document.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              PrimaryButton(
                label: isUploading ? 'Uploading...' : 'Upload Document',
                icon: Icons.cloud_upload_outlined,
                isLoading: isUploading,
                onPressed: isUploading ? null : _submit,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDocumentTypeDropdown(
    BuildContext context,
    bool isUploading,
  ) {
    return DropdownButtonFormField<String>(
      initialValue: _selectedDocumentType,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Select document type',
        prefixIcon: Icon(Icons.description_outlined),
      ),
      items: kDocumentTypeOptions
          .map(
            (option) => DropdownMenuItem(
              value: option.value,
              child: Text(option.label, overflow: TextOverflow.ellipsis),
            ),
          )
          .toList(),
      onChanged: isUploading
          ? null
          : (value) => setState(() => _selectedDocumentType = value),
      selectedItemBuilder: (context) => kDocumentTypeOptions
          .map(
            (option) => Row(
              children: [
                Icon(option.icon, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(option.label, overflow: TextOverflow.ellipsis),
                ),
              ],
            ),
          )
          .toList(),
    );
  }

  Future<void> _pickFile() async {
    if (_isPickingFile) {
      return;
    }
    setState(() => _isPickingFile = true);
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
        allowMultiple: false,
      );
      if (result == null || result.files.isEmpty) {
        return;
      }
      final file = result.files.single;
      final path = file.path;
      if (path == null || path.isEmpty) {
        return;
      }
      setState(() {
        _selectedFilePath = path;
        _selectedFileName = file.name;
      });
    } finally {
      if (mounted) {
        setState(() => _isPickingFile = false);
      }
    }
  }

  Future<void> _submit() async {
    if (_selectedDocumentType == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a document type.')),
      );
      return;
    }
    if (_selectedFilePath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a file.')),
      );
      return;
    }

    final provider = context.read<CitizenProvider>();
    if (provider.isUploadingDocument) {
      return;
    }

    setState(() => _phase = _UploadPhase.uploading);

    try {
      final result = await provider.uploadDocument(
        filePath: _selectedFilePath!,
        fileName: _selectedFileName ?? 'document',
        documentType: _selectedDocumentType!,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _processingFailed = result.isFailed;
        _processingErrorMessage = result.processingError;
        _phase = _UploadPhase.success;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _processingErrorMessage = AppStrings.friendlyError(error);
        _phase = _UploadPhase.failed;
      });
    }
  }

  // ─── Uploading ───────────────────────────────────────────────────────────

  Widget _buildUploading(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              height: 56,
              width: 56,
              child: CircularProgressIndicator(strokeWidth: 4),
            ),
            const SizedBox(height: 24),
            Text(
              'Processing your document...',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'This may take a few moments. Please wait.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }

  // ─── Success ─────────────────────────────────────────────────────────────

  Widget _buildSuccess(BuildContext context) {
    final processing = _result?.processing;
    final completion = processing?.enrichment?['profile_completion_percentage'];
    final extractedFields =
        processing?.extractedFields ?? const <String, dynamic>{};

    // Determine the truthful state based on what was actually extracted.
    final visibleFields = extractedFields.entries
        .where((entry) => entry.value != null && entry.value.toString().isNotEmpty)
        .toList();
    final hasExtractedFields = visibleFields.isNotEmpty;
    final hasMissingFields =
        extractedFields.values.any((value) => value == null);

    // State A: Successfully processed with fields
    // State B: Successfully processed but partial (some fields missing)
    // State C: Uploaded but no fields extracted
    // State D: Processing failure (handled by _buildFailed)
    final bool isProcessingFailure = _processingFailed;
    final bool isPartial = hasExtractedFields && hasMissingFields;
    final bool isNoFields = !hasExtractedFields;

    // Choose the appropriate icon and title.
    final IconData icon;
    final String title;
    final String subtitle;

    if (isProcessingFailure) {
      icon = Icons.error_outline_rounded;
      title = 'Document processing failed.';
      subtitle = _processingErrorMessage ??
          'We could not process this document. Please try a different file.';
    } else if (isNoFields) {
      icon = Icons.warning_amber_rounded;
      title = 'Document uploaded.';
      subtitle =
          "We couldn't read useful information from this document.";
    } else if (isPartial) {
      icon = Icons.check_circle_rounded;
      title = 'Document processed.';
      subtitle =
          'Some information could not be read automatically.';
    } else {
      icon = Icons.check_circle_rounded;
      title = 'Document processed successfully.';
      subtitle =
          'Your profile has been updated using information from this document.';
    }

    final bool showWarningCard = isPartial;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(
                icon,
                size: 72,
                color: isProcessingFailure
                    ? Theme.of(context).colorScheme.error
                    : isNoFields
                        ? Theme.of(context).colorScheme.onSurfaceVariant
                        : Theme.of(context).colorScheme.secondary,
              ),
              const SizedBox(height: 16),
              Text(
                title,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 16),
              if (processing != null) ...[
                _buildExtractionMethod(context, processing),
              ],
              if (hasExtractedFields) ...[
                const SizedBox(height: 16),
                _ExtractedFieldsCard(
                  fields: extractedFields,
                  documentType: _selectedDocumentType,
                ),
              ],
              if (showWarningCard) ...[
                const SizedBox(height: 16),
                Card(
                  color: Theme.of(context).colorScheme.tertiaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        const Icon(Icons.info_outline_rounded),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Some information could not be read automatically.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (isProcessingFailure) ...[
                const SizedBox(height: 16),
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(
                          Icons.warning_amber_rounded,
                          color: Theme.of(context).colorScheme.error,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _processingErrorMessage ??
                                'Document uploaded, but some details could not be read.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (completion != null) ...[
                const SizedBox(height: 8),
                Text(
                  'Profile completion: $completion%',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
              const SizedBox(height: 24),
              PrimaryButton(
                label: 'View Profile',
                icon: Icons.person_outline,
                onPressed: () => Navigator.of(context).pushNamed(
                  AppRoutes.profile,
                ),
              ),
              const SizedBox(height: 12),
              SecondaryButton(
                label: 'View Documents',
                icon: Icons.description_outlined,
                onPressed: () => Navigator.of(context).pop(true),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildExtractionMethod(
    BuildContext context,
    DocumentProcessingData processing,
  ) {
    final message = processing.usedOcr
        ? 'Document image processed successfully.'
        : processing.usedPdfText
            ? 'Document text extracted successfully.'
            : null;

    if (message == null) {
      return const SizedBox.shrink();
    }

    return Card(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.auto_awesome_rounded),
            const SizedBox(width: 10),
            Expanded(
              child: Text(message, style: Theme.of(context).textTheme.bodyMedium),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Failed ──────────────────────────────────────────────────────────────

  Widget _buildFailed(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline_rounded,
              size: 72,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Could not upload the document.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              _processingErrorMessage ?? 'Please try again.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Try Again',
              icon: Icons.refresh_rounded,
              onPressed: () => setState(() => _phase = _UploadPhase.form),
            ),
            const SizedBox(height: 12),
            SecondaryButton(
              label: 'Cancel',
              icon: Icons.close_rounded,
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
      ),
    );
  }
}

/// Displays only the extracted fields returned by the backend.
///
/// Uses human-readable labels per document type. Values come ONLY from the
/// backend processing result — nothing is hardcoded.
class _ExtractedFieldsCard extends StatelessWidget {
  const _ExtractedFieldsCard({
    required this.fields,
    this.documentType,
  });

  final Map<String, dynamic> fields;
  final String? documentType;

  static const Map<String, String> _labels = {
    'full_name': 'Name',
    'date_of_birth': 'Date of Birth',
    'gender': 'Gender',
    'address_line1': 'Address',
    'village': 'Village',
    'taluk': 'Taluk',
    'district': 'District',
    'state': 'State',
    'pincode': 'PIN Code',
    'annual_income': 'Annual Income',
    'income_category': 'Income Category',
    'financial_year': 'Financial Year',
    'caste': 'Caste',
    'community': 'Community',
    'sub_caste': 'Sub Caste',
    'religion': 'Religion',
    'card_number': 'Card Number',
    'card_type': 'Card Type',
    'family_size': 'Family Size',
    'farmer_id': 'Farmer ID',
    'is_farmer': 'Farmer',
    'occupation': 'Occupation',
    'survey_number': 'Survey Number',
    'land_area': 'Land Area',
    'unit': 'Unit',
    'land_type': 'Land Type',
    'ownership_type': 'Ownership Type',
    'patta_number': 'Patta Number',
    'holder_name': 'Holder Name',
    'owner_name': 'Owner Name',
    'is_disabled': 'Disabled',
    'disability_percentage': 'Disability Percentage',
    'issuing_authority': 'Issuing Authority',
  };

  @override
  Widget build(BuildContext context) {
    final visible = fields.entries
        .where((entry) => entry.value != null && entry.value.toString().isNotEmpty)
        .toList();

    if (visible.isEmpty) {
      // No visible fields — the parent widget handles the "no information"
      // message. Do NOT duplicate the warning here.
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Information found', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            ...visible.map(
              (entry) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 140,
                      child: Text(
                        _labels[entry.key] ?? _titleCase(entry.key),
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                    Expanded(
                      child: Text(
                        _displayValue(entry.key, entry.value),
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _displayValue(String key, dynamic value) {
    if (value is bool) {
      return value ? 'Yes' : 'No';
    }
    if (value is num) {
      if (key == 'annual_income') {
        return 'Rs. ${value.toStringAsFixed(value == value.roundToDouble() ? 0 : 2)}';
      }
      if (key == 'land_area') {
        return value.toString();
      }
      return value.toString();
    }
    final text = value.toString();
    if (key == 'date_of_birth') {
      // Backend sends ISO yyyy-MM-dd. Show dd/MM/yyyy for readability.
      final parts = text.split('-');
      if (parts.length == 3) {
        return '${parts[2]}/${parts[1]}/${parts[0]}';
      }
    }
    return text;
  }

  String _titleCase(String value) {
    return value
        .split('_')
        .map((word) => word.isEmpty
            ? word
            : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }
}