import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/eligibility.dart';

class EligibilityRepository {
  EligibilityRepository(this._apiService);

  final ApiService? _apiService;

  Future<EligibilityCheck> checkSchemeEligibility(String schemeId) async {
    assert(_apiService != null, 'Use the real repository in app runtime');
    final response = await _apiService!.get(
      ApiConstants.eligibilityCheck,
      queryParameters: {'scheme_id': schemeId},
    );
    return EligibilityCheck.fromJson(_extractData(response));
  }

  Map<String, dynamic> _extractData(dynamic response) {
    if (response is Map<String, dynamic> &&
        response['data'] is Map<String, dynamic>) {
      return Map<String, dynamic>.from(response['data'] as Map);
    }

    if (response is Map<String, dynamic>) {
      return response;
    }

    throw StateError('Unexpected response payload');
  }
}
