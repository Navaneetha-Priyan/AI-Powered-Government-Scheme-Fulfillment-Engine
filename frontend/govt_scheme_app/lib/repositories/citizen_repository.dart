import 'package:dio/dio.dart';

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

  /// Uploads a generic government document and processes it through the real
  /// backend document pipeline.
  ///
  /// The backend reads the file (PDF text extraction or OCR), extracts
  /// normalized fields, maps them to canonical domain fields, and enriches the
  /// citizen profile. Only the document type and file are required — no manual
  /// profile fields.
  Future<DocumentUploadResult> uploadDocument({
    required String filePath,
    required String fileName,
    required String documentType,
  }) async {
    final formData = FormData.fromMap({
      'document_type': documentType,
      'file': await MultipartFile.fromFile(filePath, filename: fileName),
    });

    final response = await _apiService.postMultipart(
      ApiConstants.citizenDocumentUpload,
      formData: formData,
    );

    final data = _extractData(response);
    final document = data['document'] is Map
        ? GovernmentDocument.fromJson(
            Map<String, dynamic>.from(data['document'] as Map),
          )
        : null;
    final processing = data['processing'] is Map
        ? DocumentProcessingData.fromJson(
            Map<String, dynamic>.from(data['processing'] as Map),
          )
        : null;

    return DocumentUploadResult(
      processingStatus: data['processing_status']?.toString() ?? 'not_processed',
      document: document,
      processing: processing,
      processingError: data['processing_error']?.toString(),
    );
  }

  /// Uploads a citizen-submitted land record with a supporting file.
  ///
  /// The backend accepts manually supplied land-record fields plus the file.
  /// The backend may also attempt real-document processing (PDF text
  /// extraction or OCR) on the uploaded file; the result is returned in
  /// [LandRecordUploadResult.processingStatus] / [processingError].
  Future<LandRecordUploadResult> uploadLandRecord({
    required String filePath,
    required String fileName,
    required String surveyNumber,
    required String village,
    required String district,
    required String landType,
    required double landArea,
    required String ownershipType,
    String? taluk,
    String? state,
    String? pattaNumber,
    String documentType = 'land_record',
  }) async {
    final formData = FormData.fromMap({
      'survey_number': surveyNumber,
      'village': village,
      'district': district,
      'land_type': landType,
      'land_area': landArea,
      'ownership_type': ownershipType,
      'document_type': documentType,
      if (taluk != null && taluk.trim().isNotEmpty) 'taluk': taluk,
      if (state != null && state.trim().isNotEmpty) 'state': state,
      if (pattaNumber != null && pattaNumber.trim().isNotEmpty)
        'patta_number': pattaNumber,
      'file': await MultipartFile.fromFile(filePath, filename: fileName),
    });

    final response = await _apiService.postMultipart(
      ApiConstants.citizenLandRecordUpload,
      formData: formData,
    );

    final data = _extractData(response);
    final record = data['land_record'];
    if (record is! Map) {
      throw StateError('Unexpected land record upload response payload');
    }
    return LandRecordUploadResult(
      record: LandRecord.fromJson(Map<String, dynamic>.from(record)),
      processingStatus:
          data['processing_status']?.toString() ?? 'not_processed',
      processingError: data['processing_error']?.toString(),
    );
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
