import 'package:flutter/foundation.dart';

@immutable
class RagQueryResult {
  const RagQueryResult({
    required this.query,
    required this.answer,
    required this.sources,
    required this.isGrounded,
    this.language,
    this.confidence,
    this.message,
  });

  final String query;
  final String answer;
  final List<RagSource> sources;
  final bool isGrounded;
  final String? language;
  final double? confidence;
  final String? message;

  factory RagQueryResult.fromJson(Map<String, dynamic> json) {
    return RagQueryResult(
      query: (json['query'] ?? '').toString(),
      answer: (json['answer'] ?? json['message'] ?? '').toString(),
      sources: (json['sources'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => RagSource.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
      isGrounded: json['is_grounded'] != false,
      language: json['language']?.toString(),
      confidence: double.tryParse(json['confidence']?.toString() ?? ''),
      message: json['message']?.toString(),
    );
  }
}

@immutable
class RagSource {
  const RagSource({
    required this.schemeName,
    required this.sourceFile,
    required this.score,
    this.pageNumber,
    this.sectionName,
  });

  final String schemeName;
  final String sourceFile;
  final double score;
  final int? pageNumber;
  final String? sectionName;

  factory RagSource.fromJson(Map<String, dynamic> json) {
    return RagSource(
      schemeName: (json['scheme_name'] ?? '').toString(),
      sourceFile: (json['source_file'] ?? '').toString(),
      score: double.tryParse(json['score']?.toString() ?? '') ?? 0.0,
      pageNumber: int.tryParse(json['page_number']?.toString() ?? ''),
      sectionName: json['section_name']?.toString(),
    );
  }
}
