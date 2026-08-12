import 'package:flutter/foundation.dart';

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

  factory EligibilityRuleResult.fromJson(Map<String, dynamic> json) {
    return EligibilityRuleResult(
      ruleCode: (json['rule_code'] ?? '').toString(),
      condition: (json['condition'] ?? '').toString(),
      operator: (json['operator'] ?? '').toString(),
      expectedValue: json['expected_value'],
      actualValue: json['actual_value'],
      passed: json['passed'] == true,
      priority: int.tryParse(json['priority']?.toString() ?? ''),
      description: json['description']?.toString(),
      source: json['source']?.toString(),
    );
  }

  String get displayTitle {
    if ((description ?? '').isNotEmpty) {
      return description!;
    }
    if (condition.isNotEmpty) {
      return condition;
    }
    return ruleCode.isEmpty ? 'Eligibility rule' : ruleCode;
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
    required this.matchedRules,
    required this.failedRules,
    required this.requiredDocuments,
    required this.applicationReady,
    required this.reasoning,
  });

  final String citizenId;
  final DateTime? evaluatedAt;
  final int totalRules;
  final int passedRules;
  final double eligibilityPercentage;
  final bool eligible;
  final List<EligibilityRuleResult> matchedRules;
  final List<EligibilityRuleResult> failedRules;
  final List<String> requiredDocuments;
  final bool applicationReady;
  final String reasoning;

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
      matchedRules: _rules(data['matched_rules']),
      failedRules: _rules(data['missing_requirements']),
      requiredDocuments: (data['required_documents'] as List? ?? const [])
          .map((item) => item.toString())
          .where((item) => item.trim().isNotEmpty)
          .toList(),
      applicationReady: data['application_ready'] == true,
      reasoning: (data['reasoning'] ?? '').toString(),
    );
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
