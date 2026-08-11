import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;

import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/transcription.dart';

/// Repository that uploads a recorded audio file to the backend speech-to-text
/// endpoint and returns the transcribed text.
class VoiceApiService {
  VoiceApiService({required ApiService apiService}) : _apiService = apiService;

  final ApiService _apiService;

  /// Uploads the audio file at [path] to POST /voice/transcribe.
  ///
  /// The file is sent as multipart/form-data under the field name audio.
  /// Returns a [TranscriptionResult] parsed from the backend response.
  Future<TranscriptionResult> transcribeAudio(String path) async {
    final fileName = p.basename(path);

    final formData = FormData.fromMap({
      'audio': await MultipartFile.fromFile(path, filename: fileName),
    });

    final data = await _apiService.postMultipart(
      ApiConstants.voiceTranscribe,
      formData: formData,
    );

    final map = data is Map<String, dynamic>
        ? data
        : <String, dynamic>{'text': data?.toString() ?? ''};

    return TranscriptionResult.fromJson(map);
  }
}
