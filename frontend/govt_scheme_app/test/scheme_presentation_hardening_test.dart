import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:govt_scheme_app/core/utils/presentation_text.dart';
import 'package:govt_scheme_app/models/eligibility.dart';
import 'package:govt_scheme_app/models/government_scheme.dart';
import 'package:govt_scheme_app/models/recommendation.dart';
import 'package:govt_scheme_app/providers/eligibility_provider.dart';
import 'package:govt_scheme_app/providers/scheme_provider.dart';
import 'package:govt_scheme_app/repositories/eligibility_repository.dart';
import 'package:govt_scheme_app/repositories/scheme_repository.dart';
import 'package:govt_scheme_app/screens/schemes/scheme_detail_screen.dart';


/// The exact broken OCR extraction that was surfacing under PMMVY's benefits.
const String corruptedPmmvy =
    "Ei. {r*yr {qt, er6.q.qq. \$ga rtP{s Dr. Rakesh Gupta, tAS Joint Secrotary Dt4^,,- Pgg\"^'ata*t'tt*e 748.";

GovernmentScheme _schemeFromJson(Map<String, dynamic> json) =>
    GovernmentScheme.fromJson(Map<String, dynamic>.from(json));

Map<String, dynamic> _pmmvyJson() => <String, dynamic>{
      'id': 'pmmvy-test',
      'scheme_name': 'PMMVY Test Scheme',
      'description': corruptedPmmvy,
      'benefits': corruptedPmmvy,
      'eligibility_summary': corruptedPmmvy,
      'required_documents': 'Page No. 4',
      'application_process': 'Government of India',
      'category': 'social',
      'department': 'Women and Child Development',
      'government_level': 'central',
      'about': null,
      'benefits_list': <String>[],
    };

Map<String, dynamic> _cleanSchemeJson() => <String, dynamic>{
      'id': 'enam-test',
      'scheme_name': 'e-NAM National Agriculture Market',
      'description': 'Page No. 1 Uttam fasal Uttam Enam',
      'benefits': 'Page No. 13 Government of India he',
      'category': 'agriculture',
      'department': 'Agriculture',
      'government_level': 'central',
      'display_name': 'e-NAM (National Agriculture Market)',
      'about':
          'e-NAM is an online national market platform that lets farmers sell produce in participating mandis.',
      'benefits_list': <String>[
        'Online access to more buyers and markets',
        'Transparent price discovery based on real demand and supply',
      ],
      'who_it_is_for': 'Farmers selling produce in participating mandis.',
      'documents': <String>['Identity proof'],
      'application': <String>['Register through the official portal.'],
    };

class _FakeSchemeRepository extends SchemeRepository {
  _FakeSchemeRepository(this.scheme) : super(null);

  final GovernmentScheme scheme;

  @override
  Future<SchemeListResponse> listSchemes({
    int skip = 0,
    int limit = 20,
    String? category,
    String? status,
    String? query,
  }) async =>
      SchemeListResponse(items: [scheme], total: 1, skip: skip, limit: limit);

  @override
  Future<GovernmentScheme> getScheme(String schemeId) async => scheme;
}

class _FakeEligibilityRepository extends EligibilityRepository {
  _FakeEligibilityRepository() : super(null);

  @override
  Future<EligibilityCheck> checkSchemeEligibility(String schemeId) async {
    return EligibilityCheck.fromJson({
      'citizen_id': 'citizen-1',
      'evaluated_at': '2026-08-07T10:00:00',
      'total_rules': 1,
      'passed_rules': 1,
      'eligibility_percentage': 100,
      'eligible': true,
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
      'missing_requirements': <Map<String, dynamic>>[],
      'required_documents': <String>['Aadhaar'],
      'application_ready': true,
      'reasoning': 'All checks passed.',
    });
  }
}

Widget _schemeScreen(GovernmentScheme scheme) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<SchemeProvider>(
        create: (_) => SchemeProvider(_FakeSchemeRepository(scheme)),
      ),
      ChangeNotifierProvider<EligibilityProvider>(
        create: (_) => EligibilityProvider(_FakeEligibilityRepository()),
      ),
    ],
    child: MaterialApp(
      home: SchemeDetailScreen(schemeId: scheme.id),
    ),
  );
}

// Only sections below the fold are reachable via tester.scrollUntilVisible,
// which is also how the unsealed-text regression is checked.
// The validated benefits section exists below the fold, so scroll it into
// view before asserting on it.
Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  for (var attempt = 0; attempt < 10 && finder.evaluate().isEmpty; attempt++) {
    await tester.fling(
      find.byType(ListView).first,
      const Offset(0, -400),
      2000,
    );
    await tester.pumpAndSettle();
  }
  expect(finder, findsWidgets);
}

