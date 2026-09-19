import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:govt_scheme_app/models/recommendation.dart';
import 'package:govt_scheme_app/providers/recommendation_provider.dart';
import 'package:govt_scheme_app/repositories/recommendation_repository.dart';
import 'package:govt_scheme_app/screens/recommendations/recommendation_detail_screen.dart';

/// Fake repository so the detail screen can render without network access.
class _FakeRepository extends RecommendationRepository {
  _FakeRepository() : super(null);

  @override
  Future<RecommendationMatch> getRecommendation(String recommendationId) async {
    return RecommendationMatch.fromJson(const {
      'id': 'rec-1',
      'scheme_id': 'enam',
      'scheme_name': 'e-NAM National Agriculture Market',
      'eligibility_status': 'eligible',
      'display_name': 'e-NAM (National Agriculture Market)',
      'short_description':
          'e-NAM is an online national market platform that lets farmers sell their produce in participating APMC mandis across India.',
      'benefits_list': [
        'Online access to more buyers and markets',
        'Transparent price discovery based on real demand and supply',
      ],
      'description':
          'Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET (e-NAM)',
      'benefits': 'Page No. 13 Government of India he',
      'matched_rules': [
        {'condition': 'occupation', 'result': 'PASS', 'passed': true},
      ],
      'required_documents': <String>[],
      'missing_requirements': <Map<String, dynamic>>[],
    });
  }
}

RecommendationMatch _cleanMatch() => RecommendationMatch.fromJson(const {
      'id': 'rec-1',
      'scheme_id': 'enam',
      'scheme_name': 'e-NAM National Agriculture Market',
      'eligibility_status': 'eligible',
      'display_name': 'e-NAM (National Agriculture Market)',
      'short_description':
          'e-NAM is an online national market platform that lets farmers sell their produce in participating APMC mandis across India.',
      'benefits_list': [
        'Online access to more buyers and markets',
        'Transparent price discovery based on real demand and supply',
      ],
    });

RecommendationMatch _rawExtractionMatch() => RecommendationMatch.fromJson(const {
      'id': 'rec-2',
      'scheme_id': 'enam',
      'scheme_name': 'e-NAM National Agriculture Market',
      'eligibility_status': 'eligible',
      'short_description':
          'Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET (e-NAM)',
      'benefits_list': ['&TO&P) - Part (8 | 29 | ) Government of India he'],
    });

void main() {
  test('parses structured presentation fields from the API payload', () {
    final match = _cleanMatch();
    expect(match.displayTitle, 'e-NAM (National Agriculture Market)');
    expect(match.cleanShortDescription, startsWith('e-NAM is an online'));
    expect(match.benefitBullets, hasLength(2));
    expect(match.benefitBullets.first,
        'Online access to more buyers and markets');
  });

  test('raw PDF extraction never becomes the user-facing description', () {
    final match = _rawExtractionMatch();
    expect(match.cleanShortDescription, isNull);
    expect(match.benefitBullets, isEmpty);
  });

  test('benefit bullets drop noise but keep clean text', () {
    final match = RecommendationMatch.fromJson(const {
      'id': 'rec-3',
      'scheme_id': 'smam',
      'scheme_name': 'SMAM Operational Guidelines 2025',
      'eligibility_status': 'eligible',
      'short_description':
          'SMAM helps farmers buy modern farm machinery by giving subsidy.',
      'benefits_list': [
        'Financial assistance of 50% of machine cost for small and marginal farmers',
        'Page No. 6',
        'F.No.3-4l2020-M&T0&P',
        'www.google.com',
      ],
    });
    expect(match.benefitBullets, hasLength(1));
    expect(match.benefitBullets.first, contains('50%'));
  });

  testWidgets('detail screen shows About this scheme and What you get bullets',
      (tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<RecommendationProvider>(
        create: (_) => RecommendationProvider(_FakeRepository()),
        child: const MaterialApp(
          home: RecommendationDetailScreen(recommendationId: 'rec-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('About this scheme'), findsOneWidget);
    expect(find.text('What you get'), findsOneWidget);
    expect(
      find.textContaining('e-NAM is an online national market platform'),
      findsOneWidget,
    );
    expect(
      find.text('Online access to more buyers and markets'),
      findsOneWidget,
    );
    expect(find.textContaining('Page No'), findsNothing);
    expect(find.textContaining('Uttam fasal'), findsNothing);
  });

  testWidgets('detail screen falls back safely for noisy payloads',
      (tester) async {
    final match = _rawExtractionMatch();
    // Raw extraction is sanitized away and the safe fallback is used.
    expect(match.cleanShortDescription, isNull);
    expect(match.benefitBullets, isEmpty);
    expect(RecommendationMatch.aboutFallback,
        'Information about this scheme is being prepared.');
  });
}
