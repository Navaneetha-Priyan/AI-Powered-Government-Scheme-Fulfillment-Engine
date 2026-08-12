import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

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
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadAll());
  }

  Future<void> _loadAll() async {
    final profileProvider = context.read<ProfileProvider>();
    final citizenProvider = context.read<CitizenProvider>();

    // Parallel fetch — only load what is missing
    await Future.wait([
      if (profileProvider.profile == null)
        profileProvider.loadProfile().catchError((_) {}),
      if (citizenProvider.profileDetails == null)
        citizenProvider.loadProfileDetails().catchError((_) {}),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer3<AuthProvider, ProfileProvider, CitizenProvider>(
      builder: (context, authProvider, profileProvider, citizenProvider, _) {
        final baseProfile = profileProvider.profile ?? authProvider.currentUser;
        final profile = baseProfile != null &&
                citizenProvider.profileDetails != null
            ? UserProfile.fromCitizenProfileDetails(
                baseProfile: baseProfile,
                citizenProfileDetails: Map<String, dynamic>.from(
                  citizenProvider.profileDetails!,
                ),
              )
            : baseProfile;

        final extendedProfile = citizenProvider.extendedProfile;
        final isLoading = (profileProvider.isLoading && baseProfile == null) ||
            (citizenProvider.isLoading &&
                citizenProvider.profileDetails == null);

        return Scaffold(
          appBar: AppBar(
            title: const Text('My Profile'),
            automaticallyImplyLeading: widget.showBackButton,
          ),
          body: isLoading
              ? const AppLoadingView(message: 'Loading your profile...')
              : profile == null
                  ? AppErrorView(
                      message: profileProvider.errorMessage ??
                          'Could not load your profile.',
                      onRetry: _loadAll,
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(20),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 760),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _IdentityCard(profile: profile),
                              const SizedBox(height: 16),
                              _DocumentDrivenCard(context: context),
                              const SizedBox(height: 16),
                              _PersonalInfoCard(profile: profile),
                              if (extendedProfile != null) ...[
                                const SizedBox(height: 16),
                                _ExtendedProfileCard(
                                    extendedProfile: extendedProfile),
                              ],
                              const SizedBox(height: 16),
                              _AccountStatusCard(profile: profile),
                              const SizedBox(height: 24),
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

// ─── Identity card ─────────────────────────────────────────────────────────────

class _IdentityCard extends StatelessWidget {
  const _IdentityCard({required this.profile});
  final UserProfile profile;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  height: 56,
                  width: 56,
                  decoration: BoxDecoration(
                    color: cs.primary.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.person_rounded, color: cs.primary, size: 30),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(profile.fullName,
                          style: Theme.of(context).textTheme.headlineSmall),
                      Text(profile.email,
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Text(
              'Last sign in: ${AppFormatters.displayDateTime(profile.lastLogin)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: PrimaryButton(
                    label: 'Edit Profile',
                    onPressed: () =>
                        Navigator.of(context).pushNamed(AppRoutes.editProfile),
                    icon: Icons.edit_rounded,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: SecondaryButton(
                    label: 'Change Password',
                    onPressed: () => Navigator.of(context)
                        .pushNamed(AppRoutes.changePassword),
                    icon: Icons.lock_outline,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Document-driven card ──────────────────────────────────────────────────────

class _DocumentDrivenCard extends StatelessWidget {
  const _DocumentDrivenCard({required this.context});
  final BuildContext context;

  @override
  Widget build(BuildContext ctx) {
    final cs = Theme.of(ctx).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.auto_awesome_rounded, color: cs.primary, size: 22),
                const SizedBox(width: 8),
                Text('Document-Driven Profile',
                    style: Theme.of(ctx).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Your income, community, land, and eligibility details are automatically extracted from your uploaded documents.',
            ),
            const SizedBox(height: 14),
            SecondaryButton(
              label: 'Manage Documents',
              icon: Icons.folder_copy_outlined,
              onPressed: () =>
                  Navigator.of(ctx).pushNamed(AppRoutes.documents),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Personal info card ────────────────────────────────────────────────────────

class _PersonalInfoCard extends StatelessWidget {
  const _PersonalInfoCard({required this.profile});
  final UserProfile profile;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Personal Information',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 14),
            InfoCard(
              label: 'Phone',
              value: profile.phone,
              icon: Icons.phone_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Gender',
              value: AppFormatters.displayValue(profile.gender),
              icon: Icons.wc_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Date of Birth',
              value: AppFormatters.displayDate(profile.dateOfBirth),
              icon: Icons.cake_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'District',
              value: profile.district,
              icon: Icons.location_city_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'State',
              value: profile.state,
              icon: Icons.flag_outlined,
            ),
            if (profile.village != null) ...[
              const SizedBox(height: 10),
              InfoCard(
                label: 'Village',
                value: AppFormatters.displayValue(profile.village),
                icon: Icons.map_outlined,
              ),
            ],
            if (profile.pincode != null) ...[
              const SizedBox(height: 10),
              InfoCard(
                label: 'Pincode',
                value: AppFormatters.displayValue(profile.pincode),
                icon: Icons.local_post_office_outlined,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── Extended profile card ─────────────────────────────────────────────────────

class _ExtendedProfileCard extends StatelessWidget {
  const _ExtendedProfileCard({required this.extendedProfile});
  final dynamic extendedProfile;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Extracted from Documents',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 14),
            InfoCard(
              label: 'Father Name',
              value: AppFormatters.displayValue(extendedProfile.fatherName),
              icon: Icons.person_outline,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Mother Name',
              value: AppFormatters.displayValue(extendedProfile.motherName),
              icon: Icons.person_2_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Occupation',
              value: AppFormatters.titleCase(extendedProfile.occupation),
              icon: Icons.work_outline,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Education',
              value: AppFormatters.titleCase(extendedProfile.educationLevel),
              icon: Icons.school_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Annual Income',
              value: extendedProfile.annualIncome != null
                  ? AppFormatters.money(extendedProfile.annualIncome)
                  : 'Not available',
              icon: Icons.currency_rupee_rounded,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Community',
              value: AppFormatters.displayValue(extendedProfile.community),
              icon: Icons.groups_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Farmer',
              value: extendedProfile.isFarmer ? 'Yes' : 'No',
              icon: Icons.agriculture_outlined,
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Account status card ───────────────────────────────────────────────────────

class _AccountStatusCard extends StatelessWidget {
  const _AccountStatusCard({required this.profile});
  final UserProfile profile;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Account Status',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 14),
            InfoCard(
              label: 'Account',
              value: profile.accountActive ? 'Active' : 'Inactive',
              icon: Icons.verified_user_outlined,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Preferred Language',
              value: profile.preferredLanguage,
              icon: Icons.language_rounded,
            ),
            const SizedBox(height: 10),
            InfoCard(
              label: 'Member Since',
              value: AppFormatters.displayDate(profile.createdAt),
              icon: Icons.event_available_outlined,
            ),
          ],
        ),
      ),
    );
  }
}
