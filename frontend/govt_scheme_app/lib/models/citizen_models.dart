import 'package:flutter/foundation.dart';

DateTime? parseApiDate(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value.toString());
}

double? parseApiDouble(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

int? parseApiInt(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value.toString());
}

bool parseApiBool(dynamic value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  return value?.toString().toLowerCase() == 'true';
}

String? optionalString(dynamic value) {
  final text = value?.toString();
  if (text == null || text.trim().isEmpty || text == 'null') {
    return null;
  }
  return text;
}

@immutable
class ExtendedProfile {
  const ExtendedProfile({
    required this.profileCompletionPercentage,
    required this.syncStatus,
    required this.isDisabled,
    required this.isFarmer,
    this.id,
    this.citizenId,
    this.fatherName,
    this.motherName,
    this.occupation,
    this.maritalStatus,
    this.bloodGroup,
    this.nationality,
    this.annualIncome,
    this.incomeCategory,
    this.caste,
    this.community,
    this.subCaste,
    this.religion,
    this.disabilityType,
    this.disabilityPercentage,
    this.farmerId,
    this.educationLevel,
    this.educationInstitution,
    this.familyMemberCount,
    this.familyDetails,
    this.lastSyncedAt,
  });

  final String? id;
  final String? citizenId;
  final String? fatherName;
  final String? motherName;
  final String? occupation;
  final String? maritalStatus;
  final String? bloodGroup;
  final String? nationality;
  final double? annualIncome;
  final String? incomeCategory;
  final String? caste;
  final String? community;
  final String? subCaste;
  final String? religion;
  final bool isDisabled;
  final String? disabilityType;
  final int? disabilityPercentage;
  final bool isFarmer;
  final String? farmerId;
  final String? educationLevel;
  final String? educationInstitution;
  final int? familyMemberCount;
  final String? familyDetails;
  final int profileCompletionPercentage;
  final String syncStatus;
  final DateTime? lastSyncedAt;

  factory ExtendedProfile.fromJson(Map<String, dynamic>? json) {
    final source = json ?? const <String, dynamic>{};
    return ExtendedProfile(
      id: optionalString(source['id']),
      citizenId: optionalString(source['citizen_id']),
      fatherName: optionalString(source['father_name']),
      motherName: optionalString(source['mother_name']),
      occupation: optionalString(source['occupation']),
      maritalStatus: optionalString(source['marital_status']),
      bloodGroup: optionalString(source['blood_group']),
      nationality: optionalString(source['nationality']),
      annualIncome: parseApiDouble(source['annual_income']),
      incomeCategory: optionalString(source['income_category']),
      caste: optionalString(source['caste']),
      community: optionalString(source['community']),
      subCaste: optionalString(source['sub_caste']),
      religion: optionalString(source['religion']),
      isDisabled: parseApiBool(source['is_disabled']),
      disabilityType: optionalString(source['disability_type']),
      disabilityPercentage: parseApiInt(source['disability_percentage']),
      isFarmer: parseApiBool(source['is_farmer']),
      farmerId: optionalString(source['farmer_id']),
      educationLevel: optionalString(source['education_level']),
      educationInstitution: optionalString(source['education_institution']),
      familyMemberCount: parseApiInt(source['family_member_count']),
      familyDetails: optionalString(source['family_details']),
      profileCompletionPercentage:
          parseApiInt(source['profile_completion_percentage']) ?? 0,
      syncStatus: optionalString(source['sync_status']) ?? 'not_synced',
      lastSyncedAt: parseApiDate(source['last_synced_at']),
    );
  }
}

@immutable
class LandRecord {
  const LandRecord({
    required this.id,
    this.surveyNumber,
    this.landArea,
    this.landAreaUnit,
    this.landType,
    this.village,
    this.taluk,
    this.district,
    this.state,
    this.ownershipType,
    this.pattaNumber,
  });

  final String id;
  final String? surveyNumber;
  final double? landArea;
  final String? landAreaUnit;
  final String? landType;
  final String? village;
  final String? taluk;
  final String? district;
  final String? state;
  final String? ownershipType;
  final String? pattaNumber;

  factory LandRecord.fromJson(Map<String, dynamic> json) {
    return LandRecord(
      id: optionalString(json['id']) ?? '',
      surveyNumber: optionalString(json['survey_number']),
      landArea: parseApiDouble(json['land_area']),
      landAreaUnit: optionalString(json['land_area_unit']),
      landType: optionalString(json['land_type']),
      village: optionalString(json['village']),
      taluk: optionalString(json['taluk']),
      district: optionalString(json['district']),
      state: optionalString(json['state']),
      ownershipType: optionalString(json['ownership_type']),
      pattaNumber: optionalString(json['patta_number']),
    );
  }
}

@immutable
class GovernmentDocument {
  const GovernmentDocument({
    required this.id,
    required this.documentName,
    required this.documentType,
    required this.verificationStatus,
    required this.isActive,
    this.documentNumber,
    this.issueDate,
    this.expiryDate,
    this.verifiedBy,
    this.verifiedAt,
    this.downloadUrl,
    this.metadata,
    this.createdAt,
  });

