import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/auth_models.dart';
import '../models/system_models.dart';
import '../models/user_profile.dart';

class AuthRepository {
  AuthRepository(this._apiService);

  final ApiService _apiService;

  Future<AuthTokens> login(LoginRequest request) async {
    final response = await _apiService.post(ApiConstants.login, data: request.toJson());
    return AuthTokens.fromJson(_extractData(response));
  }

  Future<AuthTokens> register(RegisterRequest request) async {
    final response = await _apiService.post(ApiConstants.register, data: request.toJson());
    return AuthTokens.fromJson(_extractData(response));
  }

  Future<AuthTokens> refresh(String refreshToken) async {
    final response = await _apiService.post(
      ApiConstants.refresh,
      data: RefreshTokenRequest(refreshToken).toJson(),
    );
    return AuthTokens.fromJson(_extractData(response));
  }

  Future<Map<String, dynamic>> verifyToken(String token) async {
    final response = await _apiService.post(
      ApiConstants.verifyToken,
      data: {'token': token},
    );
    return _extractData(response);
  }

  Future<void> logout() async {
    await _apiService.post(ApiConstants.logout, data: {});
  }

  Future<UserProfile> getCurrentUser() async {
    final response = await _apiService.get(ApiConstants.me);
    return UserProfile.fromJson(_extractData(response));
  }

  Future<BackendHealth> getHealth() async {
    final response = await _apiService.get(ApiConstants.health);
    return BackendHealth.fromJson(_extractData(response));
  }

  Future<BackendInfo> getInfo() async {
    final response = await _apiService.get(ApiConstants.info);
    return BackendInfo.fromJson(_extractData(response));
  }

  Future<String> getVersion() async {
    final response = await _apiService.get(ApiConstants.version);
    final data = _extractData(response);
    return data['version']?.toString() ?? 'unknown';
  }

  Map<String, dynamic> _extractData(dynamic response) {
    if (response is Map<String, dynamic> && response['data'] is Map<String, dynamic>) {
      return Map<String, dynamic>.from(response['data'] as Map);
    }

    if (response is Map<String, dynamic>) {
      return response;
    }

    throw StateError('Unexpected response payload');
  }
}
