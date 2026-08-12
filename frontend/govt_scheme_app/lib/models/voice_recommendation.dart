import 'package:flutter/foundation.dart';

import 'recommendation.dart';

/// Represents the response from the backend `POST /voice/recommend` endpoint.
///
/// The backend reuses the existing `RecommendationMatchResponse` schema for
/// each scheme in `schemes`, so the client parses them with the same
/// `RecommendationMatch.fromJson` used by the text-based recommendation flow.
/// Minimal voice metadata is exposed for the UI.
@immutable
class VoiceRecommendationResult {
  const VoiceRecommendationResult({
    required this.schemes,
    required this.intent,
    this.language,
    this.normalizedText,
    this.confidence = 0.0,
    this.source,
    this.message,
    this.profile,
  });

  /// Personalized scheme recommendations (existing schema).
  final List<RecommendationMatch> schemes;

  /// The voice intent that was handled.
  final String intent;

  /// Approximate language tag of the query (e.g. "ta-en").
  final String? language;

  /// Normalized representation of the citizen's query.
  final String? normalizedText;

  /// Confidence in the structured interpretation (0.0 to 1.0).
  final double confidence;

  /// Whether normalization came from "llm" or "heuristic".
  final String? source;

  /// Human-friendly message for unsupported intents / no results.
  final String? message;

  /// Verified profile returned for `profile_query` intents.
  final VoiceProfileView? profile;

  bool get hasSchemes => schemes.isNotEmpty;

  factory VoiceRecommendationResult.fromJson(Map<String, dynamic> json) {
    return VoiceRecommendationResult(
      schemes: (json['schemes'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (item) =>
                RecommendationMatch.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
      intent: (json['intent'] ?? 'unknown').toString(),
      language: json['language']?.toString(),
      normalizedText: json['normalized_text']?.toString(),
      confidence: double.tryParse(json['confidence']?.toString() ?? '') ?? 0.0,
      source: json['source']?.toString(),
      message: json['message']?.toString(),
      profile: json['profile'] is Map<String, dynamic>
          ? VoiceProfileView.fromJson(
              Map<String, dynamic>.from(json['profile'] as Map),
            )
          : null,
    );
  }
}

/// Minimal, verified profile view returned for a `profile_query` intent.
@immutable
class VoiceProfileView {
  const VoiceProfileView({
    required this.citizenId,
    this.fullName,
    this.occupation,
    this.annualIncome,
    this.incomeCategory,
    this.isFarmer,
    this.isDisabled,
    this.caste,
    this.community,
    this.educationLevel,
    this.familyMemberCount,
    this.state,
    this.district,
    this.profileCompletionPercentage,
  });

  final String citizenId;
  final String? fullName;
  final String? occupation;
  final double? annualIncome;
  final String? incomeCategory;
  final bool? isFarmer;
  final bool? isDisabled;
  final String? caste;
  final String? community;
  final String? educationLevel;
  final int? familyMemberCount;
  final String? state;
  final String? district;
  final int? profileCompletionPercentage;

  factory VoiceProfileView.fromJson(Map<String, dynamic> json) {
    return VoiceProfileView(
      citizenId: (json['citizen_id'] ?? '').toString(),
      fullName: json['full_name']?.toString(),
      occupation: json['occupation']?.toString(),
      annualIncome: double.tryParse(json['annual_income']?.toString() ?? ''),
      incomeCategory: json['income_category']?.toString(),
      isFarmer: json['is_farmer'] == true,
      isDisabled: json['is_disabled'] == true,
      caste: json['caste']?.toString(),
      community: json['community']?.toString(),
      educationLevel: json['education_level']?.toString(),
      familyMemberCount: int.tryParse(
        json['family_member_count']?.toString() ?? '',
      ),
      state: json['state']?.toString(),
      district: json['district']?.toString(),
      profileCompletionPercentage: int.tryParse(
        json['profile_completion_percentage']?.toString() ?? '',
      ),
    );
  }
}
