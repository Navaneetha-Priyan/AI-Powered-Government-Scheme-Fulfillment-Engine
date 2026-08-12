import 'package:dio/dio.dart';

import '../constants/api_constants.dart';
import '../services/storage_service.dart';
import 'api_exception.dart';

class ApiService {
  ApiService({required StorageService storageService})
    : _storageService = storageService,
      _baseUrlCandidates = ApiConstants.baseUrlCandidates {
    _initializeClients(_baseUrlCandidates.first);
  }

  final List<String> _baseUrlCandidates;
  final StorageService _storageService;
  late Dio _dio;
  late Dio _refreshDio;

  void _initializeClients(String baseUrl) {
    _dio = _createClient(baseUrl);
    _refreshDio = _createClient(baseUrl);

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = _storageService.accessToken;
          final isAuthRoute =
              options.path == ApiConstants.login ||
              options.path == ApiConstants.register ||
              options.path == ApiConstants.refresh ||
              options.path == ApiConstants.health ||
              options.path == ApiConstants.version ||
              options.path == ApiConstants.info;

          if (token != null && token.isNotEmpty && !isAuthRoute) {
            options.headers['Authorization'] = 'Bearer $token';
          }

          handler.next(options);
        },
        onError: (error, handler) async {
          final isUnauthorized = error.response?.statusCode == 401;
          final alreadyRetried = error.requestOptions.extra['retried'] == true;
          final isRefreshCall =
              error.requestOptions.path == ApiConstants.refresh;

          if (isUnauthorized && !alreadyRetried && !isRefreshCall) {
            final refreshToken = _storageService.refreshToken;
            if (refreshToken != null && refreshToken.isNotEmpty) {
              try {
                final refreshResponse = await _refreshDio.post(
                  ApiConstants.refresh,
                  data: {'refresh_token': refreshToken},
                );
                final refreshData =
                    refreshResponse.data as Map<String, dynamic>;
                final payload = refreshData['data'] as Map<String, dynamic>;
                await _storageService.saveTokens(
                  accessToken: payload['access_token'].toString(),
                  refreshToken: payload['refresh_token'].toString(),
                );

                final retryOptions = error.requestOptions;
                retryOptions.extra['retried'] = true;
                retryOptions.headers['Authorization'] =
                    'Bearer ${_storageService.accessToken}';

                final retryResponse = await _dio.fetch(retryOptions);
                return handler.resolve(retryResponse);
              } catch (_) {
                await _storageService.clearSession();
              }
            }
          }

          handler.next(error);
        },
      ),
    );
  }

  Dio _createClient(String baseUrl) {
    return Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 20),
        sendTimeout: const Duration(seconds: 20),
        contentType: Headers.jsonContentType,
        responseType: ResponseType.json,
      ),
    );
  }

  bool _isConnectivityIssue(DioException error) {
    return error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.sendTimeout;
  }

  Future<dynamic> _executeWithFallback(
    Future<Response<dynamic>> Function() request,
    String path,
  ) async {
    DioException? lastConnectivityError;

    for (var index = 0; index < _baseUrlCandidates.length; index++) {
      final baseUrl = _baseUrlCandidates[index];
      if (_dio.options.baseUrl != baseUrl) {
        _initializeClients(baseUrl);
      }

      try {
        final response = await request();
        return response.data;
      } on DioException catch (error) {
        if (!_isConnectivityIssue(error)) {
          throw ApiException.fromResponse(
            statusCode: error.response?.statusCode,
            responseData: error.response?.data,
          );
        }

        lastConnectivityError = error;
        if (index < _baseUrlCandidates.length - 1) {
          continue;
        }
      }
    }

    final attemptedHosts = _baseUrlCandidates.join(', ');
    throw ApiException(
      message:
          'Unable to reach the backend at any configured host: $attemptedHosts',
      statusCode: lastConnectivityError?.response?.statusCode,
    );
  }

  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return _executeWithFallback(
      () => _dio.get(path, queryParameters: queryParameters),
      path,
    );
  }

  Future<dynamic> post(
    String path, {
    Object? data,
    Duration? receiveTimeout,
  }) async {
    return _executeWithFallback(
      () => _dio.post(
        path,
        data: data,
        options: receiveTimeout == null
            ? null
            : Options(receiveTimeout: receiveTimeout),
      ),
      path,
    );
  }

  /// Posts [FormData] (e.g. multipart file upload) to [path].
  ///
  /// Reuses the same authenticated [_dio] client and its JWT interceptor so
  /// the `Authorization` header is attached exactly like other API calls.
  /// The content type is set to `multipart/form-data` for this request only;
  /// the client's default JSON content type is left untouched.
  Future<dynamic> postMultipart(
    String path, {
    required FormData formData,
    ProgressCallback? onSendProgress,
  }) async {
    return _executeWithFallback(
      () => _dio.post(
        path,
        data: formData,
        options: Options(contentType: Headers.multipartFormDataContentType),
        onSendProgress: onSendProgress,
      ),
      path,
    );
  }

  Future<dynamic> put(String path, {Object? data}) async {
    return _executeWithFallback(() => _dio.put(path, data: data), path);
  }

  Future<dynamic> delete(String path, {Object? data}) async {
    return _executeWithFallback(() => _dio.delete(path, data: data), path);
  }
}
