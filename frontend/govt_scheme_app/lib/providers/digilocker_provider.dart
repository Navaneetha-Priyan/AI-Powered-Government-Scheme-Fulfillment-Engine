import 'package:flutter/foundation.dart';

import '../models/citizen_models.dart';
import '../repositories/digilocker_repository.dart';
import 'eligibility_provider.dart';

class DigiLockerProvider extends ChangeNotifier {
  DigiLockerProvider(this._repository);

  final DigiLockerRepository _repository;
  EligibilityProvider? _eligibilityProvider;

  DigiLockerStatus? _status;
  DocumentSummary? _documents;
  GovernmentDocument? _selectedDocument;
  DigiLockerSyncResult? _lastSyncResult;
  bool _isLoading = false;
  bool _isSyncing = false;
  int _activeRequests = 0;
  String? _errorMessage;

  DigiLockerStatus? get status => _status;
  DocumentSummary? get documents => _documents;
  GovernmentDocument? get selectedDocument => _selectedDocument;
  DigiLockerSyncResult? get lastSyncResult => _lastSyncResult;
  bool get isLoading => _isLoading;
  bool get isSyncing => _isSyncing;
  String? get errorMessage => _errorMessage;

  void attachEligibilityProvider(EligibilityProvider eligibilityProvider) {
    _eligibilityProvider = eligibilityProvider;
  }

  Future<void> loadStatus() async {
    await _runWithLoading(() async {
      _status = await _repository.getStatus();
      _errorMessage = null;
    });
  }

  Future<void> loadDocuments() async {
    await _runWithLoading(() async {
      final previousSignature = _documentSignature(_documents);
      _documents = await _repository.getDocuments();
      if (_documentSignature(_documents) != previousSignature) {
        _eligibilityProvider?.invalidateAll();
      }
      _errorMessage = null;
    });
  }

  Future<void> loadDocument(String documentId) async {
    await _runWithLoading(() async {
      _selectedDocument = await _repository.getDocument(documentId);
      _errorMessage = null;
    });
  }

  Future<DigiLockerSyncResult> sync({bool forceRefresh = false}) async {
    if (_isSyncing) {
      if (_lastSyncResult != null) {
        return _lastSyncResult!;
      }
      throw StateError('A sync is already in progress');
    }

    _isSyncing = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final result = await _repository.sync(forceRefresh: forceRefresh);
      _lastSyncResult = result;

      await Future.wait<void>([
        _repository.getStatus().then((status) => _status = status),
        _repository.getDocuments().then((documents) => _documents = documents),
      ]);

      _eligibilityProvider?.invalidateAll();
      _errorMessage = null;
      return result;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _isSyncing = false;
      notifyListeners();
    }
  }

  Future<void> _runWithLoading(Future<void> Function() action) async {
    _activeRequests += 1;
    if (!_isLoading) {
      _isLoading = true;
      notifyListeners();
    }

    try {
      await action();
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _activeRequests -= 1;
      if (_activeRequests <= 0) {
        _activeRequests = 0;
        _isLoading = false;
        notifyListeners();
      }
    }
  }

  String _documentSignature(DocumentSummary? summary) {
    if (summary == null) {
      return '';
    }
    final ids =
        summary.documents
            .map((document) => '${document.id}:${document.verificationStatus}')
            .toList()
          ..sort();
    return ids.join('|');
  }
}
