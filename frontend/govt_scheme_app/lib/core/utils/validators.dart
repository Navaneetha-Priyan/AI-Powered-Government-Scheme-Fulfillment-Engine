class Validators {
  Validators._();

  static String? requiredField(String? value, {String label = 'This field'}) {
    if (value == null || value.trim().isEmpty) {
      return '$label is required';
    }
    return null;
  }

  static String? fullName(String? value) {
    final required = requiredField(value, label: 'Full name');
    if (required != null) {
      return required;
    }

    if (value!.trim().length < 2) {
      return 'Full name must be at least 2 characters';
    }

    if (!RegExp(r'^[a-zA-Z\s\.]+$').hasMatch(value.trim())) {
      return 'Full name can only contain letters, spaces and dots';
    }

    return null;
  }

  static String? email(String? value) {
    final required = requiredField(value, label: 'Email');
    if (required != null) {
      return required;
    }

    if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(value!.trim())) {
      return 'Enter a valid email address';
    }

    return null;
  }

  static String? phone(String? value) {
    final required = requiredField(value, label: 'Phone');
    if (required != null) {
      return required;
    }

    final digits = value!.replaceAll(RegExp(r'[\s\-\(\)]'), '');
    if (!RegExp(r'^[6-9]\d{9}$').hasMatch(digits)) {
      return 'Enter a valid 10-digit Indian mobile number';
    }

    return null;
  }

  static String? password(String? value) {
    final required = requiredField(value, label: 'Password');
    if (required != null) {
      return required;
    }

    final password = value!;
    if (password.length < 8) {
      return 'Password must be at least 8 characters';
    }

    if (!RegExp(r'[A-Z]').hasMatch(password) ||
        !RegExp(r'[a-z]').hasMatch(password) ||
        !RegExp(r'\d').hasMatch(password) ||
        !RegExp(r'[!@#\$%\^&*(),.?":{}|<>]').hasMatch(password)) {
      return 'Use uppercase, lowercase, number and special character';
    }

    return null;
  }

  static String? confirmPassword(String? value, String? password) {
    final required = requiredField(value, label: 'Confirm password');
    if (required != null) {
      return required;
    }

    if (value != password) {
      return 'Passwords do not match';
    }

    return null;
  }

  static String? pincode(String? value) {
    if (value == null || value.trim().isEmpty) {
      return null;
    }

    if (!RegExp(r'^\d{6}$').hasMatch(value.trim())) {
      return 'Enter a valid 6-digit pincode';
    }

    return null;
  }
}
