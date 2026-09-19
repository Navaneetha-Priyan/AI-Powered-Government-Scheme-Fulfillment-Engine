import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/core/utils/evidence_mapping.dart';
import 'package:govt_scheme_app/models/recommendation.dart';

RecommendationMatch _fullPmKisanMatch() => RecommendationMatch.fromJson(const {
      'id': 'rec-1',
      'scheme_id': 'pm-kisan',
      'scheme_name': 'PM-KISAN',
      'eligibility_status': 'potentially_eligible',
      'matched_rules': [
        {'condition': 'occupation', 'result': 'PASS', 'passed': true},
        {'condition': 'land_type', 'result': 'PASS', 'passed': true},
        {'condition': 'land_ownership', 'result': 'PASS', 'passed': true},
      ],
      'missing_requirements': [
        {'condition': 'income_tax_payer', 'result': 'UNKNOWN', 'passed': false},
      ],
      'required_documents': ['aadhaar', 'land_record', 'bank_account'],
      'mandatory_rules_total': 4,
      'mandatory_rules_passed': 3,
      'evidence_checklist': [
        {
          'requirement': 'aadhaar',
          'label': 'Aadhaar',
          'kind': 'document',
          'status': 'verified',
          'document_types': ['aadhaar_card'],
          'matched_document_type': 'aadhaar_card',
        },
        {
          'requirement': 'land_record',
          'label': 'Land record',
          'kind': 'document',
          'status': 'verified',
          'document_types': ['land_document'],
          'matched_document_type': 'land_document',
        },
        {
          'requirement': 'bank_account',
          'label': 'Bank account proof',
          'kind': 'document',
          'status': 'needed',
          'document_types': ['bank_passbook'],
        },
      ],
    });

