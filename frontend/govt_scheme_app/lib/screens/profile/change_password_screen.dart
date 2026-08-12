import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/validators.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_fields.dart';
import '../../models/auth_models.dart';
import '../../providers/profile_provider.dart';

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _currentPasswordController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscureCurrent = true;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    final profileProvider = context.read<ProfileProvider>();

    try {
      await profileProvider.changePassword(
        ChangePasswordRequest(
          oldPassword: _currentPasswordController.text,
          newPassword: _newPasswordController.text,
          confirmPassword: _confirmPasswordController.text,
        ),
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password changed successfully')),
      );
      Navigator.of(context).pop();
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Change Password')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Update password',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 20),
                      AppTextField(
                        controller: _currentPasswordController,
                        label: 'Current Password',
                        validator: Validators.requiredField,
                        obscureText: _obscureCurrent,
                        prefixIcon: Icons.lock_outline,
                        suffixIcon: _obscureCurrent
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        onSuffixTap: () =>
                            setState(() => _obscureCurrent = !_obscureCurrent),
                      ),
                      const SizedBox(height: 16),
                      AppTextField(
                        controller: _newPasswordController,
                        label: 'New Password',
                        validator: Validators.password,
                        obscureText: _obscureNew,
                        prefixIcon: Icons.password_rounded,
                        suffixIcon: _obscureNew
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        onSuffixTap: () =>
                            setState(() => _obscureNew = !_obscureNew),
                      ),
                      const SizedBox(height: 16),
                      AppTextField(
                        controller: _confirmPasswordController,
                        label: 'Confirm New Password',
                        validator: (value) => Validators.confirmPassword(
                          value,
                          _newPasswordController.text,
                        ),
                        obscureText: _obscureConfirm,
                        prefixIcon: Icons.lock_reset_rounded,
                        suffixIcon: _obscureConfirm
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        onSuffixTap: () =>
                            setState(() => _obscureConfirm = !_obscureConfirm),
                      ),
                      const SizedBox(height: 24),
                      Consumer<ProfileProvider>(
                        builder: (context, profileProvider, _) {
                          return PrimaryButton(
                            label: 'Change Password',
                            onPressed: _submit,
                            isLoading: profileProvider.isLoading,
                            icon: Icons.lock_reset_rounded,
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
