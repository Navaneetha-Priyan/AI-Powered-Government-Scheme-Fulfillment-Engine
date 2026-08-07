import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/government_scheme.dart';

class SchemeRepository {
  SchemeRepository(ApiService? apiService) : _apiService = apiService;

  final ApiService? _apiService;

  Future<SchemeListResponse> listSchemes({
    int skip = 0,
    int limit = 20,
    String? category,
    String? status,
    String? query,
  }) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.get(
      ApiConstants.schemes,
      queryParameters: {
        'skip': skip.toString(),
        'limit': limit.toString(),
        if (category != null && category.isNotEmpty) 'category': category,
        if (status != null && status.isNotEmpty) 'status': status,
        if (query != null && query.isNotEmpty) 'query': query,
      },
    );
    return SchemeListResponse.fromJson(response as Map<String, dynamic>);
  }

  Future<SchemeListResponse> searchSchemes(String query, {int limit = 10}) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.post(
      ApiConstants.schemeSearch,
      data: {'query': query, 'limit': limit, 'category': null},
    );
    final payload = response is Map<String, dynamic> ? response : <String, dynamic>{};
    final data = payload['data'] is Map<String, dynamic>
        ? payload['data'] as Map<String, dynamic>
        : payload;
    final items = (data['items'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => GovernmentScheme.fromJson(Map<String, dynamic>.from(item)))
        .toList();

    return SchemeListResponse(items: items, total: items.length, skip: 0, limit: limit);
  }

  Future<GovernmentScheme> getScheme(String schemeId) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.get('${ApiConstants.schemes}/$schemeId');
    final payload = response is Map<String, dynamic> ? response : <String, dynamic>{};
    final data = payload['data'] is Map<String, dynamic>
        ? payload['data'] as Map<String, dynamic>
        : payload;
    return GovernmentScheme.fromJson(data);
  }
}
