import 'package:flutter/foundation.dart';

import '../core/network/api_exception.dart';
import '../repositories/auth_repository.dart';
import '../models/system_models.dart';

class AppProvider extends ChangeNotifier {
  AppProvider(this._authRepository);

  final AuthRepository _authRepository;

  bool _isLoading = false;
  String? _errorMessage;
  BackendHealth? _backendHealth;
  BackendInfo? _backendInfo;
  String? _version;

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  BackendHealth? get backendHealth => _backendHealth;
  BackendInfo? get backendInfo => _backendInfo;
  String? get version => _version;
  bool get backendReachable => _backendHealth != null;

  Future<void> initialize() async {
    _setLoading(true);
    try {
      _backendHealth = await _authRepository.getHealth();
      _backendInfo = await _authRepository.getInfo();
      _version = await _authRepository.getVersion();
      _errorMessage = null;
    } on ApiException catch (error) {
      _errorMessage = error.message;
      _backendHealth = null;
      _backendInfo = null;
      _version = null;
    } catch (_) {
      _errorMessage = 'Unable to reach the backend service';
      _backendHealth = null;
      _backendInfo = null;
      _version = null;
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}
