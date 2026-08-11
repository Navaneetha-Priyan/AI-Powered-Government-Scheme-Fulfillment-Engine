import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/widgets/app_buttons.dart';
import '../../providers/citizen_provider.dart';

class LandRecordUploadScreen extends StatefulWidget {
  const LandRecordUploadScreen({super.key});

  @override
  State<LandRecordUploadScreen> createState() => _LandRecordUploadScreenState();
}

class _LandRecordUploadScreenState extends State<LandRecordUploadScreen> {
  final _formKey = GlobalKey<FormState>();

  final _surveyNumberController = TextEditingController();
  final _villageController = TextEditingController();
  final _districtController = TextEditingController();
  final _landTypeController = TextEditingController();
  final _landAreaController = TextEditingController();
  final _ownershipTypeController = TextEditingController();
  final _talukController = TextEditingController();
  final _stateController = TextEditingController();
  final _pattaNumberController = TextEditingController();

  String? _selectedFilePath;
  String? _selectedFileName;
  bool _isPickingFile = false;
  bool _uploadSucceeded = false;
  bool _processingSucceeded = false;
  bool _processingFailed = false;
  String? _processingErrorMessage;

  @override
  void dispose() {
    _surveyNumberController.dispose();
    _villageController.dispose();
    _districtController.dispose();
    _landTypeController.dispose();
    _landAreaController.dispose();
    _ownershipTypeController.dispose();
    _talukController.dispose();
    _stateController.dispose();
    _pattaNumberController.dispose();
    super.dispose();
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
    if (!_formKey.currentState!.validate()) {
      return;
    }
    if (_selectedFilePath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a file first.')),
      );
      return;
    }

    final provider = context.read<CitizenProvider>();
    if (provider.isUploadingLandRecord) {
      return;
    }

    final landArea = double.tryParse(_landAreaController.text.trim());
    if (landArea == null || landArea <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid land area.')),
      );
      return;
    }

    try {
      final result = await provider.uploadLandRecord(
        filePath: _selectedFilePath!,
        fileName: _selectedFileName ?? 'land_record',
        surveyNumber: _surveyNumberController.text.trim(),
        village: _villageController.text.trim(),
        district: _districtController.text.trim(),
        landType: _landTypeController.text.trim(),
        landArea: landArea,
        ownershipType: _ownershipTypeController.text.trim(),
        taluk: _talukController.text.trim().isEmpty
            ? null
            : _talukController.text.trim(),
        state: _stateController.text.trim().isEmpty
            ? null
            : _stateController.text.trim(),
        pattaNumber: _pattaNumberController.text.trim().isEmpty
            ? null
            : _pattaNumberController.text.trim(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _uploadSucceeded = true;
        _processingSucceeded = result.isProcessed;
        _processingFailed = result.isFailed;
        _processingErrorMessage = result.processingError;
      });
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
    return Scaffold(
      appBar: AppBar(title: const Text('Upload Land Record')),
      body: _uploadSucceeded
          ? _buildSuccess(context)
          : _buildForm(context),
    );
  }

  Widget _buildSuccess(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.check_circle_rounded,
              size: 72,
              color: Theme.of(context).colorScheme.secondary,
            ),
            const SizedBox(height: 16),
            Text(
              'Land record uploaded',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Your land record has been saved. It will appear in your land records.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (_processingSucceeded) ...[
              const SizedBox(height: 16),
              Card(
                color: Theme.of(context).colorScheme.secondaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.auto_awesome_rounded),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Document processed. Your profile and records were updated from the uploaded document.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ] else if (_processingFailed) ...[
              const SizedBox(height: 16),
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(
                        Icons.info_outline_rounded,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _processingErrorMessage ??
                              'Document uploaded, but we could not read all details automatically.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Done',
              icon: Icons.check_rounded,
              onPressed: () => Navigator.of(context).pop(true),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildForm(BuildContext context) {
    return Consumer<CitizenProvider>(
      builder: (context, provider, _) {
        final isUploading = provider.isUploadingLandRecord;
        return SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: Form(
                key: _formKey,
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
                              'Select File',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Upload your land record and enter the required details.',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                            const SizedBox(height: 16),
                            OutlinedButton.icon(
                              onPressed: isUploading ? null : _pickFile,
                              icon: _isPickingFile
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(Icons.attach_file_rounded),
                              label: Text(
                                _selectedFileName ?? 'Choose a file (PDF or image)',
                              ),
                            ),
                            if (_selectedFilePath != null) ...[
                              const SizedBox(height: 8),
                              Text(
                                'File selected. The application may read the document to update your details automatically.',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
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
                            Text(
                              'Land Record Details',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 16),
                            TextFormField(
                              controller: _surveyNumberController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'Survey Number *',
                                prefixIcon: Icon(Icons.numbers_rounded),
                              ),
                              validator: (value) =>
                                  (value == null || value.trim().isEmpty)
                                      ? 'Enter the survey number'
                                      : null,
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _villageController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'Village *',
                                prefixIcon: Icon(Icons.location_city_outlined),
                              ),
                              validator: (value) =>
                                  (value == null || value.trim().isEmpty)
                                      ? 'Enter the village'
                                      : null,
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _districtController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'District *',
                                prefixIcon: Icon(Icons.map_outlined),
                              ),
                              validator: (value) =>
                                  (value == null || value.trim().isEmpty)
                                      ? 'Enter the district'
                                      : null,
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _landTypeController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'Land Type *',
                                prefixIcon: Icon(Icons.landscape_outlined),
                              ),
                              validator: (value) =>
                                  (value == null || value.trim().isEmpty)
                                      ? 'Enter the land type'
                                      : null,
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _landAreaController,
                              enabled: !isUploading,
                              keyboardType: const TextInputType.numberWithOptions(
                                decimal: true,
                              ),
                              decoration: const InputDecoration(
                                labelText: 'Land Area (acres) *',
                                prefixIcon: Icon(Icons.square_foot_outlined),
                              ),
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return 'Enter the land area';
                                }
                                final parsed = double.tryParse(value.trim());
                                if (parsed == null || parsed <= 0) {
                                  return 'Enter a valid land area';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _ownershipTypeController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'Ownership Type *',
                                prefixIcon: Icon(Icons.verified_user_outlined),
                              ),
                              validator: (value) =>
                                  (value == null || value.trim().isEmpty)
                                      ? 'Enter the ownership type'
                                      : null,
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _talukController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'Taluk (optional)',
                                prefixIcon: Icon(Icons.place_outlined),
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _stateController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'State (optional)',
                                prefixIcon: Icon(Icons.flag_outlined),
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _pattaNumberController,
                              enabled: !isUploading,
                              decoration: const InputDecoration(
                                labelText: 'Patta Number (optional)',
                                prefixIcon: Icon(Icons.receipt_long_outlined),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    PrimaryButton(
                      label: isUploading ? 'Uploading...' : 'Upload',
                      icon: Icons.cloud_upload_outlined,
                      isLoading: isUploading,
                      onPressed: isUploading ? null : _submit,
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}