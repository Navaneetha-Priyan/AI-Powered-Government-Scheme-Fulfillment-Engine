import 'package:flutter/foundation.dart';

import '../core/utils/evidence_mapping.dart';

@immutable
class EligibilityRuleResult {
  const EligibilityRuleResult({
    required this.ruleCode,
    required this.condition,
    required this.operator,
    required this.passed,
    this.expectedValue,
    this.actualValue,
    this.priority,
    this.description,
    this.source,
    this.result = '',
    this.notes,
    this.mandatory = true,
  });

  final String ruleCode;
  final String condition;
  final String operator;
  final bool passed;
  final Object? expectedValue;
  final Object? actualValue;
  final int? priority;
  final String? description;
  final String? source;

  /// Structured evaluator result: PASS / FAIL / UNKNOWN / NOT_APPLICABLE.
  /// Empty for legacy payloads, which only carry [passed].
  final String result;

  /// Curated citizen-facing explanation emitted by the catalogue evaluator.
  final String? notes;

  /// Whether failing this condition blocks eligibility. Legacy payloads
  /// without a `mandatory` key default to true (conservative).
  final bool mandatory;

  factory EligibilityRuleResult.fromJson(Map<String, dynamic> json) {
    return EligibilityRuleResult(
      ruleCode: (json['rule_code'] ?? json['rule_id'] ?? '').toString(),
      condition: (json['condition'] ?? '').toString(),
      operator: (json['operator'] ?? '').toString(),
      expectedValue: json['expected_value'],
      actualValue: json['actual_value'],
      passed: json['passed'] == true,
      priority: int.tryParse(json['priority']?.toString() ?? ''),
      description: json['description']?.toString(),
      source: json['source']?.toString(),
      result: (json['result'] ?? '').toString(),
      notes: json['notes']?.toString(),
      mandatory: json['mandatory'] != false &&
          (json['severity']?.toString() ?? '') != 'optional',
    );
  }

  /// Normalized condition result used by the presentation layer.
  ///
  /// Legacy payloads (no `result`) fall back to the `passed` flag plus the
  /// missing-value heuristic: an unfilled condition cannot fail, it is
  /// simply unknown.
  String get effectiveResult {
    final r = result.trim().toUpperCase();
    if (r.isNotEmpty) return r;
    if (passed) return 'PASS';
    return hasMissingProfileValue ? 'UNKNOWN' : 'FAIL';
  }

  bool get isConditionPass => effectiveResult == 'PASS';

  bool get isConditionUnknown => effectiveResult == 'UNKNOWN';

  bool get isConditionFail => effectiveResult == 'FAIL';

  /// Whether this condition participates in the "N of M conditions met"
  /// citizen summary (mandatory and actually evaluated).
  bool get isConditionCountable =>
      mandatory && effectiveResult != 'NOT_APPLICABLE';

  String get displayTitle {
    if ((description ?? '').isNotEmpty) {
      return description!;
    }
    if (condition.isNotEmpty) {
      return condition;
    }
    return ruleCode.isEmpty ? 'Eligibility rule' : ruleCode;
  }

  /// Normalized evidence key for mapping (e.g. "identity_proof").
  String get evidenceKey {
    for (final candidate in [condition, ruleCode, description ?? '', source ?? '']) {
      final key = candidate.trim().toLowerCase().replaceAll(' ', '_');
      if (key.isNotEmpty && RegExp(r'^[a-z0-9_]+$').hasMatch(key)) return key;
    }
    return displayTitle.trim().toLowerCase().replaceAll(' ', '_');
  }

  bool get looksDocumentRelated {
    final text = '$ruleCode $condition $description $source'.toLowerCase();
    return text.contains('document') ||
        text.contains('aadhaar') ||
        text.contains('certificate') ||
        text.contains('ration') ||
        text.contains('land record') ||
        text.contains('income proof');
  }

  bool get hasMissingProfileValue {
    if (looksDocumentRelated) {
      return false;
    }
    final value = actualValue;
    if (value == null) {
      return true;
    }
    if (value is String) {
      return value.trim().isEmpty || value.toLowerCase() == 'unknown';
    }
    if (value is Iterable) {
      return value.isEmpty;
    }
    if (value is Map) {
      return value.isEmpty;
    }
    return false;
  }
}

@immutable
class EligibilityCheck {
  const EligibilityCheck({
    required this.citizenId,
    required this.evaluatedAt,
    required this.totalRules,
    required this.passedRules,
    required this.eligibilityPercentage,
    required this.eligible,
    required this.eligibilityStatus,
    required this.matchedRules,
    required this.failedRules,
    required this.requiredDocuments,
    required this.applicationReady,
    required this.reasoning,
    this.mandatoryRulesTotal = 0,
    this.mandatoryRulesPassed = 0,
    this.evidenceChecklist = const [],
  });

