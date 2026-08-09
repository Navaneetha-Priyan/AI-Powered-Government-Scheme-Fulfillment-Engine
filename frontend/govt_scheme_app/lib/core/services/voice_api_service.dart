import 'package:dio/dio.dart';

import '../constants/api_constants.dart';
import '../network/api_service.dart';
import '../../models/transcription.dart';
import '../../models/voice_recommendation.dart';

/// Encapsulates all voice backend communication for the app.
///
/// Phase 3 scope:
///  - Uploads the recorded audio file to `POST /voice/transcribe`.
///  - Reuses the existing authenticated [ApiService] (and its Dio client and
///    JWT interceptor) so the `Authorization` header is attached exactly like
///    every other authenticated API call.
///  - Parses the backend response `{"text": "<transcribed speech>"}` and
///    returns the transcript.
///
/// Phase 5 scope:
///  - Sends a raw (or normalized) transcript to `POST /voice/recommend` and
///    returns personalized scheme recommendations for the authenticated
///    citizen.
///
/// This service intentionally contains no UI logic.
class VoiceApiService {
  VoiceApiService({required ApiService apiService}) : _apiService = apiService;

  final ApiService _apiService;

  /// Uploads the audio file at [filePath] to the transcription endpoint and
  /// returns the transcribed text.
  ///
  /// Throws an [ApiException] (from [ApiService]) when the upload or
  /// transcription fails, so callers can surface the error and keep the file.
  Future<TranscriptionResult> transcribe(String filePath) async {
    final formData = FormData.fromMap({
      'audio': await MultipartFile.fromFile(
        filePath,
        filename: 'recording.m4a',
        contentType: DioMediaType('audio', 'mp4'),
      ),
    });

    final response = await _apiService.postMultipart(
      ApiConstants.voiceTranscribe,
      formData: formData,
    );

    final payload = response is Map<String, dynamic>
        ? response
        : const <String, dynamic>{};
    return TranscriptionResult.fromJson(payload);
  }

  /// Sends [text] (a raw or normalized transcript) to `POST /voice/recommend`
  /// and returns personalized scheme recommendations for the authenticated
  /// citizen.
  ///
  /// The backend treats the voice text as query context only; the verified
  /// citizen profile and the existing eligibility/RAG engine remain
  /// authoritative. The returned schemes reuse the existing recommendation
  /// schema.
  ///
  /// Throws an [ApiException] (from [ApiService]) when the request fails.
  Future<VoiceRecommendationResult> recommend(String text) async {
    final response = await _apiService.post(
      ApiConstants.voiceRecommend,
      data: {'text': text},
    );

    final payload = response is Map<String, dynamic>
        ? response
        : const <String, dynamic>{};
    return VoiceRecommendationResult.fromJson(payload);
  }
}
