import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/validators.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_fields.dart';
import '../../models/auth_models.dart';
import '../../providers/auth_provider.dart';
import '../../routes/app_routes.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  static const String routeName = AppRoutes.login;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final authProvider = context.read<AuthProvider>();
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    authProvider.clearError();

    try {
      await authProvider.login(
        LoginRequest(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        ),
      );

      if (!mounted) {
        return;
      }

      Navigator.of(
        context,
      ).pushNamedAndRemoveUntil(AppRoutes.home, (route) => false);
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppStrings.friendlyError(error))));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFF4F7FB), Color(0xFFEAF3FF)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 460),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Container(
                              height: 60,
                              width: 60,
                              decoration: BoxDecoration(
                                color: Theme.of(
                                  context,
                                ).colorScheme.primary.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(18),
                              ),
                              child: Icon(
                                Icons.login_rounded,
                                color: Theme.of(context).colorScheme.primary,
                                size: 32,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    AppStrings.signIn,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.headlineMedium,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Enter your email and password.',
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodyMedium,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 20),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Theme.of(
                              context,
                            ).colorScheme.primary.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                              color: Theme.of(
                                context,
                              ).colorScheme.primary.withValues(alpha: 0.12),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'How to sign in',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 10),
                              const _StepLine(
                                number: '1',
                                text: 'Type your email address.',
                              ),
                              const SizedBox(height: 8),
                              const _StepLine(
                                number: '2',
                                text: 'Enter your password.',
                              ),
                              const SizedBox(height: 8),
                              const _StepLine(
                                number: '3',
                                text: 'Tap Sign In.',
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),
                        Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              AppTextField(
                                controller: _emailController,
                                label: 'Email address',
                                hintText: 'example@email.com',
                                helperText:
                                    'Use the email you used during registration.',
                                validator: Validators.email,
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.next,
                                autofillHints: const [
                                  AutofillHints.username,
                                  AutofillHints.email,
                                ],
                                prefixIcon: Icons.email_outlined,
                              ),
                              const SizedBox(height: 16),
                              AppTextField(
                                controller: _passwordController,
                                label: 'Password',
                                helperText:
                                    'Type your password exactly as saved.',
                                validator: Validators.requiredField,
                                obscureText: _obscurePassword,
                                keyboardType: TextInputType.visiblePassword,
                                textInputAction: TextInputAction.done,
                                autofillHints: const [AutofillHints.password],
                                prefixIcon: Icons.lock_outline,
                                suffixIcon: _obscurePassword
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                onSuffixTap: () => setState(
                                  () => _obscurePassword = !_obscurePassword,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),
                        Consumer<AuthProvider>(
                          builder: (context, authProvider, _) {
                            return PrimaryButton(
                              label: AppStrings.signIn,
                              onPressed: _submit,
                              isLoading: authProvider.isBusy,
                              icon: Icons.login_rounded,
                            );
                          },
                        ),
                        const SizedBox(height: 14),
                        SecondaryButton(
                          label: 'Create a new account',
                          onPressed: () => Navigator.of(
                            context,
                          ).pushNamed(AppRoutes.register),
                          icon: Icons.person_add_alt_rounded,
                        ),
                        TextButton(
                          onPressed: () => Navigator.of(
                            context,
                          ).pushNamed(AppRoutes.forgotPassword),
                          child: const Text('Need help with password?'),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'If you are stuck, ask the operator at the service center to help you sign in.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
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

class _StepLine extends StatelessWidget {
  const _StepLine({required this.number, required this.text});

  final String number;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          height: 28,
          width: 28,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primary,
            shape: BoxShape.circle,
          ),
          child: Text(
            number,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ),
      ],
    );
  }
}
