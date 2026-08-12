import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/citizen_models.dart';

/// Accesses the authenticated citizen profile. Document collection lives in
/// [DocumentIntelligenceRepository], which is the single upload workflow.
class CitizenRepository {
  CitizenRepository(this._apiService);

  final ApiService _apiService;

  Future<Map<String, dynamic>> getProfileDetails() async {
    final response = await _apiService.get(ApiConstants.citizenProfileDetails);
    return _extractData(response);
  }

  Future<ExtendedProfile> updateExtendedProfile(
    Map<String, dynamic> payload,
  ) async {
    final response = await _apiService.put(
      ApiConstants.citizenProfile,
      data: payload,
    );
    return ExtendedProfile.fromJson(_extractData(response));
  }

  Map<String, dynamic> _extractData(dynamic response) {
    if (response is Map<String, dynamic> && response['data'] is Map) {
      return Map<String, dynamic>.from(response['data'] as Map);
    }
    if (response is Map<String, dynamic>) return response;
    throw StateError('Unexpected response payload');
  }
}
