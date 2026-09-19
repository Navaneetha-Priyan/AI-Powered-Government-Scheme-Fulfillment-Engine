import 'package:flutter/foundation.dart';

import '../core/utils/evidence_mapping.dart';
import '../core/utils/presentation_text.dart';

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

  factory RecommendationRule.fromJson(Map<String, dynamic> json) {
    return RecommendationRule(
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
    return ruleCode.isEmpty ? 'Rule' : ruleCode;
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
    final text = '$ruleCode $condition $description $source'
        .toLowerCase()
        .replaceAll('_', ' ');
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
    this.evidenceChecklist = const [],
    this.mandatoryRulesTotal = 0,
    this.mandatoryRulesPassed = 0,
    this.displayName,
    this.shortDescription,
    this.benefitsList = const [],
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

  /// Backend-computed evidence checklist (source of truth when present).
  /// Falls back to the local adapter when the payload predates the field.
  final List<EvidenceChecklistEntry> evidenceChecklist;

  /// Backend-computed citizen-presentable condition counts ("N of M
  /// conditions met"). 0 means the backend predates the field; the local
  /// rule lists are used instead.
  final int mandatoryRulesTotal;
  final int mandatoryRulesPassed;

  /// ── Structured citizen presentation (from curated presentation metadata) ──
  /// `displayName` is a clean human-readable scheme name; `shortDescription`
  /// is a short citizen-friendly summary; `benefitsList` holds short benefit
  /// bullets. All are grounded in the scheme source PDFs (curated on the
  /// backend) — raw PDF extraction is never delivered in these fields.
  final String? displayName;
  final String? shortDescription;
  final List<String> benefitsList;

  /// Safe fallback when no clean presentation summary exists.
  static const String aboutFallback =
      'Information about this scheme is being prepared.';

  /// Clean name for headings/cards. Falls back to the raw backend scheme
  /// name (which is a short catalog title, not PDF extraction).
  String get displayTitle {
    final clean = _sanitize(reason: displayName, max: 120);
    if (clean != null && clean.isNotEmpty) return clean;
    return schemeName;
  }

  /// Citizen-safe short description for "About this scheme", or null when
  /// nothing clean exists (callers then show [aboutFallback]). Corrupted /
  /// PDF-extraction content is rejected outright — raw `description` and RAG
  /// `matched_content`/`relevant_content` are never used as a fallback.
  String? get cleanShortDescription =>
      cleanPresentationText(shortDescription, max: 400);

  /// Sanitized benefit bullets from the curated presentation metadata.
  /// Invalid/noisy bullets are dropped; when none remain the list is empty and
  /// callers omit the benefits section. Raw `benefits` / RAG content is never
  /// used as a fallback.
  List<String> get benefitBullets =>
      cleanPresentationList(benefitsList, max: 300);

  bool get isEligible => eligibilityStatus.toLowerCase() == 'eligible';

  /// ── Citizen-facing card fields ──────────────────────────────────────
  /// The backend keeps returning internal retrieval metadata (raw RAG chunks
  /// in [semanticQuery], file refs, page markers). The card must never show
  /// those; these getters expose only concise, sanitized citizen text.
  /// Full detail remains available via the detail screen / scheme screen.

  /// Short "why you match" summary, or null when nothing citizen-safe exists.
  String? get cardReason {
    final clean = _sanitize(reason: recommendationReason);
    if (clean == null) return null;
    if (_isNoise(recommendationReason) && clean.length > 120) return null;
    return clean;
  }

  /// Short benefit summary for the card, or null.
  ///
  /// NOTE: this is derived from the legacy backend `estimated_benefit` /
  /// `benefits` columns, which can contain raw extraction text. It must NOT be
  /// rendered in a citizen-facing benefits section — use [benefitBullets]
  /// (curated presentation metadata) instead.
  String? get cardBenefit {
    final est = _sanitize(reason: estimatedBenefit, max: 140);
    if (est != null && est.isNotEmpty) return est;
    if (_isNoise(benefits)) return null;
    return _sanitize(reason: benefits, max: 140);
  }

  /// Up to 3 short "why you match" bullets using citizen-safe labels
  /// (curated notes → evidence-mapping labels → sanitized titles).
  List<String> get cardMatchBullets {
    final seen = <String>{};
    final out = <String>[];
    for (final rule in matchedRules) {
      final label = _citizenBulletLabel(rule);
      if (label == null || label.isEmpty || seen.contains(label)) continue;
      seen.add(label);
      out.add(label);
      if (out.length >= 3) break;
    }
    return out;
  }

  /// Structured evidence checklist: 1) backend `evidence_checklist` when
  /// present (source of truth); 2) local adapter over required_documents
  /// + missing_requirements otherwise. Never exposes raw snake_case keys.
  List<EvidenceChecklistEntry> get evidenceItems {
    if (evidenceChecklist.isNotEmpty) return evidenceChecklist;
    final missingKeys = <String>{};
    for (final rule in missingRequirements) {
      final key = rule.evidenceKey;
      if (key.isNotEmpty) missingKeys.add(key);
    }
    for (final doc in requiredDocuments) {
      if (ruleKeyInMissing(doc)) {
        missingKeys.add(doc.trim().toLowerCase());
      }
    }
    return resolveEvidenceChecklist(
      requiredDocuments.map((e) => e.toString()),
      uploadedDocumentTypes,
      missingOnly: missingKeys,
    );
  }

  /// Document types the citizen already holds (matched uploads only).
  Set<String> get uploadedDocumentTypes {
    final out = <String>{};
    for (final entry in evidenceChecklist) {
      final matched = entry.matchedDocumentType;
      if (entry.status.isHeld && matched != null) {
        out.add(matched.toLowerCase());
      }
    }
    return out;
  }

  bool ruleKeyInMissing(String doc) => missingRequirements.any(
        (rule) =>
            rule.evidenceKey == doc.trim().toLowerCase() ||
            rule.looksDocumentRelated &&
                rule.displayTitle.toLowerCase().contains(
                      doc.trim().toLowerCase().replaceAll('_', ' '),
                    ),
      );

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
        ...missingRequirements,
      ].where((rule) => rule.isConditionCountable).toList();
      total = countable.length;
      passed = countable.where((rule) => rule.isConditionPass).length;
    }
    if (total <= 0) return null;
    return (passed: passed, total: total);
  }

  /// "3 of 4 conditions met" — a factual count, never a percentage.
  String? get conditionSummary {
    final counts = mandatoryConditionCounts;
    if (counts == null) return null;
    return '${counts.passed} of ${counts.total} conditions met';
  }

  /// Sanitized, length-capped scheme description for the detail screen.
  /// Raw government-document dumps are reduced or dropped entirely.
  String? get cardDescription => _sanitize(reason: description, max: 400);

  /// Up to 3 short "more information needed" bullets.
  /// Document-like rules collapse into one entry; internal noise is dropped.
  List<String> get cardMissingBullets {
    final seen = <String>{};
    final out = <String>[];
    final heldEvidence = evidenceItems
        .where((entry) => entry.status.isHeld)
        .map((entry) => entry.requirement.trim().toLowerCase())
        .toSet();
    var docEntryAdded = false;
    for (final rule in missingRequirements) {
      final key = rule.evidenceKey.trim().toLowerCase();
      if (heldEvidence.contains(key) || ruleEvidenceAlreadyHeld(rule)) {
        continue;
      }
      if (rule.looksDocumentRelated) {
        if (evidenceChecklist.isEmpty) {
          final mapping = evidenceMappingFor(key);
          final label = mapping?.label;
          if (label != null && label.isNotEmpty && !seen.contains(label)) {
            seen.add(label);
            out.add(label);
          } else if (!docEntryAdded) {
            docEntryAdded = true;
            out.add('Supporting document, if applicable');
          }
          continue;
        }
        if (!docEntryAdded) {
          docEntryAdded = true;
          out.add('Supporting document, if applicable');
        }
        continue;
      }
      final label = _citizenBulletLabel(rule);
      if (label == null ||
          _isNoise(rule.displayTitle) ||
          seen.contains(label)) {
        continue;
      }
      seen.add(label);
      out.add(label);
      if (out.length >= 3) break;
    }
    if (evidenceChecklist.isNotEmpty) {
      for (final entry in evidenceItems) {
        if (out.length >= 3) break;
        if (entry.status.isHeld) continue;
        if (entry.status == EvidenceStatus.manual) continue;
        final label = entry.profilePrompt ?? entry.label;
        if (label.isEmpty || _isNoise(label) || seen.contains(label)) continue;
        seen.add(label);
        out.add(label);
      }
    } else {
      for (final doc in requiredDocuments) {
        if (out.length >= 3) break;
        final mapping = evidenceMappingFor(doc.trim().toLowerCase());
        final label = mapping?.label ?? _ruleLabel(doc);
        if (label.isEmpty || _isNoise(doc) || seen.contains(label)) continue;
        seen.add(label);
        out.add(label);
      }
    }
    return out;
  }

  /// Whether a canonical evidence item for a document-like rule is held.
  ///
  /// The authoritative checklist decides what the citizen already holds.
  /// Without this, a verified document (``land_record``) could still surface as
  /// missing because a rule references an equivalent requirement alias
  /// (``land_ownership_proof``). Only positively held evidence is matched —
  /// nothing is assumed.
  bool ruleEvidenceAlreadyHeld(RecommendationRule rule) {
    final key = rule.evidenceKey.trim().toLowerCase();
    if (key.isEmpty) return false;
    final held = evidenceItems.where((entry) => entry.status.isHeld).toList();
    if (held.isEmpty) return false;
    if (held.any((entry) => entry.requirement.trim().toLowerCase() == key)) {
      return true;
    }
    final mapping = evidenceMappingFor(key);
    if (mapping == null) return false;
    if (held.any((entry) =>
        entry.requirement.trim().toLowerCase() == mapping.requirement)) {
      return true;
    }
    final heldTypes = held
        .map((entry) => (entry.matchedDocumentType ?? '').toLowerCase())
        .where((type) => type.isNotEmpty)
        .toSet();
    if (mapping.documentTypes
        .any((type) => heldTypes.contains(type.toLowerCase()))) {
      return true;
    }
    return held
        .any((entry) => entry.label.toLowerCase() == mapping.label.toLowerCase());
  }

  /// Citizen-safe label for one rule: prefers the curated note, then the
  /// evidence-mapping label for document/profile requirements, then the
  /// sanitized display title. Returns null when nothing citizen-safe exists.
  static String? _citizenBulletLabel(RecommendationRule rule) {
    final note = (rule.notes ?? '').trim();
    if (note.isNotEmpty &&
        note.length <= 120 &&
        !_isNoise(note) &&
        !note.toLowerCase().contains('manual_review')) {
      return _ruleLabel(note);
    }
    final mapped = humanizeEvidenceRequirement(rule.evidenceKey);
    if (!mapped.toLowerCase().contains('requirement')) {
      return _ruleLabel(mapped);
    }
    final title = _ruleLabel(rule.displayTitle);
    if (title.isEmpty || _isNoise(title)) return null;
    return title;
  }

  static String _ruleLabel(String raw) {
    var label = raw.replaceAll('_', ' ').replaceAll('\n', ' ').trim();
    label = label.replaceAll(RegExp(r'\s+'), ' ').trim();
    label = label.replaceAll(RegExp(r'^[.,;:—\-]+|[.,;:—\-]+$'), '').trim();
    if (label.isEmpty) return '';
    const max = 90;
    if (label.length > max) {
      var cut = label.substring(0, max);
      final space = cut.lastIndexOf(' ');
      if (space > max * 0.6) cut = cut.substring(0, space);
      label = '$cut…';
    }
    return label[0].toUpperCase() + label.substring(1);
  }

  static String? _sanitize({String? reason, int max = 160}) {
    var text = (reason ?? '').replaceAll('\n', ' ').trim();
    if (text.isEmpty) return null;
    text = text.replaceAll(
        RegExp(r'[\w\-.]+\.(pdf|docx?|xlsx?|png|jpe?g)\b',
            caseSensitive: false),
        '');
    text = text.replaceAll(
        RegExp(
            r'\bpages?\s*\d+(\s*[-–]\s*\d+)?\b|\bpage\s*\d+\b|⋯?\s*Page\s*\d+.*',
            caseSensitive: false),
        '');
    text = text.replaceAll(
        RegExp(r'\bF\.?\s*No\.?[^,;\n]*|File\s*No\.?[^,;\n]*',
            caseSensitive: false),
        '');
    // Letterhead addresses / pincodes are OCR artifacts, never scheme prose.
    text = text.replaceAll(
        RegExp(
            r'\bnew\s*delhi\b\s*[-\u2013]?\s*(?:pin\s*(?:code)?\s*[-:]?\s*)?\d{0,6}',
            caseSensitive: false),
        '');
    text = text.replaceAll(
        RegExp(r'\b(?:pin\s*(?:code)?|pincode)\s*[-:]?\s*\d{6}\b',
            caseSensitive: false),
        '');
    if (text.length > 120) {
      text = text.replaceAll(
          RegExp(
              r'\b(government (of india|department|ministry)|ministry of|department of|ongoing scheme|guidelines?|operational guidelines?|chunk|section|retrieved|embedding|similarity)\b[^,.;\n]*[.,;]?',
              caseSensitive: false),
          '');
    }
    text = text.replaceAll(RegExp(r'\s+'), ' ').trim();
    text = text.replaceAll(RegExp(r'^[.,;:—\-]+|[.,;:—\-]+$'), '').trim();
    if (text.isEmpty) return null;
    // A leftover bare address/pincode is not a description.
    if (RegExp(r'^(?:new\s*delhi\s*[-\u2013]?\s*)?\d{6}$',
            caseSensitive: false)
        .hasMatch(text)) {
      return null;
    }
    // Letterhead fragments (short text dominated by an address) are not prose.
    if (text.length <= 120 &&
        RegExp(
                r'(newdelhi|new\s*delhi|krishi bhawan|kisan bhawan|udyog bhawan|shastri bhawan|niti ayog|pin\s*code|pincode|e-mail|telefax|@gov\.in|@nic\.in|www\.)',
                caseSensitive: false)
            .hasMatch(text)) {
      return null;
    }
    // Backend text-extraction artifacts ("N", ", N", "None") are not benefits.
    final compact = text.replaceAll(RegExp(r'[\s,.]'), '');
    if (compact.length <= 4 &&
        const {'n', 'none', 'na', 'n/a', 'nil', 'tbd'}
            .contains(compact.toLowerCase())) {
      return null;
    }
    if (text.length <= max) return text;
    var cut = text.substring(0, max);
    final space = cut.lastIndexOf(' ');
    if (space > max * 0.6) cut = cut.substring(0, space);
    return '$cut…';
  }

  static bool _isNoise(String? text) {
    if (text == null || text.trim().isEmpty) return true;
    if (text.length > 500) return true;
    if (RegExp(r'[\w\-.]+\.(pdf|docx?|xlsx?|png|jpe?g)\b',
            caseSensitive: false)
        .hasMatch(text)) {
      return true;
    }
    // "Page No. N" markers are always extraction artifacts, never prose.
    if (RegExp(r'\bpage\s*no\.?\s*\d+', caseSensitive: false)
        .hasMatch(text)) {
      return true;
    }
    // Letterhead / OCR fragments are never benefit text.
    final lower = text.toLowerCase();
    if (lower.contains('government of india') || lower.contains('&to&p')) {
      return true;
    }
    var hits = 0;
    if (RegExp(r'\bpages?\s*\d+',
            caseSensitive: false)
        .hasMatch(text)) {
      hits++;
    }
    if (lower.contains('f.no') || lower.contains('file no')) hits++;
    if (lower.contains('department of') || lower.contains('ministry of')) {
      hits++;
    }
    if (lower.contains('operational guidelines') && text.length > 120) hits++;
    return hits >= 1 && text.length > 120;
  }

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
      displayName: json['display_name']?.toString(),
      shortDescription: json['short_description']?.toString(),
      benefitsList: (json['benefits_list'] as List? ?? const [])
          .map((item) => item.toString())
          .where((item) => item.trim().isNotEmpty)
          .toList(),
      evidenceChecklist: (json['evidence_checklist'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => EvidenceChecklistEntry.fromJson(
              Map<String, dynamic>.from(item)))
          .toList(),
      mandatoryRulesTotal:
          int.tryParse(json['mandatory_rules_total']?.toString() ?? '') ?? 0,
      mandatoryRulesPassed:
          int.tryParse(json['mandatory_rules_passed']?.toString() ?? '') ?? 0,
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
