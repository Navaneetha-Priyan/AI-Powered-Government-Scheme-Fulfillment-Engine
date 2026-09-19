import 'package:flutter_test/flutter_test.dart';

import 'package:govt_scheme_app/core/presentation/eligibility_presenter.dart';
import 'package:govt_scheme_app/core/utils/evidence_mapping.dart';
import 'package:govt_scheme_app/models/eligibility.dart';

class _Sentinel {
  const _Sentinel();
}

const _sentinel = _Sentinel();

Map<String, dynamic> _checklistEntry(
  String requirement,
  String label,
  String kind,
  String status, {
  String? profilePrompt,
}) =>
    {
      'requirement': requirement,
      'label': label,
      'kind': kind,
      'status': status,
      if (profilePrompt case final prompt) 'profile_prompt': prompt,
    };

Set<String> _heldRequirementWords(Object? checklistRaw) {
  final entries = _entries(checklistRaw);
  final words = <String>{};
  for (final entry in entries) {
    if (!entry.status.isHeld) continue;
    words.add(entry.requirement.trim().toLowerCase());
    words.addAll(entry.label
        .toLowerCase()
        .split(RegExp(r'[^a-z0-9]+'))
        .where((word) => word.length > 3));
  }
  return words;
}

EligibilityRuleResult _ruleForChecklistTest(
  String condition, {
  Set<String> heldWords = const {},
  String result = 'UNKNOWN',
  String? notes,
  String? description,
  String? actual,
}) {
  if (result != 'UNKNOWN') {
    return _rule(condition,
        result: result, notes: notes, description: description, actual: actual);
  }
  final words = condition.toLowerCase().split(RegExp(r'[^a-z0-9]+'));
  if (words.any(heldWords.contains)) {
    // Held evidence satisfies this document-like rule, so the engine would
    // not report it as missing.
    return _rule(condition,
        result: 'PASS', passed: true, notes: notes, description: description);
  }
  return _rule(condition,
      result: result,
      notes: notes,
      description: description,
      actual: actual);
}

Object? _asEntryList(Object? checklist) {
  if (checklist == _sentinel) {
    return [
      _checklistEntry('aadhaar', 'Aadhaar', 'document', 'verified'),
      _checklistEntry('land_record', 'Land record', 'document', 'verified'),
      _checklistEntry(
          'bank_account', 'Bank account proof', 'document', 'needed'),
    ];
  }
  return checklist as List<Map<String, dynamic>>?;
}

List<EvidenceChecklistEntry> _entries(Object? raw) {
  final list = _asEntryList(raw);
  if (list == null) return const [];
  return (list as List)
      .whereType<Map>()
      .map((item) =>
          EvidenceChecklistEntry.fromJson(Map<String, dynamic>.from(item)))
      .toList();
}

EligibilityCheck _authoritativeCheck({
  String status = 'insufficient_information',
  Object? failed = _sentinel,
  Object? checklist = _sentinel,
  List<String> docs = const ['aadhaar', 'land_record', 'bank_account'],
}) {
  final heldWords = _heldRequirementWords(checklist);
  return EligibilityCheck(
    citizenId: 'c-1',
    evaluatedAt: DateTime(2026),
    totalRules: 4,
    passedRules: 3,
    eligibilityPercentage: 0,
    eligible: false,
    eligibilityStatus: status,
    matchedRules: const [],
    failedRules: failed == _sentinel
        ? [
            _rule('income_tax_payer',
                result: 'UNKNOWN', actual: null, notes: 'Not provided.'),
            // Legacy document-ish rule aliases stay missing only when the
            // authoritative checklist does NOT already hold the evidence.
            _ruleForChecklistTest(
                'pm-kisan-aadhaar',
                heldWords: heldWords,
                description: 'Aadhaar'),
            _ruleForChecklistTest(
                'land_ownership_proof', heldWords: heldWords),
          ]
        : (failed as List<EligibilityRuleResult>),
    requiredDocuments: docs,
    applicationReady: false,
    reasoning: '',
    mandatoryRulesTotal: 4,
    mandatoryRulesPassed: 3,
    evidenceChecklist: _entries(checklist),
  );
}


EligibilityRuleResult _rule(
  String condition, {
  String result = '',
  bool passed = false,
  String? notes,
  String? description,
  String? actual,
}) {
  return EligibilityRuleResult(
    ruleCode: 'r-1',
    condition: condition,
    operator: '==',
    passed: passed,
    actualValue: actual,
    description: description,
    result: result,
    notes: notes,
  );
}