void main() {

  group('presentation_text validator', () {
    test('rejects corrupted OCR extraction', () {
      expect(isPresentationNoise(corruptedPmmvy), isTrue);
      expect(
        isPresentationNoise(
            'Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET'),
        isTrue,
      );
      expect(
        isPresentationNoise('&TO&P) - Part (8 | 29 | ) Government of India he'),
        isTrue,
      );
    });

    test('rejects control characters and mojibake', () {
      expect(isPresentationNoise('Hello\x01World'), isTrue);
      expect(isPresentationNoise('Broken \uFFFD encoding'), isTrue);
      expect(isPresentationNoise('Ei. {r*yr {qt, er6.q.qq.'), isTrue);
      expect(isPresentationNoise('Government of lndla'), isTrue);
    });

    test('rejects placeholders and file references', () {
      expect(isPresentationNoise(null), isTrue);
      expect(isPresentationNoise(''), isTrue);
      expect(isPresentationNoise('   '), isTrue);
      expect(isPresentationNoise('None'), isTrue);
      expect(isPresentationNoise('N'), isTrue);
      expect(isPresentationNoise('www.enam.gov.in'), isTrue);
      expect(isPresentationNoise('x' * 500), isTrue);
    });

    test('accepts legitimate Indian-language Unicode', () {
      expect(
        isPresentationNoise('\u0BA4\u0BBF\u0B9F\u0BCD\u0B9F\u0BAE.'),
        isFalse,
      );
      expect(
        isPresentationNoise('\u092F\u094B\u091C\u0928\u093E.'),
        isFalse,
      );
    });

    test('accepts legitimate scheme prose', () {
      expect(
        isPresentationNoise(
            'PM-KISAN gives income support to landholding farmer families.'),
        isFalse,
      );
      expect(
        isPresentationNoise(
            'Financial assistance of 50% of machine cost for SC/ST farmers.'),
        isFalse,
      );
      expect(
        isPresentationNoise('PMAY-U 2.0 (Housing for All)'),
        isFalse,
      );
    });

    test('drops corrupted bullets but keeps valid ones', () {
      expect(
        cleanPresentationList([
          corruptedPmmvy,
          'Page No. 13',
          'Rs. 6,000 per year paid directly into the bank account',
        ]),
        ['Rs. 6,000 per year paid directly into the bank account'],
      );
      expect(cleanPresentationList([corruptedPmmvy, 'N', 'Page No. 4']),
          isEmpty);
    });
  });

  group('GovernmentScheme presentation getters', () {
    test('PMMVY corrupted columns never become presentation content', () {
      final scheme = _schemeFromJson(_pmmvyJson());
      expect(scheme.cleanAbout, isNull);
      expect(scheme.cleanBenefits, isEmpty);
      expect(scheme.cleanEligibilitySummary, isNull);
      expect(scheme.cleanDocuments, isEmpty);
      expect(scheme.displayTitle, 'PMMVY Test Scheme');
    });

    test('valid curated content is surfaced', () {
      final scheme = _schemeFromJson(_cleanSchemeJson());
      expect(scheme.cleanAbout, startsWith('e-NAM is an online'));
      expect(scheme.cleanBenefits, hasLength(2));
      expect(scheme.displayTitle, 'e-NAM (National Agriculture Market)');
      expect(scheme.cleanWhoItIsFor, isNotNull);
    });

    test('RAG matched_content is never used as presentation', () {
      final scheme = _schemeFromJson({
        'scheme_id': 'pmmvy-test',
        'scheme_name': 'PMMVY Test Scheme',
        'category': 'social',
        'department': 'Women and Child Development',
        'matched_content': corruptedPmmvy,
        'relevant_content': corruptedPmmvy,
      });
      expect(scheme.cleanAbout, isNull);
      expect(scheme.cleanShortDescription, isNull);
      expect(scheme.cleanBenefits, isEmpty);
    });
  });

  group('RecommendationMatch corrupted hardening', () {
    test('corrupted benefits_list yields no bullets', () {
      final match = RecommendationMatch.fromJson({
        'id': 'rec-pmmvy',
        'scheme_id': 'pmmvy',
        'scheme_name': 'PMMVY Test Scheme',
        'eligibility_status': 'eligible',
        'short_description': corruptedPmmvy,
        'benefits_list': [corruptedPmmvy, 'N', 'Page No. 13'],
      });
      expect(match.cleanShortDescription, isNull);
      expect(match.benefitBullets, isEmpty);
    });

    test('valid bullets are preserved', () {
      final match = RecommendationMatch.fromJson({
        'id': 'rec-clean',
        'scheme_id': 'enam',
        'scheme_name': 'e-NAM',
        'eligibility_status': 'eligible',
        'short_description': 'e-NAM is an online market platform.',
        'benefits_list': [
          corruptedPmmvy,
          'Online access to more buyers and markets',
        ],
      });
      expect(match.benefitBullets, ['Online access to more buyers and markets']);
    });
  });

  group('SchemeDetailScreen', () {
    testWidgets('omits What you get for corrupted/empty benefits',
        (tester) async {
      await tester.pumpWidget(_schemeScreen(_schemeFromJson(_pmmvyJson())));
      await tester.pumpAndSettle();

      expect(find.text('About this scheme'), findsOneWidget);
      expect(
        find.text('Information about this scheme is being prepared.'),
        findsOneWidget,
      );
      // The Benefits section is omitted — never raw extraction.
      expect(find.text('What you get'), findsNothing);
      expect(find.textContaining('{r*yr'), findsNothing);
      expect(find.textContaining('rtP'), findsNothing);
      expect(find.textContaining('Page No'), findsNothing);
    });

    testWidgets('renders curated bullets for valid presentation',
        (tester) async {
      await tester
          .pumpWidget(_schemeScreen(_schemeFromJson(_cleanSchemeJson())));
      await tester.pumpAndSettle();

      expect(find.text('About this scheme'), findsOneWidget);
      expect(
        find.textContaining('e-NAM is an online national market platform'),
        findsOneWidget,
      );

      // The validated benefits section only exists below the fold.
      await _scrollTo(tester, find.text('What you get'));
      expect(find.text('What you get'), findsOneWidget);
      expect(
        find.textContaining('Online access to more buyers and markets'),
        findsOneWidget,
      );
      // The raw DB columns are never rendered as presentation.
      expect(find.textContaining('Page No'), findsNothing);
      expect(find.textContaining('Uttam fasal'), findsNothing);
      expect(find.textContaining('Government of India he'), findsNothing);
    });
  });
}


