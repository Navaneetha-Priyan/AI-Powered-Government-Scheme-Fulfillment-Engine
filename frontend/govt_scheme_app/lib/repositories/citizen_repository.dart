import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/citizen_models.dart';

class CitizenRepository {
  CitizenRepository(this._apiService);

  final ApiService _apiService;

  Future<ExtendedProfile> getExtendedProfile() async {
    final response = await _apiService.get(ApiConstants.citizenProfile);
    return ExtendedProfile.fromJson(_extractData(response));
  }

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

  Future<IncomeDetails> getIncome() async {
    final response = await _apiService.get(ApiConstants.citizenIncome);
    return IncomeDetails.fromJson(_extractData(response));
  }

  Future<CasteDetails> getCaste() async {
    final response = await _apiService.get(ApiConstants.citizenCaste);
    return CasteDetails.fromJson(_extractData(response));
  }

  Future<LandRecordSummary> getLandRecords() async {
    final response = await _apiService.get(ApiConstants.citizenLandRecords);
    return LandRecordSummary.fromJson(_extractData(response));
  }

  Future<DocumentSummary> getDocuments() async {
    final response = await _apiService.get(ApiConstants.citizenDocuments);
    return DocumentSummary.fromJson(_extractData(response));
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
