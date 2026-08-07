import 'package:flutter/foundation.dart';

import '../models/recommendation.dart';
import '../repositories/recommendation_repository.dart';

class RecommendationProvider extends ChangeNotifier {
  RecommendationProvider(this._repository);

  final RecommendationRepository _repository;

  RecommendationSummary? _summary;
  final Map<String, RecommendationMatch> _detailCache = {};
  final Map<String, Future<RecommendationMatch?>> _detailInFlight = {};
  List<RecommendationHistory> _history = const [];
  String? _errorMessage;
  String? _historyError;
  bool _isLoading = false;
  bool _isRefreshing = false;
  bool _isHistoryLoading = false;
  int _generation = 0;
  int _version = 0;

  RecommendationSummary? get summary => _summary;
  List<RecommendationMatch> get recommendations => _summary?.recommendations ?? const [];
  List<RecommendationHistory> get history => _history;
  bool get isLoading => _isLoading;
  bool get isRefreshing => _isRefreshing;
  bool get isHistoryLoading => _isHistoryLoading;
  bool get hasLoaded => _summary != null;
  String? get errorMessage => _errorMessage;
  String? get historyError => _historyError;
  int get version => _version;

  RecommendationMatch? recommendationFor(String recommendationId) {
    return _detailCache[recommendationId];
  }

  bool isLoadingRecommendation(String recommendationId) {
    return _detailInFlight.containsKey(recommendationId);
  }

  /// Loads the latest recommendations. If nothing has been loaded yet this
  /// generates them via the backend; otherwise it returns the cached summary.
  Future<RecommendationSummary?> loadRecommendations({bool refresh = false}) async {
    if (!refresh && _summary != null) {
      return _summary;
    }

    if (_isLoading || _isRefreshing) {
      return _summary;
    }

    final generation = _generation;
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final summary = _summary == null
          ? await _repository.generate()
          : await _repository.refresh();
      if (generation != _generation) {
        return null;
      }
      _summary = summary;
      _errorMessage = null;
      return summary;
    } catch (error) {
      if (generation == _generation) {
        _errorMessage = error.toString();
      }
      return null;
    } finally {
      if (generation == _generation) {
        _isLoading = false;
        _isRefreshing = false;
        notifyListeners();
      }
    }
  }

  /// Explicitly asks the backend to (re)generate recommendations.
  Future<RecommendationSummary?> generateRecommendations() async {
    if (_isLoading || _isRefreshing) {
      return _summary;
    }

    final generation = _generation;
    _isRefreshing = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final summary = await _repository.generate();
      if (generation != _generation) {
        return null;
      }
      _summary = summary;
      _errorMessage = null;
      return summary;
    } catch (error) {
      if (generation == _generation) {
        _errorMessage = error.toString();
      }
      return null;
    } finally {
      if (generation == _generation) {
        _isRefreshing = false;
        notifyListeners();
      }
    }
  }

  /// Loads a single recommendation detail, caching it and de-duplicating
  /// concurrent requests.
  Future<RecommendationMatch?> loadRecommendationDetail(String recommendationId) async {
    if (recommendationId.isEmpty) {
      return null;
    }

    final cached = _detailCache[recommendationId];
    if (cached != null) {
      return cached;
    }

    final inFlight = _detailInFlight[recommendationId];
    if (inFlight != null) {
      return inFlight;
    }

    final generation = _generation;
    final future = _fetchDetail(recommendationId, generation);
    _detailInFlight[recommendationId] = future;

    try {
      return await future;
    } finally {
      if (_detailInFlight[recommendationId] == future) {
        _detailInFlight.remove(recommendationId);
        notifyListeners();
      }
    }
  }

  Future<RecommendationMatch?> _fetchDetail(String recommendationId, int generation) async {
    try {
      final match = await _repository.getRecommendation(recommendationId);
      if (generation != _generation) {
        return null;
      }
      _detailCache[recommendationId] = match;
      return match;
    } catch (error) {
      if (generation == _generation) {
        _errorMessage = error.toString();
      }
      return null;
    }
  }

  Future<void> loadHistory({bool refresh = false}) async {
    if (!refresh && _history.isNotEmpty) {
      return;
    }
    if (_isHistoryLoading) {
      return;
    }

    final generation = _generation;
    _isHistoryLoading = true;
    _historyError = null;
    notifyListeners();

    try {
      final history = await _repository.getHistory();
      if (generation != _generation) {
        return;
      }
      _history = history;
      _historyError = null;
    } catch (error) {
      if (generation == _generation) {
        _historyError = error.toString();
      }
    } finally {
      if (generation == _generation) {
        _isHistoryLoading = false;
        notifyListeners();
      }
    }
  }

  /// Clears the summary, detail cache, and history so the next load is fresh.
  /// Called whenever profile, documents, or eligibility data changes.
  void invalidateAll() {
    _generation += 1;
    _summary = null;
    _detailCache.clear();
    _detailInFlight.clear();
    _history = const [];
    _errorMessage = null;
    _historyError = null;
    _isLoading = false;
    _isRefreshing = false;
    _isHistoryLoading = false;
    _version += 1;
    notifyListeners();
  }
}

