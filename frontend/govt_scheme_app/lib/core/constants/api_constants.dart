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
        'http://10.80.26.147:8000',
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
  static const String citizenIncome = '/citizen/income';
  static const String citizenCaste = '/citizen/caste';
  static const String citizenLandRecords = '/citizen/land-records';
  static const String citizenDocuments = '/citizen/documents';

  static const String digilockerSync = '/digilocker/sync';
  static const String digilockerStatus = '/digilocker/status';
  static const String digilockerDocuments = '/digilocker/documents';

  static String digilockerDocument(String documentId) {
    return '/digilocker/documents/$documentId';
  }
}
