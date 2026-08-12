/// Models for the document intelligence workflow.
/// Matches backend models/citizen_document.py and document_intelligence_routes.py
class CitizenDocument {
  const CitizenDocument({
    required this.id,
    required this.type,
    required this.fileName,
    required this.fileSize,
    required this.uploadStatus,
    required this.verificationStatus,
    this.error,
  });

  final String id;
  final String type;
  final String fileName;
  final num fileSize;

  /// Values: uploaded | processing | processed | needs_review | verified | failed
  final String uploadStatus;

  /// Values: pending | verified | rejected
  final String verificationStatus;

  final String? error;

  /// Legacy alias kept for backward compatibility with existing widgets.
  String get status => uploadStatus;

  factory CitizenDocument.fromJson(Map<String, dynamic> json) =>
      CitizenDocument(
        id: json['id']?.toString() ?? '',
        type: json['document_type']?.toString() ?? 'unknown',
        fileName: json['original_file_name']?.toString() ?? 'Document',
        fileSize: json['file_size'] as num? ?? 0,
        uploadStatus: json['upload_status']?.toString() ?? 'uploaded',
        verificationStatus:
            json['verification_status']?.toString() ?? 'pending',
        error: json['processing_error']?.toString(),
      );
}

class ProfilePreview {
  const ProfilePreview({
    required this.fields,
    required this.conflicts,
    required this.needsReview,
  });

  final Map<String, dynamic> fields;
  final List<Map<String, dynamic>> conflicts;
  final int needsReview;

  factory ProfilePreview.fromJson(Map<String, dynamic> json) => ProfilePreview(
    fields: Map<String, dynamic>.from(json['fields'] as Map? ?? const {}),
    conflicts: (json['conflicts'] as List? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList(),
    needsReview: (json['needs_review'] as num?)?.toInt() ?? 0,
  );
}
