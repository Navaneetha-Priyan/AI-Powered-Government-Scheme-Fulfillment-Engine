import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/core/network/api_exception.dart';
import 'package:govt_scheme_app/core/network/api_service.dart';
import 'package:govt_scheme_app/core/services/storage_service.dart';
import 'package:govt_scheme_app/core/services/voice_api_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FakeApiService extends ApiService {
  _FakeApiService(StorageService storageService, {this.postHandler})
    : super(storageService: storageService);

  final Future<dynamic> Function(String path, Object? data)? postHandler;
  final List<String> postedPaths = [];
  final List<Object?> postedData = [];
  final List<Duration?> postedTimeouts = [];

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Duration? receiveTimeout,
  }) async {
    postedPaths.add(path);
    postedData.add(data);
    postedTimeouts.add(receiveTimeout);
    final handler = postHandler;
    if (handler == null) {
      return <String, dynamic>{};
    }
    return handler(path, data);
  }

  @override
  Future<dynamic> postMultipart(
    String path, {
    required FormData formData,
    ProgressCallback? onSendProgress,
  }) async {
    throw UnimplementedError();
  }
}

Future<StorageService> _storage() async {
  SharedPreferences.setMockInitialValues({});
  return StorageService.create();
}

void main() {
  test(
    'normalizes a transcript through the voice normalize endpoint',
    () async {
      final api = _FakeApiService(
        await _storage(),
        postHandler: (_, _) async => {
          'language': 'ta',
          'intent': 'scheme_search',
          'normalized_text':
              'Are there any government schemes available for agriculture?',
          'entities': {'occupation': 'farmer'},
          'confidence': 0.95,
          'source': 'llm',
        },
      );
      final service = VoiceApiService(apiService: api);

      final result = await service.normalize(
        'எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?',
      );

      expect(api.postedPaths, contains('/voice/normalize'));
      expect(result.intent, 'scheme_search');
      expect(result.normalizedText, contains('agriculture'));
      expect(result.entities['occupation'], 'farmer');
    },
  );

  test('sends normalized text to RAG query endpoint', () async {
    final api = _FakeApiService(
      await _storage(),
      postHandler: (_, _) async => {
        'success': true,
        'message': 'RAG query completed successfully',
        'data': {
          'query': 'Are there schemes for farmers?',
          'answer': 'Yes. PMKSY supports irrigation for farmers.',
          'sources': [
            {
              'scheme_name': 'PMKSY',
              'source_file': 'pmksy.pdf',
              'page_number': 1,
              'score': 0.91,
            },
          ],
          'language': 'en',
          'confidence': 0.91,
          'is_grounded': true,
        },
      },
    );
    final service = VoiceApiService(apiService: api);

    final result = await service.queryRag('Are there schemes for farmers?');
    final postedPayload = api.postedData.single as Map<String, dynamic>;

    expect(api.postedPaths, contains('/api/schemes/rag/query'));
    expect(postedPayload, containsPair('top_k', 3));
    expect(postedPayload, containsPair('language', 'en'));
    expect(result.answer, contains('PMKSY'));
    expect(result.sources.single.schemeName, 'PMKSY');
  });

  test('parses the generated voice response and language', () async {
    final api = _FakeApiService(
      await _storage(),
      postHandler: (_, _) async => {
        'schemes': [],
        'intent': 'scheme_search',
        'language': 'ta-en',
        'response_text': 'விவசாயிகளுக்கான அரசு திட்டங்கள் உள்ளன.',
        'response_language': 'ta',
      },
    );
    final service = VoiceApiService(apiService: api);

    final result = await service.recommend('enakku farmer scheme irukka?');

    expect(api.postedPaths, contains('/voice/recommend'));
    expect(api.postedTimeouts.single, const Duration(seconds: 120));
    expect(result.responseText, 'விவசாயிகளுக்கான அரசு திட்டங்கள் உள்ளன.');
    expect(result.responseLanguage, 'ta');
  });

  test('surfaces normalization failure for the UI state machine', () async {
    final api = _FakeApiService(
      await _storage(),
      postHandler: (_, _) async =>
          throw ApiException(message: 'normalize down'),
    );
    final service = VoiceApiService(apiService: api);

    expect(
      () => service.normalize('farmer scheme'),
      throwsA(isA<ApiException>()),
    );
  });

  test('surfaces RAG failure for the UI state machine', () async {
    final api = _FakeApiService(
      await _storage(),
      postHandler: (_, _) async => throw ApiException(message: 'rag down'),
    );
    final service = VoiceApiService(apiService: api);

    expect(
      () => service.queryRag('farmer scheme'),
      throwsA(isA<ApiException>()),
    );
  });
}
