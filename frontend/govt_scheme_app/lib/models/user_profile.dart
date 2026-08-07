import 'package:flutter/foundation.dart';

DateTime? _parseDate(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value.toString());
}

@immutable
class UserProfile {
  const UserProfile({
    required this.id,
    required this.email,
    required this.phone,
    required this.fullName,
    required this.district,
    required this.state,
    required this.emailVerified,
    required this.phoneVerified,
    required this.accountActive,
    required this.status,
    required this.preferredLanguage,
    required this.createdAt,
    required this.updatedAt,
    this.aadhaarNumber,
    this.smartRationCard,
    this.gender,
    this.dateOfBirth,
    this.addressLine1,
    this.addressLine2,
    this.village,
    this.taluk,
    this.pincode,
    this.profilePhotoUrl,
    this.lastLogin,
  });

  final String id;
  final String email;
  final String phone;
  final String fullName;
  final String district;
  final String state;
  final bool emailVerified;
  final bool phoneVerified;
  final bool accountActive;
  final String status;
  final String preferredLanguage;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? aadhaarNumber;
  final String? smartRationCard;
  final String? gender;
  final DateTime? dateOfBirth;
  final String? addressLine1;
  final String? addressLine2;
  final String? village;
  final String? taluk;
  final String? pincode;
  final String? profilePhotoUrl;
  final DateTime? lastLogin;

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id']?.toString() ?? json['citizen_id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      phone: json['phone']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      district: json['district']?.toString() ?? '',
      state: json['state']?.toString() ?? '',
      emailVerified: json['email_verified'] == true,
      phoneVerified: json['phone_verified'] == true,
      accountActive: json['account_active'] != false,
      status: json['status']?.toString() ?? 'active',
      preferredLanguage: json['preferred_language']?.toString() ?? 'en',
      createdAt: _parseDate(json['created_at']) ?? DateTime.now(),
      updatedAt: _parseDate(json['updated_at']) ?? DateTime.now(),
      aadhaarNumber: json['aadhaar_number']?.toString(),
      smartRationCard: json['smart_ration_card']?.toString(),
      gender: json['gender']?.toString(),
      dateOfBirth: _parseDate(json['date_of_birth']),
      addressLine1: json['address_line1']?.toString(),
      addressLine2: json['address_line2']?.toString(),
      village: json['village']?.toString(),
      taluk: json['taluk']?.toString(),
      pincode: json['pincode']?.toString(),
      profilePhotoUrl: json['profile_photo_url']?.toString(),
      lastLogin: _parseDate(json['last_login']),
    );
  }

  factory UserProfile.fromCitizenProfileDetails({
    required UserProfile baseProfile,
    required Map<String, dynamic> citizenProfileDetails,
  }) {
    final source = Map<String, dynamic>.from(citizenProfileDetails);
    final preferredName = source['full_name']?.toString();
    final preferredPhone = source['phone']?.toString();
    final preferredGender = source['gender']?.toString();
    final preferredDateOfBirth = _parseDate(source['date_of_birth']);
    final preferredAddressLine1 = source['address_line1']?.toString();
    final preferredAddressLine2 = source['address_line2']?.toString();
    final preferredVillage = source['village']?.toString();
    final preferredTaluk = source['taluk']?.toString();
    final preferredDistrict = source['district']?.toString();
    final preferredState = source['state']?.toString();
    final preferredPincode = source['pincode']?.toString();
    final preferredPhotoUrl = source['profile_photo_url']?.toString();
    final preferredEmail = source['email']?.toString();
    final preferredAadhaar = source['aadhaar_number']?.toString();
    final preferredRationCard = source['smart_ration_card']?.toString();

    return UserProfile(
      id: baseProfile.id,
      email: preferredEmail ?? baseProfile.email,
      phone: preferredPhone ?? baseProfile.phone,
      fullName: preferredName ?? baseProfile.fullName,
      district: preferredDistrict ?? baseProfile.district,
      state: preferredState ?? baseProfile.state,
      emailVerified: baseProfile.emailVerified,
      phoneVerified: baseProfile.phoneVerified,
      accountActive: baseProfile.accountActive,
      status: baseProfile.status,
      preferredLanguage: baseProfile.preferredLanguage,
      createdAt: baseProfile.createdAt,
      updatedAt: baseProfile.updatedAt,
      aadhaarNumber: preferredAadhaar ?? baseProfile.aadhaarNumber,
      smartRationCard: preferredRationCard ?? baseProfile.smartRationCard,
      gender: preferredGender ?? baseProfile.gender,
      dateOfBirth: preferredDateOfBirth ?? baseProfile.dateOfBirth,
      addressLine1: preferredAddressLine1 ?? baseProfile.addressLine1,
      addressLine2: preferredAddressLine2 ?? baseProfile.addressLine2,
      village: preferredVillage ?? baseProfile.village,
      taluk: preferredTaluk ?? baseProfile.taluk,
      pincode: preferredPincode ?? baseProfile.pincode,
      profilePhotoUrl: preferredPhotoUrl ?? baseProfile.profilePhotoUrl,
      lastLogin: baseProfile.lastLogin,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'phone': phone,
      'full_name': fullName,
      'district': district,
      'state': state,
      'email_verified': emailVerified,
      'phone_verified': phoneVerified,
      'account_active': accountActive,
      'status': status,
      'preferred_language': preferredLanguage,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      if (aadhaarNumber != null) 'aadhaar_number': aadhaarNumber,
      if (smartRationCard != null) 'smart_ration_card': smartRationCard,
      if (gender != null) 'gender': gender,
      if (dateOfBirth != null) 'date_of_birth': dateOfBirth!.toIso8601String(),
      if (addressLine1 != null) 'address_line1': addressLine1,
      if (addressLine2 != null) 'address_line2': addressLine2,
      if (village != null) 'village': village,
      if (taluk != null) 'taluk': taluk,
      if (pincode != null) 'pincode': pincode,
      if (profilePhotoUrl != null) 'profile_photo_url': profilePhotoUrl,
      if (lastLogin != null) 'last_login': lastLogin!.toIso8601String(),
    };
  }
}
