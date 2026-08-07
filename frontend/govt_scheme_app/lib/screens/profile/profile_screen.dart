import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../models/user_profile.dart';
import '../../providers/auth_provider.dart';
import '../../providers/citizen_provider.dart';
import '../../providers/profile_provider.dart';
import '../../routes/app_routes.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, this.showBackButton = true});

  final bool showBackButton;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final profileProvider = context.read<ProfileProvider>();
      final citizenProvider = context.read<CitizenProvider>();
      final futures = <Future<void>>[];

      if (profileProvider.profile == null) {
        futures.add(
          Future<void>(() async {
            try {
              await profileProvider.loadProfile();
            } catch (_) {
              // handled by provider state
            }
          }),
        );
      }

      if (citizenProvider.profileDetails == null) {
        futures.add(
          Future<void>(() async {
            try {
              await citizenProvider.loadProfileDetails();
            } catch (_) {
              // handled by provider state
            }
          }),
        );
      }

      if (futures.isNotEmpty) {
        await Future.wait(futures);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer3<AuthProvider, ProfileProvider, CitizenProvider>(
      builder: (context, authProvider, profileProvider, citizenProvider, _) {
        final baseProfile = profileProvider.profile ?? authProvider.currentUser;
        final mergedProfile = baseProfile != null && citizenProvider.profileDetails != null
            ? UserProfile.fromCitizenProfileDetails(
                baseProfile: baseProfile,
                citizenProfileDetails: Map<String, dynamic>.from(
                  citizenProvider.profileDetails!,
                ),
              )
            : baseProfile;
        final profile = mergedProfile;
        final extendedProfile = citizenProvider.extendedProfile;
        final isProfileLoading = (profileProvider.isLoading && baseProfile == null) ||
            (citizenProvider.isLoading && citizenProvider.profileDetails == null);

        return Scaffold(
          appBar: AppBar(
            title: const Text(AppStrings.myProfile),
            automaticallyImplyLeading: widget.showBackButton,
          ),
          body: isProfileLoading
              ? AppLoadingView(
                  message: baseProfile == null
                      ? 'Loading your profile...'
                      : 'Loading your profile details...',
                )
              : profile == null
                  ? AppErrorView(
                      message: profileProvider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => profileProvider.loadProfile(),
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(20),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 980),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(24),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(profile.fullName, style: Theme.of(context).textTheme.headlineMedium),
                                      const SizedBox(height: 8),
                                      Text(profile.email),
                                      const SizedBox(height: 12),
                                      Text('Last sign in: ${AppFormatters.displayDateTime(profile.lastLogin)}'),
                                      const SizedBox(height: 20),
                                      Wrap(
                                        spacing: 12,
                                        runSpacing: 12,
                                        children: [
                                          PrimaryButton(
                                            label: 'Edit My Profile',
                                            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.editProfile),
                                            icon: Icons.edit_rounded,
                                          ),
                                          SecondaryButton(
                                            label: 'Change Password',
                                            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.changePassword),
                                            icon: Icons.lock_outline,
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(height: 20),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(20),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('More Details', style: Theme.of(context).textTheme.titleLarge),
                                      const SizedBox(height: 12),
                                      ProfileCard(
                                        title: 'Income Details',
                                        subtitle: 'Annual income, occupation, and farmer status',
                                        icon: Icons.payments_outlined,
                                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.income),
                                      ),
                                      const SizedBox(height: 12),
                                      ProfileCard(
                                        title: 'Community Details',
                                        subtitle: 'Community, caste, and certificate status',
                                        icon: Icons.diversity_3_outlined,
                                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.caste),
                                      ),
                                      const SizedBox(height: 12),
                                      ProfileCard(
                                        title: AppStrings.myLand,
                                        subtitle: 'Survey number, village, ownership, and area',
                                        icon: Icons.landscape_outlined,
                                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.landRecords),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(height: 20),
                              Wrap(
                                spacing: 16,
                                runSpacing: 16,
                                children: [
                                  _ProfileInfoSection(profile: profile),
                                ],
                              ),
                              if (extendedProfile != null) ...[
                                const SizedBox(height: 20),
                                Card(
                                  child: Padding(
                                    padding: const EdgeInsets.all(20),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Records from Government', style: Theme.of(context).textTheme.titleLarge),
                                        const SizedBox(height: 12),
                                        InfoCard(label: 'Father Name', value: AppFormatters.displayValue(extendedProfile.fatherName), icon: Icons.person_outline),
                                        const SizedBox(height: 12),
                                        InfoCard(label: 'Mother Name', value: AppFormatters.displayValue(extendedProfile.motherName), icon: Icons.person_2_outlined),
                                        const SizedBox(height: 12),
                                        InfoCard(label: 'Occupation', value: AppFormatters.titleCase(extendedProfile.occupation), icon: Icons.work_outline),
                                        const SizedBox(height: 12),
                                        InfoCard(label: 'Education', value: AppFormatters.titleCase(extendedProfile.educationLevel), icon: Icons.school_outlined),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                              const SizedBox(height: 20),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(20),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Account Status', style: Theme.of(context).textTheme.titleLarge),
                                      const SizedBox(height: 12),
                                      InfoCard(label: 'Email Checked', value: profile.emailVerified ? 'Yes' : 'No', icon: Icons.mark_email_read_outlined),
                                      const SizedBox(height: 12),
                                      InfoCard(label: 'Phone Checked', value: profile.phoneVerified ? 'Yes' : 'No', icon: Icons.phone_android_outlined),
                                      const SizedBox(height: 12),
                                      InfoCard(label: 'Account', value: profile.accountActive ? 'Active' : 'Inactive', icon: Icons.verified_user_outlined),
                                      const SizedBox(height: 12),
                                      InfoCard(label: 'Preferred language', value: profile.preferredLanguage, icon: Icons.language_rounded),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
        );
      },
    );
  }
}

class _ProfileInfoSection extends StatelessWidget {
  const _ProfileInfoSection({required this.profile});

  final UserProfile profile;

  @override
  Widget build(BuildContext context) {
    final items = <Widget>[
      InfoCard(label: 'Account Number', value: profile.id, icon: Icons.badge_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Phone', value: profile.phone, icon: Icons.phone_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Gender', value: AppFormatters.displayValue(profile.gender), icon: Icons.wc_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Date of Birth', value: AppFormatters.displayDate(profile.dateOfBirth), icon: Icons.cake_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Aadhaar', value: AppFormatters.displayValue(profile.aadhaarNumber), icon: Icons.credit_card_rounded),
      const SizedBox(height: 12),
      InfoCard(label: 'Ration Card', value: AppFormatters.displayValue(profile.smartRationCard), icon: Icons.receipt_long_rounded),
      const SizedBox(height: 12),
      InfoCard(label: 'Address Line 1', value: AppFormatters.displayValue(profile.addressLine1), icon: Icons.home_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Address Line 2', value: AppFormatters.displayValue(profile.addressLine2), icon: Icons.home_work_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Village', value: AppFormatters.displayValue(profile.village), icon: Icons.map_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Taluk', value: AppFormatters.displayValue(profile.taluk), icon: Icons.place_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'District', value: profile.district, icon: Icons.location_city_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'State', value: profile.state, icon: Icons.flag_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Pincode', value: AppFormatters.displayValue(profile.pincode), icon: Icons.local_post_office_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Created On', value: AppFormatters.displayDateTime(profile.createdAt), icon: Icons.event_available_outlined),
      const SizedBox(height: 12),
      InfoCard(label: 'Updated On', value: AppFormatters.displayDateTime(profile.updatedAt), icon: Icons.update_outlined),
    ];

    return Column(
      children: items,
    );
  }
}
