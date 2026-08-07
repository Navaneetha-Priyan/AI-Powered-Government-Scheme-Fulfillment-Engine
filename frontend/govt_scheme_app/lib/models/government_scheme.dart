import 'package:flutter/foundation.dart';

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

  bool get hasDetailFields =>
      eligibilitySummary != null ||
      requiredDocuments != null ||
      applicationProcess != null ||
      officialLink != null ||
      createdAt != null ||
      updatedAt != null;

  factory GovernmentScheme.fromJson(Map<String, dynamic> json) {
    return GovernmentScheme(
      id: (json['id'] ?? json['scheme_id'] ?? '').toString(),
      schemeName: (json['scheme_name'] ?? json['schemeName'] ?? 'Untitled scheme').toString(),
      description: (json['description'] ?? json['matched_content'] ?? json['relevant_content'] ?? '').toString(),
      category: (json['category'] ?? '').toString(),
      department: (json['department'] ?? '').toString(),
      governmentLevel: (json['government_level'] ?? json['governmentLevel'] ?? 'state').toString(),
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
        .map((item) => GovernmentScheme.fromJson(Map<String, dynamic>.from(item)))
        .toList();

    return SchemeListResponse(
      items: items,
      total: int.tryParse(data['total']?.toString() ?? '') ?? items.length,
      skip: int.tryParse(data['skip']?.toString() ?? '') ?? 0,
      limit: int.tryParse(data['limit']?.toString() ?? '') ?? items.length,
    );
  }
}
