import 'package:flutter/foundation.dart';

import '../core/network/api_exception.dart';
import '../models/auth_models.dart';
import '../models/user_profile.dart';
import '../repositories/profile_repository.dart';
import 'auth_provider.dart';
import 'eligibility_provider.dart';

class ProfileProvider extends ChangeNotifier {
  ProfileProvider(this._profileRepository);

  final ProfileRepository _profileRepository;
  late AuthProvider _authProvider;
  EligibilityProvider? _eligibilityProvider;

  bool _isLoading = false;
  String? _errorMessage;
  UserProfile? _profile;

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  UserProfile? get profile => _profile;

  void attachAuthProvider(AuthProvider authProvider) {
    _authProvider = authProvider;
    _profile ??= authProvider.currentUser;
  }

  void attachEligibilityProvider(EligibilityProvider eligibilityProvider) {
    _eligibilityProvider = eligibilityProvider;
  }

  Future<void> loadProfile() async {
    _setLoading(true);
    try {
      _profile = await _profileRepository.getProfile();
      _authProvider.updateCurrentUser(_profile!);
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error is ApiException ? error.message : error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> updateProfile(Map<String, dynamic> payload) async {
    _setLoading(true);
    try {
      _profile = await _profileRepository.updateProfile(payload);
      _authProvider.updateCurrentUser(_profile!);
      _eligibilityProvider?.invalidateAll();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error is ApiException ? error.message : error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> changePassword(ChangePasswordRequest request) async {
    _setLoading(true);
    try {
      await _profileRepository.changePassword(request);
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error is ApiException ? error.message : error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}