void main() {
  test('parses structured condition result, notes and mandatory flag', () {
    final rule = RecommendationRule.fromJson(const {
      'rule_id': 'SMAM-001',
      'condition': 'land_ownership_proof',
      'operator': '==',
      'result': 'UNKNOWN',
      'passed': false,
      'mandatory': true,
      'notes': 'Land ownership could not be verified from the profile.',
    });

    expect(rule.ruleCode, 'SMAM-001');
    expect(rule.result, 'UNKNOWN');
    expect(rule.isConditionUnknown, isTrue);
    expect(rule.isConditionFail, isFalse);
    expect(rule.mandatory, isTrue);
    expect(rule.notes, isNotNull);
  });

  test('optional conditions are not mandatory in the citizen count', () {
    final rule = RecommendationRule.fromJson(const {
      'condition': 'preference',
      'passed': false,
      'severity': 'optional',
    });
    expect(rule.mandatory, isFalse);
    expect(rule.isConditionCountable, isFalse);
  });

  test('parses evidence checklist entries from the backend payload', () {
    final match = RecommendationMatch.fromJson(const {
      'id': 'rec-1',
      'scheme_id': 's-1',
      'scheme_name': 'Scheme',
      'eligibility_status': 'potentially_eligible',
      'evidence_checklist': [
        {
          'requirement': 'land_record',
          'label': 'Land record',
          'kind': 'document',
          'status': 'needed',
          'document_types': ['land_document'],
        },
        {
          'requirement': 'aadhaar',
          'label': 'Aadhaar',
          'kind': 'document',
          'status': 'available',
          'matched_document_type': 'aadhaar_card',
        },
      ],
      'mandatory_rules_total': 3,
      'mandatory_rules_passed': 2,
    });

    expect(match.evidenceChecklist, hasLength(2));
    expect(match.evidenceChecklist.first.label, 'Land record');
    expect(match.mandatoryRulesTotal, 3);
    expect(match.mandatoryRulesPassed, 2);
    expect(match.conditionSummary, '2 of 3 conditions met');
  });

  test('verified backend evidence is not treated as still needed', () {
    final match = RecommendationMatch.fromJson(const {
      'id': 'rec-1',
      'scheme_id': 'pm-kisan',
      'scheme_name': 'PM-KISAN',
      'eligibility_status': 'potentially_eligible',
      'missing_requirements': [
        {
          'condition': 'aadhaar',
          'result': 'UNKNOWN',
          'passed': false,
        },
        {
          'condition': 'land_record',
          'result': 'UNKNOWN',
          'passed': false,
        },
        {
          'condition': 'income_tax_payer',
          'result': 'UNKNOWN',
          'passed': false,
        },
      ],
      'evidence_checklist': [
        {
          'requirement': 'aadhaar',
          'label': 'Aadhaar',
          'kind': 'document',
          'status': 'verified',
          'document_types': ['aadhaar_card'],
          'matched_document_type': 'aadhaar_card',
        },
        {
          'requirement': 'land_record',
          'label': 'Land record',
          'kind': 'document',
          'status': 'verified',
          'document_types': ['land_document'],
          'matched_document_type': 'land_document',
        },
      ],
      'required_documents': ['aadhaar', 'land_record'],
    });

    expect(
      match.evidenceItems.where((entry) => entry.status == EvidenceStatus.needed),
      isEmpty,
    );
    expect(match.cardMissingBullets.join(' '), isNot(contains('Aadhaar')));
    expect(match.cardMissingBullets.join(' '), isNot(contains('Land record')));
    expect(match.cardMissingBullets.join(' '), contains('Income-tax payer'));
    expect(match.uploadedDocumentTypes, {'aadhaar_card', 'land_document'});
  });

  test('farmer and community evidence stay available from backend checklist', () {
    final match = RecommendationMatch.fromJson(const {
      'id': 'rec-1',
      'scheme_id': 'enam',
      'scheme_name': 'e-NAM',
      'eligibility_status': 'potentially_eligible',
      'evidence_checklist': [
        {
          'requirement': 'farmer_registration',
          'label': 'Farmer ID',
          'kind': 'document',
          'status': 'verified',
          'document_types': ['farmer_document'],
          'matched_document_type': 'farmer_document',
        },
        {
          'requirement': 'caste_certificate',
          'label': 'Community certificate',
          'kind': 'document',
          'status': 'verified',
          'document_types': ['community_certificate'],
          'matched_document_type': 'community_certificate',
        },
      ],
    });

    expect(match.evidenceItems.every((entry) => entry.status.isHeld), isTrue);
    expect(
      match.uploadedDocumentTypes,
      {'farmer_document', 'community_certificate'},
    );
  });

  test('condition summary falls back to structured rule lists', () {
    final match = RecommendationMatch(
      id: 'rec-1',
      schemeId: 's-1',
      schemeName: 'Scheme',
      eligibilityStatus: 'potentially_eligible',
      eligibilityPercentage: 50,
      confidenceScore: 0,
      rankingPosition: 1,
      matchedRules: [
        _rule('age', result: 'PASS', passed: true),
        _rule('is_farmer', result: 'PASS', passed: true),
      ],
      missingRequirements: [
        _rule('income', result: 'FAIL', passed: false),
        _rule('caste', result: 'UNKNOWN', passed: false),
        // Optional conditions never inflate the citizen count.
        _rule('pref', result: 'FAIL', passed: false, mandatory: false),
        // Non-applicable conditional rules are excluded.
        _rule('cond', result: 'NOT_APPLICABLE', passed: true),
      ],
    );

    expect(match.conditionSummary, '2 of 4 conditions met');
  });

  test('text-extraction artifacts are never shown as benefits', () {
    expect(_matchWithBenefit('N').cardBenefit, isNull);
    expect(_matchWithBenefit(', N').cardBenefit, isNull);
    expect(_matchWithBenefit('None').cardBenefit, isNull);
    expect(_matchWithBenefit('Rs. 6000 per year').cardBenefit, isNotNull);
  });

  test('card description is sanitized and capped for the detail screen', () {
    final clean =
        _matchWithDescription('Support for small and marginal farmers.');
    expect(clean.cardDescription, isNotNull);

    final noisy = _matchWithDescription(
        'SMAM Operational Guidelines 2025 F.No. 13-1/2025 pages 12-40 chunk '
        'retrieved smam-guidelines.pdf ' *
            6);
    final desc = noisy.cardDescription;
    if (desc != null) {
      expect(desc.length, lessThanOrEqualTo(401));
      expect(desc, isNot(contains('.pdf')));
    }
  });

  test('bullet labels prefer curated notes and mapped document labels', () {
    final match = RecommendationMatch(
      id: 'rec-1',
      schemeId: 's-1',
      schemeName: 'Scheme',
      eligibilityStatus: 'potentially_eligible',
      eligibilityPercentage: 0,
      confidenceScore: 0,
      rankingPosition: 1,
      matchedRules: [
        _rule('is_farmer',
            result: 'PASS',
            passed: true,
            notes: 'Citizen is a registered farmer.'),
      ],
      missingRequirements: [
        _rule('land_record', result: 'UNKNOWN', passed: false),
      ],
      requiredDocuments: const ['bank_passbook'],
    );

    expect(match.cardMatchBullets, ['Citizen is a registered farmer']);

    expect(match.cardMissingBullets, contains('Land record'));
    expect(match.cardMissingBullets, contains('Bank account proof'));
    expect(match.cardMissingBullets.join(' '), isNot(contains('_')));
  });

  test('CASE 1/2/8: pm-kisan detail never contradicts its own evidence', () {
    final match = _fullPmKisanMatch();

    // "Documents & evidence": verified stays verified.
    final statuses = {
      for (final entry in match.evidenceItems) entry.requirement: entry.status
    };
    expect(statuses['aadhaar'], EvidenceStatus.verified);
    expect(statuses['land_record'], EvidenceStatus.verified);
    expect(statuses['bank_account'], EvidenceStatus.needed);

    // "What information is missing": verified evidence never reappears.
    final missing = match.cardMissingBullets.join(' ');
    expect(missing, isNot(contains('Aadhaar')));
    expect(missing, isNot(contains('Land record')));

    // The only genuinely missing document and the unknown profile fact.
    expect(missing, contains('Bank account proof'));
    expect(missing, contains('Income-tax payer'));
  });

  test('CASE 8: legacy document-alias rules are resolved to held evidence', () {
    final match = RecommendationMatch(
      id: 'rec-1',
      schemeId: 'pm-kisan',
      schemeName: 'PM-KISAN',
      eligibilityStatus: 'insufficient_information',
      eligibilityPercentage: 0,
      confidenceScore: 0,
      rankingPosition: 1,
      matchedRules: const [],
      // Legacy snapshot references land_record through a requirement alias.
      missingRequirements: [
        _rule('land_ownership_proof', result: 'UNKNOWN'),
      ],
      requiredDocuments: const ['aadhaar', 'land_record', 'bank_account'],
      evidenceChecklist: [
        for (final entry in _fullPmKisanMatch().evidenceChecklist) entry,
      ],
    );

    expect(match.ruleEvidenceAlreadyHeld(match.missingRequirements.single),
        isTrue);
    expect(match.cardMissingBullets.join(' '), isNot(contains('Land record')));
    expect(match.cardMissingBullets.join(' '), contains('Bank account proof'));
  });

  test('TASK 8: raw letterhead text is never a scheme description', () {
    expect(_matchWithDescription('NewDelhi-110001').cardDescription, isNull);
    expect(_matchWithDescription('New Delhi - 110001').cardDescription,
        isNull);
    final ocr = _matchWithDescription(
            '1 PRADHAN MANTRI KISAN SAMMAN NIDHI SCHEME Krishi Bhawan NewDelhi-110001')
        .cardDescription;
    expect(ocr == null || (!ocr.contains('NewDelhi') && !ocr.contains('110001')),
        isTrue);
    expect(
        _matchWithDescription('Income support for eligible farmers.'),
        isNotNull);
  });
}

RecommendationRule _rule(
  String condition, {
  String result = '',
  bool passed = false,
  bool mandatory = true,
  String? notes,
}) {
  return RecommendationRule(
    ruleCode: condition,
    condition: condition,
    operator: '==',
    passed: passed,
    result: result,
    mandatory: mandatory,
    notes: notes,
  );
}

RecommendationMatch _matchWithBenefit(String? estimated) =>
    RecommendationMatch(
      id: 'rec-1',
      schemeId: 's-1',
      schemeName: 'Scheme',
      eligibilityStatus: 'eligible',
      eligibilityPercentage: 0,
      confidenceScore: 0,
      rankingPosition: 1,
      estimatedBenefit: estimated,
    );

RecommendationMatch _matchWithDescription(String description) =>
    RecommendationMatch(
      id: 'rec-1',
      schemeId: 's-1',
      schemeName: 'Scheme',
      eligibilityStatus: 'eligible',
      eligibilityPercentage: 0,
      confidenceScore: 0,
      rankingPosition: 1,
      description: description,
    );

