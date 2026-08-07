import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:govt_scheme_app/core/network/api_service.dart';
import 'package:govt_scheme_app/core/services/storage_service.dart';
import 'package:govt_scheme_app/models/citizen_models.dart';
import 'package:govt_scheme_app/providers/digilocker_provider.dart';
import 'package:govt_scheme_app/repositories/digilocker_repository.dart';

class _FakeDigiLockerRepository extends DigiLockerRepository {
  _FakeDigiLockerRepository(super.apiService);

  @override
  Future<DigiLockerStatus> getStatus() async {
    await Future<void>.delayed(const Duration(milliseconds: 20));
    return const DigiLockerStatus(
      isActive: true,
      totalDocuments: 1,
      verifiedDocuments: 1,
      pendingDocuments: 0,
      expiredDocuments: 0,
    );
  }

  @override
  Future<DocumentSummary> getDocuments() async {
    await Future<void>.delayed(const Duration(milliseconds: 50));
    return const DocumentSummary(totalDocuments: 0, documents: <GovernmentDocument>[]);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  test('keeps loading state active while overlapping requests are in flight', () async {
    final storage = await StorageService.create();
    final apiService = ApiService(storageService: storage);
    final provider = DigiLockerProvider(_FakeDigiLockerRepository(apiService));

    final statusFuture = provider.loadStatus();
    final documentsFuture = provider.loadDocuments();

    await Future<void>.delayed(const Duration(milliseconds: 25));

    expect(provider.isLoading, isTrue);

    await Future.wait<void>([statusFuture, documentsFuture]);
  });
}
