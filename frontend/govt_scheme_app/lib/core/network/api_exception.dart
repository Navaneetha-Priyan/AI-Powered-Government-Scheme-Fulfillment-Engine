class ApiException implements Exception {
  ApiException({
    required this.message,
    this.statusCode,
    this.code,
    this.details,
  });

  final String message;
  final int? statusCode;
  final String? code;
  final Map<String, dynamic>? details;

  factory ApiException.fromResponse({int? statusCode, dynamic responseData}) {
    if (responseData is Map<String, dynamic>) {
      final dynamic detail = responseData['detail'];
      if (detail is Map<String, dynamic>) {
        return ApiException(
          message:
              (detail['message'] ?? responseData['message'] ?? 'Request failed')
                  .toString(),
          statusCode: statusCode,
          code:
              detail['error']?.toString() ?? responseData['error']?.toString(),
          details: detail['details'] is Map<String, dynamic>
              ? Map<String, dynamic>.from(detail['details'] as Map)
              : null,
        );
      }

      return ApiException(
        message:
            (responseData['message'] ??
                    responseData['detail'] ??
                    'Request failed')
                .toString(),
        statusCode: statusCode,
        code: responseData['error']?.toString(),
        details: responseData['details'] is Map<String, dynamic>
            ? Map<String, dynamic>.from(responseData['details'] as Map)
            : null,
      );
    }

    return ApiException(message: 'Request failed', statusCode: statusCode);
  }

  @override
  String toString() => message;
}
