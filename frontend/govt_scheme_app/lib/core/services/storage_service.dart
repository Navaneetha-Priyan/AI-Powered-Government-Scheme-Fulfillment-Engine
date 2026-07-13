import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../models/user_profile.dart';

class StorageService {
  StorageService._(this._preferences);

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _profileKey = 'cached_profile';

  final SharedPreferences _preferences;

  static Future<StorageService> create() async {
    final preferences = await SharedPreferences.getInstance();
    return StorageService._(preferences);
  }

  String? get accessToken => _preferences.getString(_accessTokenKey);

  String? get refreshToken => _preferences.getString(_refreshTokenKey);

  bool get hasTokens => accessToken != null && refreshToken != null;

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _preferences.setString(_accessTokenKey, accessToken);
    await _preferences.setString(_refreshTokenKey, refreshToken);
  }

  Future<void> saveCachedProfile(UserProfile profile) async {
    await _preferences.setString(_profileKey, jsonEncode(profile.toJson()));
  }

  UserProfile? getCachedProfile() {
    final raw = _preferences.getString(_profileKey);
    if (raw == null || raw.isEmpty) {
      return null;
    }

    return UserProfile.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  Future<void> clearSession() async {
    await _preferences.remove(_accessTokenKey);
    await _preferences.remove(_refreshTokenKey);
    await _preferences.remove(_profileKey);
  }
}
