import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/recommendation.dart';

class RecommendationRepository {
  RecommendationRepository(ApiService? apiService) : _apiService = apiService;

  final ApiService? _apiService;

  Future<RecommendationSummary> getLatest() async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.get(ApiConstants.recommendations);
    final data = _dataMap(response);
    return RecommendationSummary.fromJson(data);
  }

  Future<RecommendationSummary> generate({
    int limit = 5,
    String? category,
    String? state,
  }) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.post(
      ApiConstants.recommendationGenerate,
      data: {
        'limit': limit,
        if (category != null && category.isNotEmpty) 'category': category,
        if (state != null && state.isNotEmpty) 'state': state,
      },
    );
    final data = _dataMap(response);
    return RecommendationSummary.fromJson(data);
  }

  Future<RecommendationSummary> refresh({
    int limit = 5,
    String? category,
    String? state,
  }) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.post(
      ApiConstants.recommendationRefresh,
      data: {
        'limit': limit,
        if (category != null && category.isNotEmpty) 'category': category,
        if (state != null && state.isNotEmpty) 'state': state,
      },
    );
    final data = _dataMap(response);
    return RecommendationSummary.fromJson(data);
  }

  Future<RecommendationMatch> getRecommendation(String recommendationId) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.get(
      ApiConstants.recommendationDetail(recommendationId),
    );
    final data = _dataMap(response);
    return RecommendationMatch.fromJson(data);
  }

  Future<List<RecommendationHistory>> getHistory({int limit = 20}) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.get(
      ApiConstants.recommendationHistory,
      queryParameters: {'limit': limit.toString()},
    );
    return _historyList(response);
  }

  Map<String, dynamic> _dataMap(dynamic response) {
    final payload = response is Map<String, dynamic>
        ? response
        : <String, dynamic>{};
    return payload['data'] is Map<String, dynamic>
        ? Map<String, dynamic>.from(payload['data'] as Map)
        : payload;
  }

  List<RecommendationHistory> _historyList(dynamic response) {
    final payload = response is Map<String, dynamic>
        ? response
        : <String, dynamic>{};
    final data = payload['data'] is List ? payload['data'] as List : const [];
    return data
        .whereType<Map>()
        .map(
          (item) =>
              RecommendationHistory.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }
}
