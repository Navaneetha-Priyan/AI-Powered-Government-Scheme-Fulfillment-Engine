import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/models/recommendation.dart';
import 'package:govt_scheme_app/screens/recommendations/recommendations_screen.dart';

RecommendationMatch _cardMatch({
  String schemeName = 'Scheme',
  String? reason,
  String? estimatedBenefit,
  String? benefits,
  List<RecommendationRule> matched = const [],
  List<RecommendationRule> missing = const [],
  List<String> docs = const [],
  String eligibilityStatus = 'potentially_eligible',
  double eligibilityPercentage = 72,
  double confidenceScore = 68,
  String? semanticQuery,
}) {
  return RecommendationMatch(
    id: 'rec-1',
    schemeId: 'scheme-1',
    schemeName: schemeName,
    eligibilityStatus: eligibilityStatus,
    eligibilityPercentage: eligibilityPercentage,
    confidenceScore: confidenceScore,
    rankingPosition: 1,
    recommendationReason: reason,
    estimatedBenefit: estimatedBenefit,
    benefits: benefits,
    matchedRules: matched,
    missingRequirements: missing,
    requiredDocuments: docs,
    semanticQuery: semanticQuery,
  );
}

RecommendationRule _rule(String title, {bool passed = true}) {
  return RecommendationRule(
    ruleCode: 'rule-1',
    condition: title,
    operator: '==',
    passed: passed,
    description: title,
  );
}

void main() {
  test('cardReason never leaks raw PDF/RAG markers', () {
    final noisy = _cardMatch(
      reason:
          'SMAM Operational Guidelines 2025 F.No. 13-1/2025-SMAM pages 12-40 Department of Agriculture chunk retrieved smam-guidelines.pdf ... ' *
              8,
    );
    final reason = noisy.cardReason;
    // Either dropped entirely or sanitized to a short citizen-safe string.
    if (reason != null) {
      expect(reason.length, lessThanOrEqualTo(161));
      expect(reason, isNot(contains('F.No')));
      expect(reason, isNot(contains('.pdf')));
      expect(reason.toLowerCase(), isNot(contains('pages 12')));
    }

    final clean = _cardMatch(reason: 'You are registered as a farmer');
    expect(clean.cardReason, 'You are registered as a farmer');
  });

  test('cardBenefit prefers estimated benefit and truncates long text', () {
    final m = _cardMatch(
      estimatedBenefit: 'Support related to agricultural machinery/equipment. ' * 10,
    );
    expect(m.cardBenefit, isNotNull);
    expect(m.cardBenefit!.length, lessThanOrEqualTo(141));
  });

  test('card bullets are bounded and collapse documents', () {
    final m = _cardMatch(
      matched: [
        _rule('You are registered as a farmer'),
        _rule('Your farmer status matches the scheme requirements'),
      ],
      missing: [
        _rule('Aadhaar document required', passed: false),
        _rule('Priority category unknown', passed: false),
      ],
      docs: const ['Bank passbook'],
    );
    expect(m.cardMatchBullets.length, lessThanOrEqualTo(3));
    expect(m.cardMissingBullets.length, lessThanOrEqualTo(3));
    expect(
      m.cardMissingBullets,
      contains('Supporting document, if applicable'),
    );
  });

  test('recommendation card never shows raw retrieval/match percentages', () {
    final m = _cardMatch(
      eligibilityStatus: 'more_information_needed',
      eligibilityPercentage: 55,
      confidenceScore: 58,
    );
    // Backend still carries raw numeric metrics, but the card helper must not
    // leak them as citizen-facing percentages or technical labels.
    final line = cardStatusLine(m.eligibilityStatus);
    expect(line, 'More information needed');
    expect(line, isNot(contains('%')));
    expect(line.toLowerCase(), isNot(contains('match')));
    expect(line.toLowerCase(), isNot(contains('eligibility')));
  });

  test('narrow screen summary line maps statuses to citizen labels', () {
    expect(cardStatusLine(''), 'Information not available');
    expect(cardStatusLine('unknown'), 'Information not available');
    expect(cardStatusLine('potentially_eligible'), 'More information needed');
    expect(cardStatusLine('eligible'), 'You may be eligible');
    expect(cardStatusLine('not_eligible'), 'You are not currently eligible');
  });

  testWidgets('recommendation list does not overflow on narrow screen', (tester) async {
    final matches = [
      _cardMatch(
        schemeName:
            'Sub-Mission on Agricultural Mechanization SMAM Operational Guidelines 2025 with a very long scheme name that must wrap',
        reason: 'You are registered as a farmer',
        estimatedBenefit:
            'Support related to agricultural machinery and equipment for eligible farmers.',
        matched: [_rule('You are registered as a farmer')],
        missing: [_rule('Priority category')],
        eligibilityStatus: 'potentially_eligible',
        semanticQuery: 'RAW CHUNK smam-guidelines.pdf Page 37 F.No. 13 ... ' * 20,
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 360,
            child: RecommendationsListView(matches: matches),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    // Citizen text visible…
    expect(find.textContaining('Why this may be useful for you'), findsOneWidget);
    expect(find.text('View Scheme'), findsOneWidget);
    // …but raw retrieval dump never rendered on the card.
    expect(find.textContaining('RAW CHUNK'), findsNothing);
    expect(find.textContaining('.pdf'), findsNothing);
    // Technical percentage chips must not appear.
    expect(find.textContaining('Eligibility'), findsNothing);
    expect(find.textContaining('Match 68'), findsNothing);
    expect(find.textContaining('55%'), findsNothing);
  });
}
