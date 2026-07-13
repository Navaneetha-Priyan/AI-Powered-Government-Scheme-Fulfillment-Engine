import '../core/network/api_service.dart';
import '../models/india_location_models.dart';

class IndiaLocationRepository {
  IndiaLocationRepository(this._apiService);

  final ApiService _apiService;

  Future<IndiaLocations> getLocations() async {
    final response = await _apiService.get('/meta/india-locations');
    return IndiaLocations.fromJson(_extractData(response));
  }

  Map<String, dynamic> _extractData(dynamic response) {
    if (response is Map<String, dynamic> && response['data'] is Map<String, dynamic>) {
      return Map<String, dynamic>.from(response['data'] as Map);
    }

    if (response is Map<String, dynamic>) {
      return response;
    }

    throw StateError('Unexpected response payload');
  }
}