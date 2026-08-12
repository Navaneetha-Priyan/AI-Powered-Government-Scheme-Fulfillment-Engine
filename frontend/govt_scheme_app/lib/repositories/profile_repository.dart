import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/auth_models.dart';
import '../models/user_profile.dart';

class ProfileRepository {
  ProfileRepository(this._apiService);

  final ApiService _apiService;

  Future<UserProfile> getProfile() async {
    final response = await _apiService.get(ApiConstants.me);
    return UserProfile.fromJson(_extractData(response));
  }

  Future<UserProfile> updateProfile(Map<String, dynamic> payload) async {
    final response = await _apiService.put(ApiConstants.profile, data: payload);
    return UserProfile.fromJson(_extractData(response));
  }

  Future<void> changePassword(ChangePasswordRequest request) async {
    await _apiService.put(ApiConstants.changePassword, data: request.toJson());
  }

  Map<String, dynamic> _extractData(dynamic response) {
    if (response is Map<String, dynamic> &&
        response['data'] is Map<String, dynamic>) {
      return Map<String, dynamic>.from(response['data'] as Map);
    }

    if (response is Map<String, dynamic>) {
      return response;
    }

    throw StateError('Unexpected response payload');
  }
}
