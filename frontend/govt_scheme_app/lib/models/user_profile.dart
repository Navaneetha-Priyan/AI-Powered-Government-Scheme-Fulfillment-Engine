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
