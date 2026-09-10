import 'dart:io';
import 'package:flutter/foundation.dart';
import '../core/network/api_exception.dart';
import '../models/document_intelligence.dart';
import '../repositories/document_intelligence_repository.dart';
import '../repositories/citizen_repository.dart';

class DocumentIntelligenceProvider extends ChangeNotifier {
  DocumentIntelligenceProvider(this._repository, this._citizenRepository);
  final DocumentIntelligenceRepository _repository;
  final CitizenRepository _citizenRepository;
  List<CitizenDocument>? documents;
  ProfilePreview? preview;
  bool showingPersistedProfile = false;
  Map<String, int>? completeness;
  String? errorMessage;
  bool loading = false, processing = false;
  final Map<String, double> uploadProgress = {};
  VoidCallback? _onProfileDataChanged;
  VoidCallback? _onCitizenProfileInvalidate;
  VoidCallback? _onBaseProfileInvalidate;

  /// Recommendation results are derived from this document-backed profile.
  /// Clear them whenever a document or confirmed profile changes.
  void attachRecommendationInvalidator(VoidCallback callback) {
    _onProfileDataChanged = callback;
  }

  /// Attach invalidators for the base profile (AuthProvider/ProfileProvider)
  /// and extended citizen profile (CitizenProvider).
  void attachProfileInvalidators({
    VoidCallback? onCitizenProfileInvalidate,
    VoidCallback? onBaseProfileInvalidate,
  }) {
    _onCitizenProfileInvalidate = onCitizenProfileInvalidate;
    _onBaseProfileInvalidate = onBaseProfileInvalidate;
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

  Future<void> upload(String type, File file, {bool replace = false}) async {
    uploadProgress[type] = 0;
    notifyListeners();
    try {
      await _repository.upload(type, file, (sent, total) {
        uploadProgress[type] = total == 0 ? 0 : sent / total;
        notifyListeners();
      }, replace: replace);
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
      showingPersistedProfile = false;
      if (!preview!.hasReviewItems) {
        final persisted = await _citizenRepository.getProfileDetails();
        final persistedFields = _persistedFields(persisted);
        if (persistedFields.isNotEmpty) {
          preview = ProfilePreview(
            fields: persistedFields,
            conflicts: const [],
            needsReview: 0,
          );
          showingPersistedProfile = true;
          final extended = persisted['extended_profile'];
          final persistedCompletion = extended is Map
              ? int.tryParse(extended['profile_completion_percentage']?.toString() ?? '')
              : null;
          if (persistedCompletion != null) {
            completeness = {...?completeness, 'overall': persistedCompletion};
          }
        }
      }
      errorMessage = null;
    } on ApiException catch (e) {
      errorMessage = e.message;
      rethrow;
    } finally {
      notifyListeners();
    }
  }

  Map<String, dynamic> _persistedFields(Map<String, dynamic> data) {
    final fields = <String, dynamic>{};
    for (final entry in data.entries) {
      if (entry.key != 'extended_profile' && entry.key != 'citizen_id' &&
          entry.key != 'email' && entry.key != 'phone' &&
          entry.key != 'profile_photo_url' && entry.value != null &&
          entry.value.toString().isNotEmpty) {
        fields[entry.key] = entry.value;
      }
    }
    final extended = data['extended_profile'];
    if (extended is Map) {
      for (final entry in extended.entries) {
        if (entry.key != 'id' && entry.key != 'citizen_id' &&
            entry.value != null && entry.value.toString().isNotEmpty) {
          fields[entry.key] = entry.value;
        }
      }
    }
    return fields;
  }

  Future<void> correct(String key, String value) async {
    await _repository.correct(key, value);
    await loadProfileReview();
  }

  Future<void> confirm() async {
    await _repository.confirm();
    // Confirmation changes documents to VERIFIED. The review endpoint only
    // lists pre-confirmation documents, so refreshing it here would replace
    // the populated review state with an empty preview.
    await load();
    _onProfileDataChanged?.call();
    _onCitizenProfileInvalidate?.call();
    _onBaseProfileInvalidate?.call();
  }
}
