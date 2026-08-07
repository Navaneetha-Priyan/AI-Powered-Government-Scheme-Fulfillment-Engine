import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/models/user_profile.dart';

void main() {
  group('UserProfile profile merging', () {
    test('uses citizen profile details when available and falls back otherwise', () {
      final baseProfile = UserProfile(
        id: 'citizen-1',
        email: 'citizen@example.com',
        phone: '9999999999',
        fullName: 'Original Name',
        district: 'Old District',
        state: 'Old State',
        emailVerified: true,
        phoneVerified: true,
        accountActive: true,
        status: 'active',
        preferredLanguage: 'en',
        createdAt: DateTime(2024, 1, 1),
        updatedAt: DateTime(2024, 1, 2),
      );

      final mergedProfile = UserProfile.fromCitizenProfileDetails(
        baseProfile: baseProfile,
        citizenProfileDetails: {
          'full_name': 'Ravi Kumar',
          'phone': '9876543210',
          'district': 'Coimbatore',
          'state': 'Tamil Nadu',
          'address_line1': '5, Main Road',
          'pincode': '641001',
          'profile_photo_url': 'https://example.com/me.jpg',
          'extended_profile': {
            'father_name': 'Muthu',
            'profile_completion_percentage': 82,
          },
        },
      );

      expect(mergedProfile.fullName, 'Ravi Kumar');
      expect(mergedProfile.phone, '9876543210');
      expect(mergedProfile.district, 'Coimbatore');
      expect(mergedProfile.state, 'Tamil Nadu');
      expect(mergedProfile.addressLine1, '5, Main Road');
      expect(mergedProfile.pincode, '641001');
      expect(mergedProfile.profilePhotoUrl, 'https://example.com/me.jpg');
      expect(mergedProfile.email, 'citizen@example.com');
    });
  });
}
