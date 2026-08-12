class AuthTokens {
  AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
  });

  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token'].toString(),
      refreshToken: json['refresh_token'].toString(),
      tokenType: json['token_type']?.toString() ?? 'bearer',
      expiresIn: int.tryParse(json['expires_in'].toString()) ?? 0,
    );
  }
}

class LoginRequest {
  LoginRequest({required this.email, required this.password});

  final String email;
  final String password;

  Map<String, dynamic> toJson() => {'email': email, 'password': password};
}

class RegisterRequest {
  RegisterRequest({
    required this.fullName,
    required this.email,
    required this.phone,
    required this.password,
    required this.confirmPassword,
    required this.district,
    required this.state,
    this.aadhaarNumber,
    this.rationCardNumber,
    this.gender,
    this.dateOfBirth,
    this.addressLine1,
    this.addressLine2,
    this.village,
    this.taluk,
    this.pincode,
    this.preferredLanguage,
  });

  final String fullName;
  final String email;
  final String phone;
  final String password;
  final String confirmPassword;
  final String district;
  final String state;
  final String? aadhaarNumber;
  final String? rationCardNumber;
  final String? gender;
  final DateTime? dateOfBirth;
  final String? addressLine1;
  final String? addressLine2;
  final String? village;
  final String? taluk;
  final String? pincode;
  final String? preferredLanguage;

  Map<String, dynamic> toJson() {
    return {
      'full_name': fullName,
      'email': email,
      'phone': phone,
      'password': password,
      'confirm_password': confirmPassword,
      'district': district,
      'state': state,
      if (aadhaarNumber != null && aadhaarNumber!.isNotEmpty)
        'aadhaar_number': aadhaarNumber,
      if (rationCardNumber != null && rationCardNumber!.isNotEmpty)
        'smart_ration_card': rationCardNumber,
      if (gender != null && gender!.isNotEmpty) 'gender': gender,
      if (dateOfBirth != null) 'date_of_birth': dateOfBirth!.toIso8601String(),
      if (addressLine1 != null && addressLine1!.isNotEmpty)
        'address_line1': addressLine1,
      if (addressLine2 != null && addressLine2!.isNotEmpty)
        'address_line2': addressLine2,
      if (village != null && village!.isNotEmpty) 'village': village,
      if (taluk != null && taluk!.isNotEmpty) 'taluk': taluk,
      if (pincode != null && pincode!.isNotEmpty) 'pincode': pincode,
      if (preferredLanguage != null && preferredLanguage!.isNotEmpty)
        'preferred_language': preferredLanguage,
    };
  }
}

class RefreshTokenRequest {
  RefreshTokenRequest(this.refreshToken);

  final String refreshToken;

  Map<String, dynamic> toJson() => {'refresh_token': refreshToken};
}

class ChangePasswordRequest {
  ChangePasswordRequest({
    required this.oldPassword,
    required this.newPassword,
    required this.confirmPassword,
  });

  final String oldPassword;
  final String newPassword;
  final String confirmPassword;

  Map<String, dynamic> toJson() {
    return {
      'old_password': oldPassword,
      'new_password': newPassword,
      'confirm_password': confirmPassword,
    };
  }
}
