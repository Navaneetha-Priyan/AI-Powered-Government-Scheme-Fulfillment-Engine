import 'package:flutter/foundation.dart';

import '../models/citizen_models.dart';
import '../repositories/citizen_repository.dart';
import 'eligibility_provider.dart';

class CitizenProvider extends ChangeNotifier {
  CitizenProvider(this._repository);

  final CitizenRepository _repository;
  EligibilityProvider? _eligibilityProvider;

  ExtendedProfile? _extendedProfile;
  IncomeDetails? _income;
  CasteDetails? _caste;
  LandRecordSummary? _landRecords;
  DocumentSummary? _documents;
  Map<String, dynamic>? _profileDetails;
  bool _isLoading = false;
  bool _isUploadingLandRecord = false;
  bool _isUploadingDocument = false;
  String? _errorMessage;
  String? _uploadErrorMessage;

  ExtendedProfile? get extendedProfile => _extendedProfile;
  IncomeDetails? get income => _income;
  CasteDetails? get caste => _caste;
  LandRecordSummary? get landRecords => _landRecords;
  DocumentSummary? get documents => _documents;
  Map<String, dynamic>? get profileDetails => _profileDetails;
  bool get isLoading => _isLoading;
  bool get isUploadingLandRecord => _isUploadingLandRecord;
  bool get isUploadingDocument => _isUploadingDocument;
  String? get errorMessage => _errorMessage;
  String? get uploadErrorMessage => _uploadErrorMessage;

  void attachEligibilityProvider(EligibilityProvider eligibilityProvider) {
    _eligibilityProvider = eligibilityProvider;
  }

  Future<void> loadProfileDetails() async {
    await _load(() async {
      _profileDetails = await _repository.getProfileDetails();
      _extendedProfile = ExtendedProfile.fromJson(
        _profileDetails?['extended_profile'] is Map
            ? Map<String, dynamic>.from(_profileDetails!['extended_profile'] as Map)
            : null,
      );
    });
  }

  Future<void> loadIncome() async {
    await _load(() async => _income = await _repository.getIncome());
  }

  Future<void> loadCaste() async {
    await _load(() async => _caste = await _repository.getCaste());
  }

  Future<void> loadLandRecords() async {
    await _load(() async => _landRecords = await _repository.getLandRecords());
  }

  Future<void> loadDocuments() async {
    await _load(() async {
      final previousSignature = _documentSignature(_documents);
      _documents = await _repository.getDocuments();
      if (_documentSignature(_documents) != previousSignature) {
        _eligibilityProvider?.invalidateAll();
      }
    });
  }

  Future<void> updateExtendedProfile(Map<String, dynamic> payload) async {
    await _load(() async {
      _extendedProfile = await _repository.updateExtendedProfile(payload);
      _eligibilityProvider?.invalidateAll();
    });
  }

  /// Uploads a land record with a supporting file, then refreshes the
  /// displayed land records so the new record appears immediately.
  ///
  /// The manually supplied fields remain the source of truth. The backend may
  /// also attempt real-document processing (PDF text extraction or OCR); its
  /// outcome is returned in [LandRecordUploadResult.processingStatus].
  Future<LandRecordUploadResult> uploadLandRecord({
    required String filePath,
    required String fileName,
    required String surveyNumber,
    required String village,
    required String district,
    required String landType,
    required double landArea,
    required String ownershipType,
    String? taluk,
    String? state,
    String? pattaNumber,
    String documentType = 'land_record',
  }) async {
    _isUploadingLandRecord = true;
    _uploadErrorMessage = null;
    notifyListeners();
    try {
      final result = await _repository.uploadLandRecord(
        filePath: filePath,
        fileName: fileName,
        surveyNumber: surveyNumber,
        village: village,
        district: district,
        landType: landType,
        landArea: landArea,
        ownershipType: ownershipType,
        taluk: taluk,
        state: state,
        pattaNumber: pattaNumber,
        documentType: documentType,
      );
      await loadLandRecords();
      _eligibilityProvider?.invalidateAll();
      return result;
    } catch (error) {
      _uploadErrorMessage = error.toString();
      rethrow;
    } finally {
      _isUploadingLandRecord = false;
      notifyListeners();
    }
  }

  /// Uploads a generic government document and processes it through the real
  /// backend document pipeline. After a successful upload, the document list
  /// and land records are refreshed so the UI reflects the enriched profile.
  Future<DocumentUploadResult> uploadDocument({
    required String filePath,
    required String fileName,
    required String documentType,
  }) async {
    _isUploadingDocument = true;
    _uploadErrorMessage = null;
    notifyListeners();
    try {
      final result = await _repository.uploadDocument(
        filePath: filePath,
        fileName: fileName,
        documentType: documentType,
      );
      await Future.wait<void>([
        loadDocuments(),
        loadLandRecords(),
      ]);
      _eligibilityProvider?.invalidateAll();
      return result;
    } catch (error) {
      _uploadErrorMessage = error.toString();
      rethrow;
    } finally {
      _isUploadingDocument = false;
      notifyListeners();
    }
  }

  Future<void> _load(Future<void> Function() action) async {
    _setLoading(true);
    try {
      await action();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  String _documentSignature(DocumentSummary? summary) {
    if (summary == null) {
      return '';
    }
    final ids = summary.documents.map((document) => '${document.id}:${document.verificationStatus}').toList()..sort();
    return ids.join('|');
  }
}