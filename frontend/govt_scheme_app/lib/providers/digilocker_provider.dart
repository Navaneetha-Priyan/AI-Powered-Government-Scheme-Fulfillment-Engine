import 'package:flutter/foundation.dart';

import '../models/citizen_models.dart';
import '../repositories/digilocker_repository.dart';

class DigiLockerProvider extends ChangeNotifier {
  DigiLockerProvider(this._repository);

  final DigiLockerRepository _repository;

  DigiLockerStatus? _status;
  DocumentSummary? _documents;
  GovernmentDocument? _selectedDocument;
  DigiLockerSyncResult? _lastSyncResult;
  bool _isLoading = false;
  bool _isSyncing = false;
  String? _errorMessage;

  DigiLockerStatus? get status => _status;
  DocumentSummary? get documents => _documents;
  GovernmentDocument? get selectedDocument => _selectedDocument;
  DigiLockerSyncResult? get lastSyncResult => _lastSyncResult;
  bool get isLoading => _isLoading;
  bool get isSyncing => _isSyncing;
  String? get errorMessage => _errorMessage;

  Future<void> loadStatus() async {
    _setLoading(true);
    try {
      _status = await _repository.getStatus();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadDocuments() async {
    _setLoading(true);
    try {
      _documents = await _repository.getDocuments();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadDocument(String documentId) async {
    _setLoading(true);
    try {
      _selectedDocument = await _repository.getDocument(documentId);
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<DigiLockerSyncResult> sync({bool forceRefresh = false}) async {
    _isSyncing = true;
    notifyListeners();
    try {
      _lastSyncResult = await _repository.sync(forceRefresh: forceRefresh);
      _status = await _repository.getStatus();
      _errorMessage = null;
      return _lastSyncResult!;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _isSyncing = false;
      notifyListeners();
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}
