import 'package:flutter/foundation.dart';

import '../models/citizen_models.dart';
import '../repositories/dashboard_repository.dart';

class DashboardProvider extends ChangeNotifier {
  DashboardProvider(this._repository);

  final DashboardRepository _repository;

  CitizenDashboard? _dashboard;
  bool _isLoading = false;
  String? _errorMessage;

  CitizenDashboard? get dashboard => _dashboard;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadDashboard() async {
    if (_isLoading) return;
    _setLoading(true);
    try {
      _dashboard = await _repository.getDashboard();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> refresh() => loadDashboard();

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}
