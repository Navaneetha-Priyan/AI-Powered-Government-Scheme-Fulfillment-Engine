import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/models/recommendation.dart';
import 'package:govt_scheme_app/providers/recommendation_provider.dart';
import 'package:govt_scheme_app/repositories/recommendation_repository.dart';

RecommendationMatch _match(String id, {String schemeName = 'Scheme', double confidence = 80}) {
  return RecommendationMatch(
    id: id,
    schemeId: 'scheme-$id',
    schemeName: schemeName,
    eligibilityStatus: 'eligible',
    eligibilityPercentage: 85,
    confidenceScore: confidence,
    rankingPosition: 1,
    matchedRules: const [],
    missingRequirements: const [],
    requiredDocuments: const ['Aadhaar'],
  );
}

RecommendationSummary _summary({String citizenId = 'citizen-1'}) {
  return RecommendationSummary(
    citizenId: citizenId,
    totalCandidates: 10,
    eligibleCount: 1,
    overallConfidence: 80,
    recommendations: [_match('rec-1')],
    history: RecommendationHistory(
      id: 'history-1',
      requestType: 'generate',
      totalCandidates: 10,
      eligibleCount: 1,
      overallConfidence: 80,
      status: 'completed',
      createdAt: DateTime(2026, 8, 7),
      matches: const [],
    ),
  );
}

class _FakeRecommendationRepository extends RecommendationRepository {
  _FakeRecommendationRepository() : super(null);

  int generateCalls = 0;
  int refreshCalls = 0;
  int latestCalls = 0;
  int detailCalls = 0;
  int historyCalls = 0;
  Duration delay = Duration.zero;
  bool failNext = false;

  @override
  Future<RecommendationSummary> generate({int limit = 5, String? category, String? state}) async {
    generateCalls += 1;
    await _maybeDelay();
    _maybeFail();
    return _summary();
  }

  @override
  Future<RecommendationSummary> refresh({int limit = 5, String? category, String? state}) async {
    refreshCalls += 1;
    await _maybeDelay();
    _maybeFail();
    return _summary();
  }

  @override
  Future<RecommendationSummary> getLatest() async {
    latestCalls += 1;
    await _maybeDelay();
    _maybeFail();
    return _summary();
  }

  @override
  Future<RecommendationMatch> getRecommendation(String recommendationId) async {
    detailCalls += 1;
    await _maybeDelay();
    _maybeFail();
    return _match(recommendationId);
  }

  @override
  Future<List<RecommendationHistory>> getHistory({int limit = 20}) async {
    historyCalls += 1;
    await _maybeDelay();
    _maybeFail();
    return [_summary().history];
  }

  Future<void> _maybeDelay() async {
    if (delay > Duration.zero) {
      await Future<void>.delayed(delay);
    }
  }

  void _maybeFail() {
    if (failNext) {
      failNext = false;
      throw StateError('backend exploded');
    }
  }
}

void main() {
  test('generates recommendations on first load and caches them', () async {
    final repository = _FakeRecommendationRepository();
    final provider = RecommendationProvider(repository);

    final first = await provider.loadRecommendations();
    final second = await provider.loadRecommendations();

    expect(repository.generateCalls, 1);
    expect(repository.latestCalls, 0);
    expect(first, same(second));
    expect(provider.recommendations.length, 1);
    expect(provider.hasLoaded, isTrue);
  });

  test('refresh calls the backend and updates the summary', () async {
    final repository = _FakeRecommendationRepository();
    final provider = RecommendationProvider(repository);

    await provider.loadRecommendations();
    await provider.loadRecommendations(refresh: true);

    expect(repository.generateCalls, 1);
    expect(repository.refreshCalls, 1);
    expect(provider.summary, isNotNull);
  });

  test('explicit generate re-runs the pipeline', () async {
    final repository = _FakeRecommendationRepository();
    final provider = RecommendationProvider(repository);

    await provider.generateRecommendations();

    expect(repository.generateCalls, 1);
    expect(provider.hasLoaded, isTrue);
  });

  test('deduplicates concurrent detail loads', () async {
    final repository = _FakeRecommendationRepository()..delay = const Duration(milliseconds: 50);
    final provider = RecommendationProvider(repository);

    final results = await Future.wait([
      provider.loadRecommendationDetail('rec-1'),
      provider.loadRecommendationDetail('rec-1'),
      provider.loadRecommendationDetail('rec-1'),
    ]);

    expect(repository.detailCalls, 1);
    expect(results.whereType<RecommendationMatch>().length, 3);
    expect(provider.isLoadingRecommendation('rec-1'), isFalse);
  });

  test('caches detail results after first load', () async {
    final repository = _FakeRecommendationRepository();
    final provider = RecommendationProvider(repository);

    await provider.loadRecommendationDetail('rec-1');
    await provider.loadRecommendationDetail('rec-1');

    expect(repository.detailCalls, 1);
    expect(provider.recommendationFor('rec-1'), isNotNull);
  });

  test('invalidateAll clears summary, details and history', () async {
    final repository = _FakeRecommendationRepository();
    final provider = RecommendationProvider(repository);

    await provider.loadRecommendations();
    await provider.loadRecommendationDetail('rec-1');
    await provider.loadHistory();

    provider.invalidateAll();

    expect(provider.summary, isNull);
    expect(provider.recommendationFor('rec-1'), isNull);
    expect(provider.history, isEmpty);
    expect(provider.hasLoaded, isFalse);
  });

  test('discards stale summary results that complete after invalidation', () async {
    final repository = _FakeRecommendationRepository()..delay = const Duration(milliseconds: 50);
    final provider = RecommendationProvider(repository);

    final inFlight = provider.loadRecommendations();
    provider.invalidateAll();

    final result = await inFlight;
    expect(result, isNull);
    expect(provider.summary, isNull);

    // A fresh load after invalidation must hit the backend again.
    final reloaded = await provider.loadRecommendations();
    expect(reloaded, isNotNull);
    expect(repository.generateCalls, 2);
  });

  test('records errorMessage on failure', () async {
    final repository = _FakeRecommendationRepository()..failNext = true;
    final provider = RecommendationProvider(repository);

    final result = await provider.loadRecommendations();

    expect(result, isNull);
    expect(provider.errorMessage, isNotNull);
    expect(provider.hasLoaded, isFalse);
  });

  test('expose history loading and error scoping', () async {
    final repository = _FakeRecommendationRepository();
    final provider = RecommendationProvider(repository);

    await provider.loadHistory();
    expect(provider.history.length, 1);
    expect(provider.historyError, isNull);

    repository.failNext = true;
    await provider.loadHistory(refresh: true);
    expect(provider.historyError, isNotNull);
  });
}

