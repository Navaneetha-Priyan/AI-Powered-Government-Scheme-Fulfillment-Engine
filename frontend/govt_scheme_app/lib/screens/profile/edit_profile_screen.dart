import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/formatters.dart';
import '../../core/utils/validators.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_fields.dart';
import '../../providers/auth_provider.dart';
import '../../providers/profile_provider.dart';
import '../../routes/app_routes.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key, this.returnToDashboardAfterSave = false});

  final bool returnToDashboardAfterSave;

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _fullNameController;
  late final TextEditingController _phoneController;
  late final TextEditingController _addressLine1Controller;
  late final TextEditingController _addressLine2Controller;
  late final TextEditingController _villageController;
  late final TextEditingController _talukController;
  late final TextEditingController _districtController;
  late final TextEditingController _stateController;
  late final TextEditingController _pincodeController;
  late final TextEditingController _preferredLanguageController;
  late final TextEditingController _profilePhotoUrlController;
  String? _gender;
  DateTime? _dateOfBirth;

  @override
  void initState() {
    super.initState();
    final profile = context.read<AuthProvider>().currentUser;
    _fullNameController = TextEditingController(text: profile?.fullName ?? '');
    _phoneController = TextEditingController(text: profile?.phone ?? '');
    _addressLine1Controller = TextEditingController(text: profile?.addressLine1 ?? '');
    _addressLine2Controller = TextEditingController(text: profile?.addressLine2 ?? '');
    _villageController = TextEditingController(text: profile?.village ?? '');
    _talukController = TextEditingController(text: profile?.taluk ?? '');
    _districtController = TextEditingController(text: profile?.district ?? '');
    _stateController = TextEditingController(text: profile?.state ?? '');
    _pincodeController = TextEditingController(text: profile?.pincode ?? '');
    _preferredLanguageController = TextEditingController(text: profile?.preferredLanguage ?? 'en');
    _profilePhotoUrlController = TextEditingController(text: profile?.profilePhotoUrl ?? '');
    _gender = profile?.gender;
    _dateOfBirth = profile?.dateOfBirth;
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _phoneController.dispose();
    _addressLine1Controller.dispose();
    _addressLine2Controller.dispose();
    _villageController.dispose();
    _talukController.dispose();
    _districtController.dispose();
    _stateController.dispose();
    _pincodeController.dispose();
    _preferredLanguageController.dispose();
    _profilePhotoUrlController.dispose();
    super.dispose();
  }

  Future<void> _pickDateOfBirth() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _dateOfBirth ?? DateTime(1995, 1, 1),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
    );

    if (selected != null) {
      setState(() => _dateOfBirth = selected);
    }
  }

  Future<void> _save() async {
    final profileProvider = context.read<ProfileProvider>();
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    final payload = <String, dynamic>{
      'full_name': _fullNameController.text.trim(),
      'phone': _phoneController.text.trim(),
      'gender': _gender,
      'date_of_birth': _dateOfBirth?.toIso8601String(),
      'address_line1': _addressLine1Controller.text.trim(),
      'address_line2': _addressLine2Controller.text.trim(),
      'village': _villageController.text.trim(),
      'taluk': _talukController.text.trim(),
      'district': _districtController.text.trim(),
      'state': _stateController.text.trim(),
      'pincode': _pincodeController.text.trim(),
      'preferred_language': _preferredLanguageController.text.trim(),
      'profile_photo_url': _profilePhotoUrlController.text.trim(),
    };

    payload.removeWhere((key, value) => value == null || value.toString().trim().isEmpty);

    try {
      await profileProvider.updateProfile(payload);
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile updated successfully')),
      );

      if (widget.returnToDashboardAfterSave) {
        Navigator.of(context).pushNamedAndRemoveUntil(AppRoutes.home, (route) => false);
      } else {
        Navigator.of(context).pop();
      }
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Edit Profile')),
      body: Consumer<ProfileProvider>(
        builder: (context, profileProvider, _) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 860),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text('Update your profile', style: Theme.of(context).textTheme.headlineMedium),
                          const SizedBox(height: 20),
                          AppTextField(
                            controller: _fullNameController,
                            label: 'Full Name',
                            validator: Validators.fullName,
                            prefixIcon: Icons.person_outline,
                          ),
                          const SizedBox(height: 16),
                          AppTextField(
                            controller: _phoneController,
                            label: 'Phone',
                            validator: Validators.phone,
                            keyboardType: TextInputType.phone,
                            prefixIcon: Icons.phone_outlined,
                          ),
                          const SizedBox(height: 16),
                          DropdownButtonFormField<String>(
                            initialValue: _gender,
                            items: const [
                              DropdownMenuItem(value: 'male', child: Text('Male')),
                              DropdownMenuItem(value: 'female', child: Text('Female')),
                              DropdownMenuItem(value: 'other', child: Text('Other')),
                              DropdownMenuItem(value: 'prefer_not_to_say', child: Text('Prefer not to say')),
                            ],
                            onChanged: (value) => setState(() => _gender = value),
                            decoration: const InputDecoration(labelText: 'Gender'),
                          ),
                          const SizedBox(height: 16),
                          AppTextField(
                            controller: TextEditingController(text: AppFormatters.displayDate(_dateOfBirth)),
                            label: 'Date of Birth',
                            readOnly: true,
                            onTap: _pickDateOfBirth,
                            prefixIcon: Icons.cake_rounded,
                            suffixIcon: Icons.calendar_month_rounded,
                            onSuffixTap: _pickDateOfBirth,
                          ),
                          const SizedBox(height: 16),
                          AppTextField(controller: _addressLine1Controller, label: 'Address Line 1'),
                          const SizedBox(height: 16),
                          AppTextField(controller: _addressLine2Controller, label: 'Address Line 2'),
                          const SizedBox(height: 16),
                          AppTextField(controller: _villageController, label: 'Village'),
                          const SizedBox(height: 16),
                          AppTextField(controller: _talukController, label: 'Taluk'),
                          const SizedBox(height: 16),
                          AppTextField(
                            controller: _districtController,
                            label: 'District',
                            validator: (value) => Validators.requiredField(value, label: 'District'),
                          ),
                          const SizedBox(height: 16),
                          AppTextField(
                            controller: _stateController,
                            label: 'State',
                            validator: (value) => Validators.requiredField(value, label: 'State'),
                          ),
                          const SizedBox(height: 16),
                          AppTextField(
                            controller: _pincodeController,
                            label: 'Pincode',
                            keyboardType: TextInputType.number,
                            validator: Validators.pincode,
                          ),
                          const SizedBox(height: 16),
                          AppTextField(controller: _preferredLanguageController, label: 'Preferred Language'),
                          const SizedBox(height: 16),
                          AppTextField(controller: _profilePhotoUrlController, label: 'Profile Photo URL'),
                          const SizedBox(height: 24),
                          PrimaryButton(
                            label: 'Save Changes',
                            onPressed: _save,
                            isLoading: profileProvider.isLoading,
                            icon: Icons.save_rounded,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
