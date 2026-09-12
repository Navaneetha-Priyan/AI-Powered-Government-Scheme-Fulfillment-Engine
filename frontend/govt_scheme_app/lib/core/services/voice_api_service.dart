import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../constants/api_constants.dart';
import '../network/api_service.dart';
import '../../models/normalization.dart';
import '../../models/rag_query.dart';
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

  @protected
  ApiService get apiService => _apiService;

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

    final response = await apiService.postMultipart(
      ApiConstants.voiceTranscribe,
      formData: formData,
    );
    debugPrint('[VOICE] Audio uploaded');

    final payload = response is Map<String, dynamic>
        ? response
        : const <String, dynamic>{};
    final result = TranscriptionResult.fromJson(payload);
    debugPrint('[VOICE] Transcript received');
    return result;
  }

  Future<NormalizationResult> normalize(String text) async {
    final response = await apiService.post(
      ApiConstants.voiceNormalize,
      data: {'text': text},
      receiveTimeout: const Duration(seconds: 45),
    );

    final payload = response is Map<String, dynamic>
        ? response
        : const <String, dynamic>{};
    final result = NormalizationResult.fromJson(payload);
    debugPrint('[VOICE] Normalization received');
    return result;
  }

  Future<RagQueryResult> queryRag(
    String normalizedText, {
    int topK = 3,
    String language = 'en',
  }) async {
    debugPrint('[VOICE] RAG request sent');
    final response = await apiService.post(
      ApiConstants.ragQuery,
      data: {'query': normalizedText, 'top_k': topK, 'language': language},
      receiveTimeout: const Duration(seconds: 90),
    );

    final wrapper = response is Map<String, dynamic>
        ? response
        : const <String, dynamic>{};
    final data = wrapper['data'] is Map
        ? Map<String, dynamic>.from(wrapper['data'] as Map)
        : wrapper;
    final result = RagQueryResult.fromJson(data);
    debugPrint('[VOICE] RAG response received');
    return result;
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
  Future<VoiceRecommendationResult> recommend(
    String text, {
    NormalizationResult? normalization,
  }) async {
    final requestData = normalization == null
        ? <String, dynamic>{'text': text}
        : <String, dynamic>{
            'normalization': {
              'language': normalization.language,
              'intent': normalization.intent,
              'normalized_text': normalization.normalizedText,
              'entities': normalization.entities,
              'confidence': normalization.confidence,
              'source': normalization.source,
            },
          };
    final response = await apiService.post(
      ApiConstants.voiceRecommend,
      data: requestData,
      // Recommendation may load embeddings and perform one local Qwen call;
      // the default 20-second client timeout is too short for a cold start.
      receiveTimeout: const Duration(seconds: 120),
    );

    final payload = response is Map<String, dynamic>
        ? response
        : const <String, dynamic>{};
    debugPrint('[VOICE] Recommendation response received');
    return VoiceRecommendationResult.fromJson(payload);
  }
}
