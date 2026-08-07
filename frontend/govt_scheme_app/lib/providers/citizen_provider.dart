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
  String? _errorMessage;

  ExtendedProfile? get extendedProfile => _extendedProfile;
  IncomeDetails? get income => _income;
  CasteDetails? get caste => _caste;
  LandRecordSummary? get landRecords => _landRecords;
  DocumentSummary? get documents => _documents;
  Map<String, dynamic>? get profileDetails => _profileDetails;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

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
