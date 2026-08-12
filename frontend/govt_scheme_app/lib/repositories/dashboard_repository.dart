import '../core/constants/api_constants.dart';
import '../core/network/api_service.dart';
import '../models/citizen_models.dart';

class DashboardRepository {
  DashboardRepository(this._apiService);

  final ApiService _apiService;

  Future<CitizenDashboard> getDashboard() async {
    final response = await _apiService.get(ApiConstants.citizenDashboard);
    final data =
        response is Map<String, dynamic> &&
            response['data'] is Map<String, dynamic>
        ? Map<String, dynamic>.from(response['data'] as Map)
        : Map<String, dynamic>.from(response as Map);
    return CitizenDashboard.fromJson(data);
  }
}
