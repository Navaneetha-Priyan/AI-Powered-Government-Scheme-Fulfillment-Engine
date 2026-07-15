import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/citizen_models.dart';

class DigiLockerRepository {
  DigiLockerRepository(this._apiService);

  final ApiService _apiService;

  Future<DigiLockerStatus> getStatus() async {
    final response = await _apiService.get(ApiConstants.digilockerStatus);
    return DigiLockerStatus.fromJson(_extractData(response));
  }

  Future<DigiLockerSyncResult> sync({bool forceRefresh = false}) async {
    final response = await _apiService.post(
      ApiConstants.digilockerSync,
      data: {'force_refresh': forceRefresh},
    );
    return DigiLockerSyncResult.fromJson(_extractData(response));
  }

  Future<DocumentSummary> getDocuments() async {
    final response = await _apiService.get(ApiConstants.digilockerDocuments);
    return DocumentSummary.fromJson(_extractData(response));
  }

  Future<GovernmentDocument> getDocument(String documentId) async {
    final response = await _apiService.get(
      ApiConstants.digilockerDocument(documentId),
    );
    return GovernmentDocument.fromJson(_extractData(response));
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
