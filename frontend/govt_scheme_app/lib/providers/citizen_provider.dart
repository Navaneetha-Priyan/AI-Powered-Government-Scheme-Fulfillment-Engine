import 'package:flutter/foundation.dart';

import '../models/citizen_models.dart';
import '../repositories/citizen_repository.dart';
import 'eligibility_provider.dart';

/// State for profile display and small, supported manual corrections only.
class CitizenProvider extends ChangeNotifier {
  CitizenProvider(this._repository);

  final CitizenRepository _repository;
  EligibilityProvider? _eligibilityProvider;
  ExtendedProfile? _extendedProfile;
  Map<String, dynamic>? _profileDetails;
  bool _isLoading = false;
  String? _errorMessage;

  ExtendedProfile? get extendedProfile => _extendedProfile;
  Map<String, dynamic>? get profileDetails => _profileDetails;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  void attachEligibilityProvider(EligibilityProvider provider) =>
      _eligibilityProvider = provider;

  Future<void> loadProfileDetails() async {
    await _load(() async {
      _profileDetails = await _repository.getProfileDetails();
      _extendedProfile = ExtendedProfile.fromJson(
        _profileDetails?['extended_profile'] is Map
            ? Map<String, dynamic>.from(
                _profileDetails!['extended_profile'] as Map,
              )
            : null,
      );
    });
  }

  Future<void> updateExtendedProfile(Map<String, dynamic> payload) async {
    await _load(() async {
      _extendedProfile = await _repository.updateExtendedProfile(payload);
      _eligibilityProvider?.invalidateAll();
    });
  }

  Future<void> _load(Future<void> Function() action) async {
    _isLoading = true;
    notifyListeners();
    try {
      await action();
      _errorMessage = null;
    } catch (error) {
      _errorMessage = error.toString();
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