  final String id;
  final String documentName;
  final String documentType;
  final String? documentNumber;
  final DateTime? issueDate;
  final DateTime? expiryDate;
  final String verificationStatus;
  final String? verifiedBy;
  final DateTime? verifiedAt;
  final String? downloadUrl;
  final String? metadata;
  final DateTime? createdAt;
  final bool isActive;

  factory GovernmentDocument.fromJson(Map<String, dynamic> json) {
    return GovernmentDocument(
      id: optionalString(json['id']) ?? '',
      documentName: optionalString(json['document_name']) ?? 'Government Document',
      documentType: optionalString(json['document_type']) ?? 'document',
      documentNumber: optionalString(json['document_number']),
      issueDate: parseApiDate(json['issue_date']),
      expiryDate: parseApiDate(json['expiry_date']),
      verificationStatus:
          optionalString(json['verification_status']) ?? 'pending',
      verifiedBy: optionalString(json['verified_by']),
      verifiedAt: parseApiDate(json['verified_at']),
      downloadUrl: optionalString(json['download_url']),
      metadata: optionalString(json['doc_metadata']),
      createdAt: parseApiDate(json['created_at']),
      isActive: json['is_active'] != false,
    );
  }
}

@immutable
class CitizenDashboard {
  const CitizenDashboard({
    required this.citizenId,
    required this.fullName,
    required this.email,
    required this.phone,
    required this.district,
    required this.state,
    required this.extendedProfile,
    required this.landRecords,
    required this.totalLandArea,
    required this.totalDocuments,
    required this.verifiedDocuments,
    required this.digilockerSynced,
    required this.profileCompletionPercentage,
    this.gender,
    this.dateOfBirth,
    this.profilePhotoUrl,
    this.aadhaarNumber,
    this.smartRationCard,
    this.addressLine1,
    this.addressLine2,
    this.village,
    this.taluk,
    this.pincode,
    this.lastSyncedAt,
    this.lastLogin,
  });

  final String citizenId;
  final String fullName;
  final String email;
  final String phone;
  final String? gender;
  final DateTime? dateOfBirth;
  final String? profilePhotoUrl;
  final String? aadhaarNumber;
  final String? smartRationCard;
  final String? addressLine1;
  final String? addressLine2;
  final String? village;
  final String? taluk;
  final String district;
  final String state;
  final String? pincode;
  final ExtendedProfile extendedProfile;
  final List<LandRecord> landRecords;
  final double totalLandArea;
  final int totalDocuments;
  final int verifiedDocuments;
  final bool digilockerSynced;
  final DateTime? lastSyncedAt;
  final DateTime? lastLogin;
  final int profileCompletionPercentage;

  factory CitizenDashboard.fromJson(Map<String, dynamic> json) {
    final records = (json['land_records'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => LandRecord.fromJson(Map<String, dynamic>.from(item)))
        .toList();

    return CitizenDashboard(
      citizenId: optionalString(json['citizen_id']) ?? '',
      fullName: optionalString(json['full_name']) ?? 'Citizen',
      email: optionalString(json['email']) ?? '',
      phone: optionalString(json['phone']) ?? '',
      gender: optionalString(json['gender']),
      dateOfBirth: parseApiDate(json['date_of_birth']),
      profilePhotoUrl: optionalString(json['profile_photo_url']),
      aadhaarNumber: optionalString(json['aadhaar_number']),
      smartRationCard: optionalString(json['smart_ration_card']),
      addressLine1: optionalString(json['address_line1']),
      addressLine2: optionalString(json['address_line2']),
      village: optionalString(json['village']),
      taluk: optionalString(json['taluk']),
      district: optionalString(json['district']) ?? '',
      state: optionalString(json['state']) ?? '',
      pincode: optionalString(json['pincode']),
      extendedProfile: ExtendedProfile.fromJson(
        json['extended_profile'] is Map
            ? Map<String, dynamic>.from(json['extended_profile'] as Map)
            : null,
      ),
      landRecords: records,
      totalLandArea: parseApiDouble(json['total_land_area']) ?? 0,
      totalDocuments: parseApiInt(json['total_documents']) ?? 0,
      verifiedDocuments: parseApiInt(json['verified_documents']) ?? 0,
      digilockerSynced: parseApiBool(json['digilocker_synced']),
      lastSyncedAt: parseApiDate(json['last_synced_at']),
      lastLogin: parseApiDate(json['last_login']),
      profileCompletionPercentage:
          parseApiInt(json['profile_completion_percentage']) ?? 0,
    );
  }
}

@immutable
class IncomeDetails {
  const IncomeDetails({
    this.annualIncome,
    this.incomeCategory,
    this.occupation,
    required this.isFarmer,
    this.farmerId,
    this.incomeCertificate,
  });

