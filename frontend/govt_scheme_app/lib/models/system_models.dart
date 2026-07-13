DateTime? _parseDate(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value.toString());
}

class BackendHealth {
  BackendHealth({
    required this.status,
    required this.version,
    required this.database,
    required this.environment,
    required this.timestamp,
  });

  final String status;
  final String version;
  final String database;
  final String environment;
  final DateTime timestamp;

  factory BackendHealth.fromJson(Map<String, dynamic> json) {
    return BackendHealth(
      status: json['status']?.toString() ?? 'degraded',
      version: json['version']?.toString() ?? 'unknown',
      database: json['database']?.toString() ?? 'disconnected',
      environment: json['environment']?.toString() ?? 'unknown',
      timestamp: _parseDate(json['timestamp']) ?? DateTime.now(),
    );
  }
}

class BackendInfo {
  BackendInfo({
    required this.appName,
    required this.version,
    required this.description,
    required this.environment,
    required this.debugMode,
    required this.docsUrl,
    required this.openapiUrl,
  });

  final String appName;
  final String version;
  final String description;
  final String environment;
  final bool debugMode;
  final String docsUrl;
  final String openapiUrl;

  factory BackendInfo.fromJson(Map<String, dynamic> json) {
    return BackendInfo(
      appName: json['app_name']?.toString() ?? 'Backend',
      version: json['version']?.toString() ?? 'unknown',
      description: json['description']?.toString() ?? '',
      environment: json['environment']?.toString() ?? 'unknown',
      debugMode: json['debug_mode'] == true,
      docsUrl: json['docs_url']?.toString() ?? '',
      openapiUrl: json['openapi_url']?.toString() ?? '',
    );
  }
}
