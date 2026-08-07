import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/models/eligibility.dart';
import 'package:govt_scheme_app/providers/eligibility_provider.dart';
import 'package:govt_scheme_app/repositories/eligibility_repository.dart';

class _FakeEligibilityRepository extends EligibilityRepository {
  _FakeEligibilityRepository() : super(null);

  int calls = 0;
  Duration delay = Duration.zero;
  final Set<String> failingSchemes = {};

  @override
  Future<EligibilityCheck> checkSchemeEligibility(String schemeId) async {
    calls += 1;
    if (delay > Duration.zero) {
      await Future<void>.delayed(delay);
    }
    if (failingSchemes.contains(schemeId)) {
      throw StateError('backend exploded');
    }
    return EligibilityCheck.fromJson({
      'citizen_id': 'citizen-1',
      'evaluated_at': '2026-08-07T10:00:00',
      'total_rules': 2,
      'passed_rules': 1,
      'eligibility_percentage': 50,
      'eligible': false,
      'matched_rules': [
        {
          'rule_code': 'state_match',
          'condition': 'state',
          'operator': 'equals',
          'expected_value': 'Tamil Nadu',
          'actual_value': 'Tamil Nadu',
          'passed': true,
        }
      ],
      'missing_requirements': [
        {
          'rule_code': 'income_certificate',
          'condition': 'income certificate document',
          'operator': 'exists',
          'expected_value': 'Income Certificate',
          'actual_value': null,
          'passed': false,
        }
      ],
      'required_documents': ['Income Certificate', 'Aadhaar'],
      'application_ready': false,
      'reasoning': 'One mandatory requirement is missing.',
    });
  }
}

void main() {
  test('caches eligibility checks by scheme id', () async {
    final repository = _FakeEligibilityRepository();
    final provider = EligibilityProvider(repository);

    final first = await provider.loadEligibility('scheme-1');
    final second = await provider.loadEligibility('scheme-1');

    expect(first, same(second));
    expect(repository.calls, 1);
    expect(provider.eligibilityFor('scheme-1')?.eligibilityPercentage, 50);
  });

  test('invalidates cache and reloads refreshed eligibility', () async {
    final repository = _FakeEligibilityRepository();
    final provider = EligibilityProvider(repository);

    await provider.loadEligibility('scheme-1');
    provider.invalidateAll();
    await provider.loadEligibility('scheme-1');

    expect(repository.calls, 2);
    expect(provider.cacheVersion, 1);
  });

  test('derives missing documents from failed rules', () async {
    final provider = EligibilityProvider(_FakeEligibilityRepository());

    final result = await provider.loadEligibility('scheme-1');

    expect(result?.eligible, isFalse);
    expect(result?.matchedRules.length, 1);
    expect(result?.failedRules.length, 1);
    expect(result?.missingDocuments, contains('Income Certificate'));
    expect(result?.requiredDocuments, contains('Aadhaar'));
    expect(result?.applicationReady, isFalse);
  });

  test('shares a single in-flight request across concurrent calls', () async {
    final repository = _FakeEligibilityRepository()..delay = const Duration(milliseconds: 50);
    final provider = EligibilityProvider(repository);

    final results = await Future.wait([
      provider.loadEligibility('scheme-1'),
      provider.loadEligibility('scheme-1'),
      provider.loadEligibility('scheme-1', refresh: true),
    ]);

    expect(repository.calls, 1);
    expect(results.whereType<EligibilityCheck>().length, 3);
    expect(provider.isLoadingScheme('scheme-1'), isFalse);
  });

  test('discards stale results that complete after cache invalidation', () async {
    final repository = _FakeEligibilityRepository()..delay = const Duration(milliseconds: 50);
    final provider = EligibilityProvider(repository);

    final inFlight = provider.loadEligibility('scheme-1');
    provider.invalidateAll();

    final result = await inFlight;
    expect(result, isNull);
    expect(provider.eligibilityFor('scheme-1'), isNull);
    expect(repository.calls, 1);

    // A fresh load after invalidation must hit the API again.
    final reloaded = await provider.loadEligibility('scheme-1');
    expect(reloaded, isNotNull);
    expect(repository.calls, 2);
  });

  test('scopes error messages per scheme id', () async {
    final repository = _FakeEligibilityRepository()..failingSchemes.add('scheme-bad');
    final provider = EligibilityProvider(repository);

    await provider.loadEligibility('scheme-bad');
    expect(provider.errorFor('scheme-bad'), isNotNull);
    expect(provider.errorFor('scheme-good'), isNull);

    // A successful load clears only its own error.
    await provider.loadEligibility('scheme-good');
    expect(provider.errorFor('scheme-bad'), isNotNull);
    expect(provider.errorFor('scheme-good'), isNull);
  });
}