  final double? annualIncome;
  final String? incomeCategory;
  final String? occupation;
  final bool isFarmer;
  final String? farmerId;
  final GovernmentDocument? incomeCertificate;

  factory IncomeDetails.fromJson(Map<String, dynamic> json) {
    return IncomeDetails(
      annualIncome: parseApiDouble(json['annual_income']),
      incomeCategory: optionalString(json['income_category']),
      occupation: optionalString(json['occupation']),
      isFarmer: parseApiBool(json['is_farmer']),
      farmerId: optionalString(json['farmer_id']),
      incomeCertificate: json['income_certificate'] is Map
          ? GovernmentDocument.fromJson(
              Map<String, dynamic>.from(json['income_certificate'] as Map),
            )
          : null,
    );
  }
}

@immutable
class CasteDetails {
  const CasteDetails({
    this.caste,
    this.community,
    this.subCaste,
    this.religion,
    this.category,
    this.communityCertificate,
  });

  final String? caste;
  final String? community;
  final String? subCaste;
  final String? religion;
  final String? category;
  final GovernmentDocument? communityCertificate;

  factory CasteDetails.fromJson(Map<String, dynamic> json) {
    return CasteDetails(
      caste: optionalString(json['caste']),
      community: optionalString(json['community']),
      subCaste: optionalString(json['sub_caste']),
      religion: optionalString(json['religion']),
      category:
          optionalString(json['category']) ?? optionalString(json['community']),
      communityCertificate: json['community_certificate'] is Map
          ? GovernmentDocument.fromJson(
              Map<String, dynamic>.from(json['community_certificate'] as Map),
            )
          : null,
    );
  }
}

@immutable
class DigiLockerStatus {
  const DigiLockerStatus({
    required this.isActive,
    required this.totalDocuments,
    required this.verifiedDocuments,
    required this.pendingDocuments,
    required this.expiredDocuments,
    this.citizenId,
    this.digilockerId,
    this.lastSyncAt,
    this.syncCount,
  });

  final String? citizenId;
  final String? digilockerId;
  final bool isActive;
  final DateTime? lastSyncAt;
  final String? syncCount;
  final int totalDocuments;
  final int verifiedDocuments;
  final int pendingDocuments;
  final int expiredDocuments;

  factory DigiLockerStatus.fromJson(Map<String, dynamic> json) {
    return DigiLockerStatus(
      citizenId: optionalString(json['citizen_id']),
      digilockerId: optionalString(json['digilocker_id']),
      isActive: parseApiBool(json['is_active']),
      lastSyncAt: parseApiDate(json['last_sync_at']),
      syncCount: optionalString(json['sync_count']),
      totalDocuments: parseApiInt(json['total_documents']) ?? 0,
      verifiedDocuments: parseApiInt(json['verified_documents']) ?? 0,
      pendingDocuments: parseApiInt(json['pending_documents']) ?? 0,
      expiredDocuments: parseApiInt(json['expired_documents']) ?? 0,
    );
  }
}

@immutable
class DigiLockerSyncResult {
  const DigiLockerSyncResult({
    required this.syncStatus,
    required this.documentsSynced,
    required this.profileUpdated,
    required this.message,
  });

  final String syncStatus;
  final int documentsSynced;
  final bool profileUpdated;
  final String message;

  factory DigiLockerSyncResult.fromJson(Map<String, dynamic> json) {
    return DigiLockerSyncResult(
      syncStatus: optionalString(json['sync_status']) ?? 'unknown',
      documentsSynced: parseApiInt(json['documents_synced']) ?? 0,
      profileUpdated: parseApiBool(json['profile_updated']),
      message: optionalString(json['message']) ?? 'DigiLocker sync completed',
    );
  }
}

@immutable
class LandRecordSummary {
  const LandRecordSummary({
    required this.totalLandArea,
    required this.records,
  });

  final double totalLandArea;
  final List<LandRecord> records;

  factory LandRecordSummary.fromJson(Map<String, dynamic> json) {
    final records = (json['land_records'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => LandRecord.fromJson(Map<String, dynamic>.from(item)))
        .toList();

    return LandRecordSummary(
      totalLandArea: parseApiDouble(json['total_land_area']) ??
          records.fold<double>(0, (sum, record) => sum + (record.landArea ?? 0)),
      records: records,
    );
  }
}

@immutable
class DocumentSummary {
  const DocumentSummary({
    required this.totalDocuments,
    required this.documents,
  });

  final int totalDocuments;
  final List<GovernmentDocument> documents;

  factory DocumentSummary.fromJson(Map<String, dynamic> json) {
    final documents = (json['documents'] as List? ?? const [])
        .whereType<Map>()
        .map((item) =>
            GovernmentDocument.fromJson(Map<String, dynamic>.from(item)))
        .toList();

    return DocumentSummary(
      totalDocuments: parseApiInt(json['total_documents']) ?? documents.length,
      documents: documents,
    );
  }
}
