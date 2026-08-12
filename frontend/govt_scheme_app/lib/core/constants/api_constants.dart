import 'package:flutter/foundation.dart';

class ApiConstants {
  ApiConstants._();

  static const String _overrideBaseUrl = String.fromEnvironment('API_BASE_URL');

  static List<String> get baseUrlCandidates {
    if (_overrideBaseUrl.isNotEmpty) {
      return [_overrideBaseUrl];
    }

    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return const [
        'http://10.124.204.147:8000',
        'http://10.0.2.2:8000',
        'http://127.0.0.1:8000',
        'http://localhost:8000',
      ];
    }

    return const ['http://localhost:8000'];
  }

  static String get baseUrl {
    return baseUrlCandidates.first;
  }

  static const String health = '/health';
  static const String version = '/version';
  static const String info = '/info';
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String me = '/auth/me';
  static const String profile = '/auth/profile';
  static const String changePassword = '/auth/change-password';
  static const String logout = '/auth/logout';
  static const String verifyToken = '/auth/verify-token';

  static const String citizenProfile = '/citizen/profile';
  static const String citizenProfileDetails = '/citizen/profile/details';
  static const String citizenDashboard = '/citizen/dashboard';

  static const String digilockerSync = '/digilocker/sync';
  static const String digilockerStatus = '/digilocker/status';
  static const String digilockerDocuments = '/digilocker/documents';
  static const String schemes = '/api/schemes';
  static const String schemeSearch = '/api/search/schemes';
  static const String eligibilityCheck = '/api/eligibility/check';
  static const String eligibilityPreview = '/api/eligibility/preview';
  static const String eligibilityRules = '/api/eligibility/rules';

  static const String recommendations = '/api/recommendations';
  static const String recommendationGenerate = '/api/recommendations/generate';
  static const String recommendationRefresh = '/api/recommendations/refresh';
  static const String recommendationHistory = '/api/recommendations/history';

  static const String voiceTranscribe = '/voice/transcribe';
  static const String voiceRecommend = '/voice/recommend';

  // Citizen document intelligence (the backend-first profile workflow).
  static const String intelligentDocuments = '/api/documents';
  static const String processAllDocuments = '/api/documents/process-all';
  static const String profilePreview = '/api/profile/preview';
  static const String profileCompleteness = '/api/profile/completeness';
  static const String profileConfirm = '/api/profile/confirm';

  static String intelligentDocumentUpload(String documentType) =>
      '/api/documents/$documentType/upload';

  static String recommendationDetail(String recommendationId) {
    return '/api/recommendations/$recommendationId';
  }

  static String digilockerDocument(String documentId) {
    return '/digilocker/documents/$documentId';
  }
}
