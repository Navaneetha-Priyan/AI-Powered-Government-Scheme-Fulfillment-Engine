import 'package:flutter/foundation.dart';

import '../models/eligibility.dart';
import '../repositories/eligibility_repository.dart';

class EligibilityProvider extends ChangeNotifier {
  EligibilityProvider(this._repository);

  final EligibilityRepository _repository;

  final Map<String, EligibilityCheck> _cache = {};
  final Map<String, Future<EligibilityCheck?>> _inFlight = {};
  final Map<String, String> _errors = {};
  bool _isLoading = false;
  int _cacheVersion = 0;
  int _generation = 0;

  /// Invoked whenever the eligibility cache is fully invalidated so dependent
  /// caches (e.g. recommendations) can be refreshed too.
  VoidCallback? onInvalidateAll;

  bool get isLoading => _isLoading;
  int get cacheVersion => _cacheVersion;

  EligibilityCheck? eligibilityFor(String schemeId) => _cache[schemeId];
  bool isLoadingScheme(String schemeId) => _inFlight.containsKey(schemeId);

  String? errorFor(String schemeId) => _errors[schemeId];

  Future<EligibilityCheck?> loadEligibility(String schemeId, {bool refresh = false}) async {
    if (schemeId.isEmpty) {
      return null;
    }

    if (!refresh && _cache.containsKey(schemeId)) {
      return _cache[schemeId];
    }

    // Share the in-flight request: concurrent calls (including refresh)
    // await the same future instead of firing duplicate API requests.
    final inFlight = _inFlight[schemeId];
    if (inFlight != null) {
      return inFlight;
    }

    final generation = _generation;
    final future = _fetch(schemeId, generation);
    _inFlight[schemeId] = future;

    try {
      return await future;
    } finally {
      if (_inFlight[schemeId] == future) {
        _inFlight.remove(schemeId);
        _isLoading = _inFlight.isNotEmpty;
        notifyListeners();
      }
    }
  }

  Future<EligibilityCheck?> _fetch(String schemeId, int generation) async {
    _errors.remove(schemeId);
    _isLoading = true;
    notifyListeners();

    try {
      final result = await _repository.checkSchemeEligibility(schemeId);
      // Discard stale results that arrive after the cache was invalidated.
      if (generation != _generation) {
        return null;
      }
      _cache[schemeId] = result;
      _errors.remove(schemeId);
      return result;
    } catch (error) {
      _errors[schemeId] = error.toString();
      return null;
    }
  }

  void invalidateScheme(String schemeId) {
    _generation += 1;
    if (_cache.remove(schemeId) != null ||
        _inFlight.remove(schemeId) != null ||
        _errors.remove(schemeId) != null) {
      _cacheVersion += 1;
      notifyListeners();
    }
  }

  void invalidateAll() {
    _generation += 1;
    _cache.clear();
    _inFlight.clear();
    _errors.clear();
    _cacheVersion += 1;
    _isLoading = false;
    notifyListeners();
    onInvalidateAll?.call();
  }
}

