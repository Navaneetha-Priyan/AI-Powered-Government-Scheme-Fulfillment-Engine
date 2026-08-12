import 'dart:io';
import 'package:dio/dio.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/document_intelligence.dart';

class DocumentIntelligenceRepository {
  DocumentIntelligenceRepository(this._api);
  final ApiService _api;
  Map<String, dynamic> _data(dynamic value) =>
      Map<String, dynamic>.from((value as Map)['data'] as Map? ?? const {});
  Future<List<CitizenDocument>> documents() async {
    final data = _data(await _api.get(ApiConstants.intelligentDocuments));
    return (data['items'] as List? ?? const [])
        .map(
          (e) => CitizenDocument.fromJson(Map<String, dynamic>.from(e as Map)),
        )
        .toList();
  }

  Future<void> upload(
    String type,
    File file,
    void Function(int, int) progress,
  ) async {
    await _api.postMultipart(
      ApiConstants.intelligentDocumentUpload(type),
      formData: FormData.fromMap({
        'file': await MultipartFile.fromFile(
          file.path,
          filename: file.uri.pathSegments.last,
        ),
      }),
      onSendProgress: progress,
    );
  }

  /// OCR can legitimately take longer than normal interactive requests.
  Future<void> processAll() => _api.post(
    ApiConstants.processAllDocuments,
    receiveTimeout: const Duration(minutes: 2),
  );
  Future<ProfilePreview> preview() async => ProfilePreview.fromJson(
    _data(await _api.get(ApiConstants.profilePreview)),
  );
  Future<Map<String, int>> completeness() async {
    final data = _data(await _api.get(ApiConstants.profileCompleteness));
    return data.map(
      (key, value) => MapEntry(key, (value as num?)?.toInt() ?? 0),
    );
  }

  Future<void> correct(String field, String value) => _api.post(
    '/api/profile/correct',
    data: {'field_name': field, 'value': value},
  );
  Future<void> confirm() => _api.post(ApiConstants.profileConfirm);
}
