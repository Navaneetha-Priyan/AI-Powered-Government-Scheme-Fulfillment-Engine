import 'dart:io';
import 'package:flutter/foundation.dart';
import '../core/network/api_exception.dart';
import '../models/document_intelligence.dart';
import '../repositories/document_intelligence_repository.dart';

class DocumentIntelligenceProvider extends ChangeNotifier {
  DocumentIntelligenceProvider(this._repository);
  final DocumentIntelligenceRepository _repository;
  List<CitizenDocument>? documents;
  ProfilePreview? preview;
  Map<String, int>? completeness;
  String? errorMessage;
  bool loading = false, processing = false;
  final Map<String, double> uploadProgress = {};
  VoidCallback? _onProfileDataChanged;

  /// Recommendation results are derived from this document-backed profile.
  /// Clear them whenever a document or confirmed profile changes.
  void attachRecommendationInvalidator(VoidCallback callback) {
    _onProfileDataChanged = callback;
  }

  Future<void> load() async {
    if (loading) return;
    loading = true;
    notifyListeners();
    try {
      documents = await _repository.documents();
      errorMessage = null;
    } catch (e) {
      errorMessage = e is ApiException
          ? e.message
          : 'Could not load your documents.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> upload(String type, File file) async {
    uploadProgress[type] = 0;
    notifyListeners();
    try {
      await _repository.upload(type, file, (sent, total) {
        uploadProgress[type] = total == 0 ? 0 : sent / total;
        notifyListeners();
      });
      await load();
      _onProfileDataChanged?.call();
    } finally {
      uploadProgress.remove(type);
      notifyListeners();
    }
  }

  Future<bool> processAndPrepareProfile() async {
    if (processing) return false;
    processing = true;
    notifyListeners();
    try {
      await _repository.processAll();
      await Future.wait([load(), loadProfileReview()]);
      _onProfileDataChanged?.call();
      return true;
    } catch (e) {
      errorMessage = e is ApiException
          ? e.message
          : 'We could not process your documents.';
      return false;
    } finally {
      processing = false;
      notifyListeners();
    }
  }

  Future<void> loadProfileReview() async {
    try {
      final values = await Future.wait([
        _repository.preview(),
        _repository.completeness(),
      ]);
      preview = values[0] as ProfilePreview;
      completeness = values[1] as Map<String, int>;
      errorMessage = null;
    } on ApiException catch (e) {
      errorMessage = e.message;
      rethrow;
    } finally {
      notifyListeners();
    }
  }

  Future<void> correct(String key, String value) async {
    await _repository.correct(key, value);
    await loadProfileReview();
  }

  Future<void> confirm() async {
    await _repository.confirm();
    await Future.wait([load(), loadProfileReview()]);
    _onProfileDataChanged?.call();
  }
}
