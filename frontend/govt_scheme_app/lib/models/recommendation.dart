import 'package:flutter/foundation.dart';

@immutable
class RecommendationRule {
  const RecommendationRule({
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

  factory RecommendationRule.fromJson(Map<String, dynamic> json) {
    return RecommendationRule(
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
    return ruleCode.isEmpty ? 'Rule' : ruleCode;
  }

  bool get looksDocumentRelated {
    final text = '$ruleCode $condition $description $source'.toLowerCase();
    return text.contains('document') ||
        text.contains('aadhaar') ||
        text.contains('certificate') ||
        text.contains('ration') ||
        text.contains('land record') ||
        text.contains('income proof') ||
        text.contains('required_documents');
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
class RecommendationMatch {
  const RecommendationMatch({
    required this.id,
    required this.schemeId,
    required this.schemeName,
    required this.eligibilityStatus,
    required this.eligibilityPercentage,
    required this.confidenceScore,
    required this.rankingPosition,
    this.historyId,
    this.description,
    this.benefits,
    this.similarityScore = 0,
    this.overallScore = 0,
    this.recommendationReason,
    this.matchedRules = const [],
    this.missingRequirements = const [],
    this.requiredDocuments = const [],
    this.estimatedBenefit,
    this.applicationReady = false,
    this.profileMatchPercentage = 0,
    this.semanticQuery,
    this.createdAt,
  });

  final String id;
  final String? historyId;
  final String schemeId;
  final String schemeName;
  final String? description;
  final String? benefits;
  final String eligibilityStatus;
  final double eligibilityPercentage;
  final double similarityScore;
  final double confidenceScore;
  final double overallScore;
  final int rankingPosition;
  final String? recommendationReason;
  final List<RecommendationRule> matchedRules;
  final List<RecommendationRule> missingRequirements;
  final List<String> requiredDocuments;
  final String? estimatedBenefit;
  final bool applicationReady;
  final double profileMatchPercentage;
  final String? semanticQuery;
  final DateTime? createdAt;

  bool get isEligible => eligibilityStatus.toLowerCase() == 'eligible';

  factory RecommendationMatch.fromJson(Map<String, dynamic> json) {
    return RecommendationMatch(
      id: (json['id'] ?? json['recommendation_id'] ?? '').toString(),
      historyId: json['history_id']?.toString(),
      schemeId: (json['scheme_id'] ?? '').toString(),
      schemeName: (json['scheme_name'] ?? 'Untitled scheme').toString(),
      description: json['description']?.toString(),
      benefits: json['benefits']?.toString(),
      eligibilityStatus:
          (json['eligibility_status'] ??
                  json['eligibilityStatus'] ??
                  'ineligible')
              .toString(),
      eligibilityPercentage: _toDouble(json['eligibility_percentage']),
      similarityScore: _toDouble(json['similarity_score']),
      confidenceScore: _toDouble(json['confidence_score']),
      overallScore: _toDouble(json['overall_score']),
      rankingPosition:
          int.tryParse(json['ranking_position']?.toString() ?? '') ?? 0,
      recommendationReason: json['recommendation_reason']?.toString(),
      matchedRules: _rules(json['matched_rules']),
      missingRequirements: _rules(json['missing_requirements']),
      requiredDocuments: _stringList(json['required_documents']),
      estimatedBenefit: json['estimated_benefit']?.toString(),
      applicationReady: json['application_ready'] == true,
      profileMatchPercentage: _toDouble(json['profile_match_percentage']),
      semanticQuery: json['semantic_query']?.toString(),
      createdAt: _parseDate(json['created_at']),
    );
  }

  static double _toDouble(Object? value) {
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  static List<RecommendationRule> _rules(Object? value) {
    return (value as List? ?? const [])
        .whereType<Map>()
        .map(
          (item) =>
              RecommendationRule.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  static List<String> _stringList(Object? value) {
    return (value as List? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.trim().isNotEmpty)
        .toList();
  }

  static DateTime? _parseDate(Object? value) {
    if (value == null) {
      return null;
    }
    if (value is DateTime) {
      return value;
    }
    if (value is String && value.isNotEmpty) {
      return DateTime.tryParse(value);
    }
    return null;
  }
}

@immutable
class RecommendationHistory {
  const RecommendationHistory({
    required this.id,
    required this.requestType,
    required this.totalCandidates,
    required this.eligibleCount,
    required this.overallConfidence,
    required this.status,
    required this.createdAt,
    this.queryText,
    this.topK = 0,
    this.executionTimeMs = 0,
    this.contextSnapshot,
    this.matches = const [],
  });

  final String id;
  final String requestType;
  final String? queryText;
  final int topK;
  final int totalCandidates;
  final int eligibleCount;
  final double overallConfidence;
  final String status;
  final int executionTimeMs;
  final Object? contextSnapshot;
  final DateTime? createdAt;
  final List<RecommendationMatch> matches;

  factory RecommendationHistory.fromJson(Map<String, dynamic> json) {
    return RecommendationHistory(
      id: (json['id'] ?? '').toString(),
      requestType: (json['request_type'] ?? 'generate').toString(),
      queryText: json['query_text']?.toString(),
      topK: int.tryParse(json['top_k']?.toString() ?? '') ?? 0,
      totalCandidates:
          int.tryParse(json['total_candidates']?.toString() ?? '') ?? 0,
      eligibleCount:
          int.tryParse(json['eligible_count']?.toString() ?? '') ?? 0,
      overallConfidence:
          double.tryParse(json['overall_confidence']?.toString() ?? '') ?? 0,
      status: (json['status'] ?? 'completed').toString(),
      executionTimeMs:
          int.tryParse(json['execution_time_ms']?.toString() ?? '') ?? 0,
      contextSnapshot: json['context_snapshot'],
      createdAt: _parseDate(json['created_at']),
      matches: (json['matches'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (item) =>
                RecommendationMatch.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
    );
  }

  static DateTime? _parseDate(Object? value) {
    if (value == null) {
      return null;
    }
    if (value is DateTime) {
      return value;
    }
    if (value is String && value.isNotEmpty) {
      return DateTime.tryParse(value);
    }
    return null;
  }
}

@immutable
class RecommendationSummary {
  const RecommendationSummary({
    required this.citizenId,
    required this.totalCandidates,
    required this.eligibleCount,
    required this.overallConfidence,
    required this.recommendations,
    required this.history,
    this.generatedAt,
    this.topRankedScheme,
  });

  final String citizenId;
  final DateTime? generatedAt;
  final int totalCandidates;
  final int eligibleCount;
  final String? topRankedScheme;
  final double overallConfidence;
  final List<RecommendationMatch> recommendations;
  final RecommendationHistory history;

  factory RecommendationSummary.fromJson(Map<String, dynamic> json) {
    return RecommendationSummary(
      citizenId: (json['citizen_id'] ?? '').toString(),
      generatedAt: RecommendationMatch._parseDate(json['generated_at']),
      totalCandidates:
          int.tryParse(json['total_candidates']?.toString() ?? '') ?? 0,
      eligibleCount:
          int.tryParse(json['eligible_count']?.toString() ?? '') ?? 0,
      topRankedScheme: json['top_ranked_scheme']?.toString(),
      overallConfidence:
          double.tryParse(json['overall_confidence']?.toString() ?? '') ?? 0,
      recommendations: (json['recommendations'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (item) =>
                RecommendationMatch.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
      history: RecommendationHistory.fromJson(
        json['history'] is Map<String, dynamic>
            ? Map<String, dynamic>.from(json['history'] as Map)
            : const <String, dynamic>{},
      ),
    );
  }
}
