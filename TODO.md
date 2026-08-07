# Recommendation Engine Implementation

- [x] Review backend recommendation schemas & routes (generate, latest, history, detail, refresh)
- [x] Created `lib/models/recommendation.dart` (RecommendationMatch, RecommendationRule, RecommendationSummary, RecommendationHistory)
- [x] Created `lib/repositories/recommendation_repository.dart` (getLatest/generate/refresh/getRecommendation/getHistory)
- [x] Added recommendation API constants to `lib/core/constants/api_constants.dart`
- [x] Created `lib/providers/recommendation_provider.dart` (caching, shared in-flight, stale-result discard, error scoping, invalidateAll)
- [x] Added `onInvalidateAll` callback to `EligibilityProvider` for recommendation cache invalidation on eligibility changes
- [x] Wired `RecommendationProvider` in `main.dart` via `ChangeNotifierProxyProvider` (eligibility invalidation → recommendation invalidation)
- [x] Created `lib/screens/recommendations/recommendations_screen.dart` (list with rank, confidence, eligibility %, benefit, reason)
- [x] Created `lib/screens/recommendations/recommendation_detail_screen.dart` (why-recommended, matched attributes/documents/rules, benefits, next steps, required actions)
- [x] Created `lib/screens/recommendations/recommendation_history_screen.dart` (history from backend)
- [x] Added routes to `lib/routes/app_routes.dart` (recommendations)
- [x] Added "Recommended Schemes" entry card to `lib/screens/home/dashboard_screen.dart`
- [x] Created `test/recommendation_provider_test.dart` (9 tests: caching, dedup, refresh, invalidation, error scoping)
- [x] Ran `flutter analyze` — clean (only pre-existing `land_records_screen.dart` info remains)
- [x] Ran `flutter test` — all 22 tests passed (6 eligibility + 9 recommendation + 7 others)

