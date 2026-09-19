import 'package:flutter/foundation.dart';

import '../core/utils/presentation_text.dart';

@immutable
class GovernmentScheme {
  const GovernmentScheme({
    required this.id,
    required this.schemeName,
    required this.description,
    required this.category,
    required this.department,
    required this.governmentLevel,
    this.state,
    this.benefits,
    this.eligibilitySummary,
    this.requiredDocuments,
    this.applicationProcess,
    this.officialLink,
    this.language = 'en',
    this.status = 'active',
    this.createdAt,
    this.updatedAt,
    this.displayName,
    this.about,
    this.benefitsList = const [],
    this.whoItIsFor,
    this.documents = const [],
    this.application = const [],
    this.sourceStatus,
    this.sourcePdf,
  });

  final String id;
  final String schemeName;
  final String description;
  final String category;
  final String department;
  final String governmentLevel;
  final String? state;
  final String? benefits;
  final String? eligibilitySummary;
  final String? requiredDocuments;
  final String? applicationProcess;
  final String? officialLink;
  final String language;
  final String status;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  /// Citizen-facing presentation fields populated by the backend from
  /// backend/data/scheme_presentation.json (curated, PDF-grounded).
  /// Raw PDF extraction is never placed in these fields.
  final String? displayName;
  final String? about;       // short_description / "About this scheme"
  final List<String> benefitsList;
  final String? whoItIsFor;
  final List<String> documents;      // human-readable document names
  final List<String> application;    // numbered application steps
  final String? sourceStatus;
  final String? sourcePdf;

  bool get hasDetailFields =>
      eligibilitySummary != null ||
      requiredDocuments != null ||
      applicationProcess != null ||
      officialLink != null ||
      createdAt != null ||
      updatedAt != null;

  /// ─ Validated citizen-facing presentation ───────────────────────────────
  /// These getters are the ONLY values the UI should render for scheme
  /// information. Corrupted / PDF-extraction content is rejected here, and raw
  /// scheme columns are deliberately NOT used as a fallback: the app hides the
  /// section instead of showing extraction noise.

  /// Clean scheme name, falling back to the catalogue title (which is a short
  /// catalog name, never PDF extraction).
  String get displayTitle =>
      cleanPresentationText(displayName, max: 120) ?? schemeName;

  /// "About this scheme" text, or null when nothing clean exists.
  String? get cleanAbout => cleanPresentationText(about);

  /// Short description for cards, or null when nothing clean exists.
  String? get cleanShortDescription {
    final clean = cleanPresentationText(about, max: 220);
    if (clean == null) return null;
    return clean;
  }

  /// Validated benefit bullets ("What you get"). Empty means omit the section.
  List<String> get cleanBenefits => cleanPresentationList(benefitsList);

  /// Validated "who this is for" text, or null.
  String? get cleanWhoItIsFor => cleanPresentationText(whoItIsFor);

  /// Validated informational eligibility summary, or null. The real eligibility
  /// decision always comes from the deterministic eligibility engine.
  String? get cleanEligibilitySummary =>
      cleanPresentationText(eligibilitySummary);

  /// Validated human-readable document list.
  List<String> get cleanDocuments => cleanPresentationList(documents);

  /// Validated application steps.
  List<String> get cleanApplication => cleanPresentationList(application);

  factory GovernmentScheme.fromJson(Map<String, dynamic> json) {
    return GovernmentScheme(
      id: (json['id'] ?? json['scheme_id'] ?? '').toString(),
      schemeName:
          (json['scheme_name'] ?? json['schemeName'] ?? 'Untitled scheme')
              .toString(),
      description:
          (json['description'] ??
                  json['matched_content'] ??
                  json['relevant_content'] ??
                  '')
              .toString(),
      category: (json['category'] ?? '').toString(),
      department: (json['department'] ?? '').toString(),
      governmentLevel:
          (json['government_level'] ?? json['governmentLevel'] ?? 'state')
              .toString(),
      state: json['state']?.toString(),
      benefits: json['benefits']?.toString(),
      eligibilitySummary: json['eligibility_summary']?.toString(),
      requiredDocuments: json['required_documents']?.toString(),
      applicationProcess: json['application_process']?.toString(),
      officialLink: json['official_link']?.toString(),
      language: (json['language'] ?? 'en').toString(),
      status: (json['status'] ?? 'active').toString(),
      createdAt: _parseDate(json['created_at']),
      updatedAt: _parseDate(json['updated_at']),
      displayName: json['display_name']?.toString(),
      about: json['about']?.toString(),
      benefitsList: _stringList(json['benefits_list']),
      whoItIsFor: json['who_it_is_for']?.toString(),
      documents: _stringList(json['documents']),
      application: _stringList(json['application']),
      sourceStatus: json['source_status']?.toString(),
      sourcePdf: json['source_pdf']?.toString(),
    );
  }

  static List<String> _stringList(dynamic value) {
    if (value is List) {
      return value.whereType<String>().toList();
    }
    if (value is String) {
      return [value];
    }
    return const [];
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
class SchemeListResponse {
  const SchemeListResponse({
    required this.items,
    required this.total,
    required this.skip,
    required this.limit,
  });

  final List<GovernmentScheme> items;
  final int total;
  final int skip;
  final int limit;

  factory SchemeListResponse.fromJson(Map<String, dynamic> json) {
    final data = json['data'] is Map<String, dynamic>
        ? json['data'] as Map<String, dynamic>
        : json;
    final items = (data['items'] as List? ?? const [])
        .whereType<Map>()
        .map(
          (item) => GovernmentScheme.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();

    return SchemeListResponse(
      items: items,
      total: int.tryParse(data['total']?.toString() ?? '') ?? items.length,
      skip: int.tryParse(data['skip']?.toString() ?? '') ?? 0,
      limit: int.tryParse(data['limit']?.toString() ?? '') ?? items.length,
    );
  }
}
