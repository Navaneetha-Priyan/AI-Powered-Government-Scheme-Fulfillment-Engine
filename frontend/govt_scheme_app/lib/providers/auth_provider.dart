import 'package:flutter/foundation.dart';

import '../core/network/api_exception.dart';
import '../core/services/storage_service.dart';
import '../models/auth_models.dart';
import '../models/user_profile.dart';
import '../repositories/auth_repository.dart';
import '../repositories/profile_repository.dart';

enum AuthStatus { unknown, unauthenticated, authenticated }

class AuthProvider extends ChangeNotifier {
  AuthProvider(
    this._authRepository,
    this._profileRepository,
    this._storageService,
  );

  final AuthRepository _authRepository;
  final ProfileRepository _profileRepository;
  final StorageService _storageService;

  AuthStatus _status = AuthStatus.unknown;
  bool _isBusy = false;
  String? _errorMessage;
  UserProfile? _currentUser;

  AuthStatus get status => _status;
  bool get isBusy => _isBusy;
  String? get errorMessage => _errorMessage;
  UserProfile? get currentUser => _currentUser;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  Future<void> bootstrap() async {
    if (!_storageService.hasTokens) {
      _status = AuthStatus.unauthenticated;
      _currentUser = null;
      notifyListeners();
      return;
    }

    _setBusy(true);
    try {
      _currentUser = await _profileRepository.getProfile();
      await _storageService.saveCachedProfile(_currentUser!);
      _status = AuthStatus.authenticated;
      _errorMessage = null;
    } catch (_) {
      await logout(silent: true);
    } finally {
      _setBusy(false);
    }
  }

  Future<void> login(LoginRequest request) async {
    await _authenticate(() => _authRepository.login(request));
  }

  Future<void> register(RegisterRequest request) async {
    await _authenticate(() => _authRepository.register(request));
  }

  Future<void> _authenticate(Future<AuthTokens> Function() action) async {
    _setBusy(true);
    try {
      final tokens = await action();
      await _storageService.saveTokens(
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
      );
      _currentUser = await _profileRepository.getProfile();
      await _storageService.saveCachedProfile(_currentUser!);
      _status = AuthStatus.authenticated;
      _errorMessage = null;
    } on ApiException catch (error) {
      _errorMessage = error.message;
      rethrow;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setBusy(false);
    }
  }

  Future<void> refreshProfile() async {
    _setBusy(true);
    try {
      _currentUser = await _profileRepository.getProfile();
      await _storageService.saveCachedProfile(_currentUser!);
      _status = AuthStatus.authenticated;
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setBusy(false);
    }
  }

  Future<void> logout({bool silent = false}) async {
    if (!silent) {
      _setBusy(true);
    }

    try {
      if (_storageService.hasTokens) {
        await _authRepository.logout();
      }
    } catch (_) {
      // Logout should always clear the local session even if the backend call fails.
    } finally {
      await _storageService.clearSession();
      _currentUser = null;
      _status = AuthStatus.unauthenticated;
      _errorMessage = null;
      if (!silent) {
        _setBusy(false);
      } else {
        notifyListeners();
      }
    }
  }

  void updateCurrentUser(UserProfile profile) {
    _currentUser = profile;
    _status = AuthStatus.authenticated;
    _storageService.saveCachedProfile(profile);
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  void _setBusy(bool value) {
    _isBusy = value;
    notifyListeners();
  }
}
