import 'package:flutter/foundation.dart';

import '../core/network/api_exception.dart';
import '../models/india_location_models.dart';
import '../repositories/india_location_repository.dart';

class IndiaLocationProvider extends ChangeNotifier {
  IndiaLocationProvider(this._repository);

  final IndiaLocationRepository _repository;

  bool _isLoading = false;
  String? _errorMessage;
  IndiaLocations _locations = IndiaLocations.fallback();

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  List<String> get states => _locations.states;

  List<String> districtsFor(String state) {
    return _locations.districtsByState[state] ?? const [];
  }

  Future<void> loadLocations() async {
    if (_locations.districtsByState.isNotEmpty) {
      return;
    }

    _setLoading(true);
    try {
      _locations = await _repository.getLocations();
      _errorMessage = null;
    } catch (error) {
      _locations = IndiaLocations.fallback();
      _errorMessage = error is ApiException ? error.message : error.toString();
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}
