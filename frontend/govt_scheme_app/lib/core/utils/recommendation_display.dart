/// Citizen-facing sanitization lives directly on [RecommendationMatch] in
/// `lib/models/recommendation.dart` (`cardReason`, `cardBenefit`,
/// `cardMatchBullets`, `cardMissingBullets`), so card widgets, the detail
/// screen, and tests share one implementation with no import cycles.
/// The backend still returns full retrieval metadata (`semantic_query`,
/// file refs, page markers); only the presentation layer filters it.
const String recommendationDisplayNote = 'see RecommendationMatch';