EligibilityCheck _check({
  String status = 'eligible',
  bool eligible = true,
  bool applicationReady = true,
  List<EligibilityRuleResult> matched = const [],
  List<EligibilityRuleResult> failed = const [],
  List<String> docs = const [],
  int mandatoryTotal = 0,
  int mandatoryPassed = 0,
}) {
  return EligibilityCheck(
    citizenId: 'c-1',
    evaluatedAt: DateTime(2026),
    totalRules: matched.length + failed.length,
    passedRules: matched.length,
    eligibilityPercentage: 0,
    eligible: eligible,
    eligibilityStatus: status,
    matchedRules: matched,
    failedRules: failed,
    requiredDocuments: docs,
    applicationReady: applicationReady,
    reasoning: 'SMAM: Not Eligible | Matched: land_record | Benefit: , N | 7%',
    mandatoryRulesTotal: mandatoryTotal,
    mandatoryRulesPassed: mandatoryPassed,
  );
}

void main() {
  const presenter = EligibilityPresentationPresenter();

  test('PASS conditions become why-you-match sentences with the count', () {
    final presentation = presenter.present(_check(
      status: 'eligible',
      matched: [
        _rule('is_farmer',
            result: 'PASS',
            passed: true,
            notes: 'Citizen is a registered farmer.'),
        _rule('age',
            result: 'PASS',
            passed: true,
            notes: 'Citizen age is within the scheme limit.'),
      ],
      mandatoryTotal: 2,
      mandatoryPassed: 2,
    ));

    expect(presentation.status, EligibilityStatus.eligible);
    expect(presentation.statusLabel, 'You may be eligible');
    expect(presentation.conditionSummary, '2 of 2 conditions met');
    expect(presentation.whyYouMatch, hasLength(2));
    expect(presentation.whyYouMatch.first, 'Citizen is a registered farmer.');
  });

  test('FAIL conditions produce a not-eligible citizen status', () {
    final presentation = presenter.present(_check(
      status: 'not_eligible',
      eligible: false,
      applicationReady: false,
      matched: [_rule('age', result: 'PASS', passed: true)],
      failed: [
        _rule('annual_income',
            result: 'FAIL', notes: 'Income exceeds the scheme limit.'),
      ],
      mandatoryTotal: 2,
      mandatoryPassed: 1,
    ));

    expect(presentation.status, EligibilityStatus.notEligible);
    expect(presentation.statusLabel, 'You are not currently eligible');
    expect(presentation.conditionSummary, '1 of 2 conditions met');
  });

  test('UNKNOWN conditions mean more information needed, never a failure', () {
    final presentation = presenter.present(_check(
      status: 'insufficient_information',
      eligible: false,
      applicationReady: false,
      failed: [
        _rule('pregnancy_status', result: 'UNKNOWN', actual: null),
      ],
      mandatoryTotal: 1,
      mandatoryPassed: 0,
    ));

    expect(presentation.status, EligibilityStatus.insufficientInformation);
    expect(presentation.statusLabel, 'More information needed');
    expect(presentation.missingInformation.join(' '),
        contains('Pregnancy status'));
    expect(presentation.missingInformation.join(' '),
        isNot(contains('pregnancy_status')));
  });

  test('mixed FAIL + UNKNOWN keeps the deterministic not-eligible decision',
      () {
    final presentation = presenter.present(_check(
      status: 'not_eligible',
      eligible: false,
      applicationReady: false,
      failed: [
        _rule('annual_income', result: 'FAIL'),
        _rule('caste', result: 'UNKNOWN'),
      ],
    ));

    expect(presentation.status, EligibilityStatus.notEligible);
  });

  test('failed document conditions become upload prompts, not rejections', () {
    final presentation = presenter.present(_check(
      status: 'insufficient_information',
      eligible: false,
      applicationReady: false,
      failed: [
        _rule('land_ownership_proof', result: 'FAIL', actual: null),
      ],
      docs: const ['land_record', 'bank_account'],
    ));

    final all = [
      ...presentation.missingDocuments,
      ...presentation.missingInformation,
    ].join(' ');
    expect(all, contains('Land record'));
    expect(all, contains('Bank account proof'));
    expect(all, isNot(contains('land_record')));
    expect(all, isNot(contains('bank_account')));
    // Document gaps never flip the backend decision to a rejection.
    expect(presentation.status, EligibilityStatus.insufficientInformation);
  });

  test('legacy payloads without a result fall back to passed + heuristics',
      () {
    final presentation = presenter.present(_check(
      status: 'not_eligible',
      eligible: false,
      applicationReady: false,
      failed: [
        // No result key, no actual value → UNKNOWN, not a hard failure.
        _rule('occupation', actual: null),
        // No result key but a real value that failed → genuine FAIL.
        _rule('age', actual: '35'),
      ],
    ));

    expect(presentation.status, EligibilityStatus.notEligible);
    expect(presentation.missingInformation, isNotEmpty);
  });

  test('raw backend metrics never leak into the citizen presentation', () {
    final presentation = presenter.present(_check(
      status: 'potentially_eligible',
      eligible: false,
      applicationReady: false,
      matched: [_rule('is_farmer', result: 'PASS', passed: true)],
      failed: [_rule('land_area', result: 'UNKNOWN')],
      docs: const ['land_record'],
    ));

    final rendered = [
      presentation.statusLabel,
      presentation.conditionSummary ?? '',
      ...presentation.whyYouMatch,
      ...presentation.missingDocuments,
      ...presentation.missingInformation,
      presentation.benefitSummary,
    ].join(' ');
    expect(rendered, isNot(contains('7%')));
    expect(rendered, isNot(contains('Benefit:')));
    expect(rendered, isNot(contains('land_record')));
    expect(rendered, isNot(contains('Expected')));
    expect(rendered, isNot(contains('Current')));
    // Raw status text is never shown; unknown statuses map conservatively.
    expect(presentation.statusLabel, 'More information needed');
  });

  test('status mapping is deterministic and conservative', () {
    expect(EligibilityPresentationPresenter.citizenStatusLabel('eligible'),
        'You may be eligible');
    expect(
        EligibilityPresentationPresenter.citizenStatusLabel(
            'potentially_eligible'),
        'More information needed');
    expect(
        EligibilityPresentationPresenter.citizenStatusLabel(
            'insufficient_information'),
        'More information needed');
    expect(EligibilityPresentationPresenter.citizenStatusLabel('not_eligible'),
        'You are not currently eligible');
    expect(
        EligibilityPresentationPresenter.citizenStatusLabel(
            'manual_review_required'),
        'Manual verification required');
    expect(EligibilityPresentationPresenter.citizenStatusLabel(''),
        'Information not available');
    expect(
        EligibilityPresentationPresenter.citizenStatusLabel('some_new_status'),
        'Information not available');
  });


  group('authoritative evidence checklist (CASE 1/2/3/8)', () {
    test('verified documents are never reported as missing', () {
      final presentation = presenter.present(_authoritativeCheck());

      final missing = presentation.missingDocuments.join(' ');
      expect(missing, isNot(contains('Aadhaar')));
      expect(missing, isNot(contains('Land record')));
      expect(
        missing, contains('You still need to provide Bank account proof.'));
    });

    test('unknown profile facts stay out of the document list', () {
      final presentation = presenter.present(_authoritativeCheck());

      expect(presentation.missingDocuments, hasLength(1));
      // income_tax_payer is a profile fact: it lands in "information needed"
      // with its curated backend note, never as a missing document.
      expect(presentation.missingInformation.single, 'Not provided.');
      expect(presentation.missingInformation.join(' '),
          isNot(contains('Aadhaar')));
    });

    test('checklist and rule bullets cannot contradict each other', () {
      final check = _authoritativeCheck();
      final presentation = presenter.present(check);
      final held = check.evidenceChecklist
          .where((entry) => entry.status.isHeld)
          .map((entry) => entry.label)
          .toSet();
      final reported = [
        ...presentation.missingDocuments,
        ...presentation.missingInformation,
      ].join(' ');
      for (final label in held) {
        expect(reported, isNot(contains('provide $label.')));
      }
    });

    test('pending evidence is treated as present, not missing', () {
      final presentation = presenter.present(_authoritativeCheck(
        checklist: [
          _checklistEntry('aadhaar', 'Aadhaar', 'document', 'pending'),
          _checklistEntry('land_record', 'Land record', 'document', 'available'),
          _checklistEntry(
              'bank_account', 'Bank account proof', 'document', 'needed'),
        ],
      ));

      expect(presentation.missingDocuments, hasLength(1));
      expect(presentation.missingDocuments.single,
          contains('Bank account proof'));
    });
  });

  test('next action routes citizens to the right fix', () {
    final withDocs = presenter.present(_check(
      status: 'insufficient_information',
      eligible: false,
      applicationReady: false,
      failed: [_rule('land_ownership_proof', result: 'FAIL')],
      docs: const ['land_record'],
    ));
    expect(withDocs.nextAction, NextAction.uploadDocuments);

    final ready = presenter.present(_check(
      status: 'eligible',
      matched: [_rule('age', result: 'PASS', passed: true)],
      mandatoryTotal: 1,
      mandatoryPassed: 1,
    ));
    expect(ready.nextAction, NextAction.proceedToApplication);
  });
}
