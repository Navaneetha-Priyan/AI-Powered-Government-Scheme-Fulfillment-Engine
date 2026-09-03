import 'package:flutter/foundation.dart';

@immutable
class NormalizationResult {
  const NormalizationResult({
    required this.language,
    required this.intent,
    required this.normalizedText,
    required this.entities,
    required this.confidence,
    required this.source,
  });

  final String language;
  final String intent;
  final String normalizedText;
  final Map<String, dynamic> entities;
  final double confidence;
  final String source;

  factory NormalizationResult.fromJson(Map<String, dynamic> json) {
    return NormalizationResult(
      language: (json['language'] ?? 'unknown').toString(),
      intent: (json['intent'] ?? 'unknown').toString(),
      normalizedText: (json['normalized_text'] ?? '').toString(),
      entities: json['entities'] is Map
          ? Map<String, dynamic>.from(json['entities'] as Map)
          : const <String, dynamic>{},
      confidence: double.tryParse(json['confidence']?.toString() ?? '') ?? 0.0,
      source: (json['source'] ?? 'heuristic').toString(),
    );
  }
}