  final String citizenId;
  final DateTime? evaluatedAt;
  final int totalRules;
  final int passedRules;
  final double eligibilityPercentage;
  final bool eligible;
  final String eligibilityStatus;
  final List<EligibilityRuleResult> matchedRules;
  final List<EligibilityRuleResult> failedRules;
  final List<String> requiredDocuments;
  final bool applicationReady;
  final String reasoning;

  /// Backend-computed citizen-presentable condition counts
  /// ("N of M conditions met"). 0 means the backend predates the field.
  final int mandatoryRulesTotal;
  final int mandatoryRulesPassed;

  /// Backend-computed evidence checklist with human-readable labels
  /// (source of truth when present). Falls back to local mapping.
  final List<EvidenceChecklistEntry> evidenceChecklist;

  factory EligibilityCheck.fromJson(Map<String, dynamic> json) {
    final data = json['data'] is Map<String, dynamic>
        ? Map<String, dynamic>.from(json['data'] as Map)
        : json;

    return EligibilityCheck(
      citizenId: (data['citizen_id'] ?? '').toString(),
      evaluatedAt: DateTime.tryParse(data['evaluated_at']?.toString() ?? ''),
      totalRules: int.tryParse(data['total_rules']?.toString() ?? '') ?? 0,
      passedRules: int.tryParse(data['passed_rules']?.toString() ?? '') ?? 0,
      eligibilityPercentage:
          double.tryParse(data['eligibility_percentage']?.toString() ?? '') ??
          0,
      eligible: data['eligible'] == true,
      eligibilityStatus: (data['eligibility_status'] ??
              (data['eligible'] == true ? 'eligible' : 'not_eligible'))
          .toString(),
      matchedRules: _rules(data['matched_rules']),
      failedRules: _rules(data['missing_requirements']),
      requiredDocuments: (data['required_documents'] as List? ?? const [])
          .map((item) => item.toString())
          .where((item) => item.trim().isNotEmpty)
          .toList(),
      applicationReady: data['application_ready'] == true,
      reasoning: (data['reasoning'] ?? '').toString(),
      mandatoryRulesTotal:
          int.tryParse(data['mandatory_rules_total']?.toString() ?? '') ?? 0,
      mandatoryRulesPassed:
          int.tryParse(data['mandatory_rules_passed']?.toString() ?? '') ?? 0,
      evidenceChecklist: (data['evidence_checklist'] as List? ?? const [])
          .whereType<Map>()
          .map((item) =>
              EvidenceChecklistEntry.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
    );
  }

  /// Citizen-presentable mandatory condition counts. Prefers the backend
  /// counts when present; otherwise derives them from the structured rule
  /// lists (PASS/FAIL/UNKNOWN aware, skipping optional and non-applicable
  /// conditions). Returns null when nothing was evaluated.
  ({int passed, int total})? get mandatoryConditionCounts {
    var total = mandatoryRulesTotal;
    var passed = mandatoryRulesPassed;
    if (total <= 0) {
      final countable = [
        ...matchedRules,
        ...failedRules,
      ].where((rule) => rule.isConditionCountable).toList();
      total = countable.length;
      passed = countable.where((rule) => rule.isConditionPass).length;
    }
    if (total <= 0) return null;
    return (passed: passed, total: total);
  }

  /// Citizen-facing "N of M conditions met" summary, or null when no
  /// mandatory conditions were evaluated.
  String? get conditionSummary {
    final counts = mandatoryConditionCounts;
    if (counts == null) return null;
    return '${counts.passed} of ${counts.total} conditions met';
  }

  static List<EligibilityRuleResult> _rules(Object? value) {
    return (value as List? ?? const [])
        .whereType<Map>()
        .map(
          (item) =>
              EligibilityRuleResult.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  List<EligibilityRuleResult> get missingProfileInformation {
    return failedRules.where((rule) => rule.hasMissingProfileValue).toList();
  }

  List<String> get missingDocuments {
    final documentFailures = failedRules
        .where((rule) => rule.looksDocumentRelated)
        .map((rule) => rule.expectedValue?.toString() ?? rule.condition)
        .where((item) => item.trim().isNotEmpty)
        .toSet();

    if (documentFailures.isNotEmpty) {
      return documentFailures.toList();
    }

    if (!applicationReady && requiredDocuments.isNotEmpty) {
      return requiredDocuments;
    }

    return const [];
  }
}
