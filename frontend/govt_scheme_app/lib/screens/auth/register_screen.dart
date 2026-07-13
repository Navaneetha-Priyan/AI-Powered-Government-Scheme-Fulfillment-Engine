import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/validators.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_fields.dart';
import '../../models/auth_models.dart';
import '../../providers/india_location_provider.dart';
import '../../providers/auth_provider.dart';
import '../../routes/app_routes.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  static const String routeName = AppRoutes.register;

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();

  final _fullNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  TextEditingController? _stateController;
  TextEditingController? _districtController;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  String? _selectedState;
  String? _selectedDistrict;

  @override
  void dispose() {
    _fullNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  List<String> _rankedMatches(List<String> options, String query) {
    if (query.trim().isEmpty) {
      return options;
    }

    final normalizedQuery = query.trim().toLowerCase();
    final prefixMatches = <String>[];
    final containsMatches = <String>[];

    for (final option in options) {
      final normalizedOption = option.toLowerCase();
      if (normalizedOption.startsWith(normalizedQuery)) {
        prefixMatches.add(option);
      } else if (normalizedOption.contains(normalizedQuery)) {
        containsMatches.add(option);
      }
    }

    return [...prefixMatches, ...containsMatches];
  }

  String? _matchedOption(List<String> options, String value) {
    final normalizedValue = value.trim().toLowerCase();
    if (normalizedValue.isEmpty) {
      return null;
    }

    for (final option in options) {
      if (option.toLowerCase() == normalizedValue) {
        return option;
      }
    }

    return null;
  }

  String? _currentStateName(List<String> states) {
    final typedState = _stateController?.text.trim() ?? '';
    final exactMatch = _matchedOption(states, typedState);
    if (exactMatch != null) {
      return exactMatch;
    }

    if (_selectedState != null && states.any((state) => state == _selectedState)) {
      return _selectedState;
    }

    return null;
  }

  Widget _buildAutocompleteField({
    required String label,
    required String helperText,
    required IconData prefixIcon,
    required bool enabled,
    required Iterable<String> Function(String query) optionsBuilder,
    required void Function(String value) onSelected,
    required String? Function(String value) validator,
    required void Function(TextEditingController controller) onControllerReady,
    required void Function(String value) onChanged,
  }) {
    return Autocomplete<String>(
      displayStringForOption: (option) => option,
      optionsBuilder: (textEditingValue) {
        if (!enabled) {
          return const Iterable<String>.empty();
        }

        return optionsBuilder(textEditingValue.text);
      },
      onSelected: onSelected,
      fieldViewBuilder: (context, textEditingController, focusNode, onFieldSubmitted) {
        onControllerReady(textEditingController);

        return TextFormField(
          controller: textEditingController,
          focusNode: focusNode,
          enabled: enabled,
          decoration: InputDecoration(
            labelText: label,
            helperText: helperText,
            prefixIcon: Icon(prefixIcon),
          ),
          validator: (value) => validator(value ?? ''),
          onChanged: onChanged,
          onFieldSubmitted: (_) => onFieldSubmitted(),
        );
      },
      optionsViewBuilder: (context, onSelectedOption, options) {
        return Align(
          alignment: Alignment.topLeft,
          child: Material(
            elevation: 4,
            borderRadius: BorderRadius.circular(12),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 240, maxWidth: 560),
              child: ListView.builder(
                padding: EdgeInsets.zero,
                shrinkWrap: true,
                itemCount: options.length,
                itemBuilder: (context, index) {
                  final option = options.elementAt(index);
                  return ListTile(
                    dense: true,
                    title: Text(option),
                    onTap: () => onSelectedOption(option),
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<IndiaLocationProvider>().loadLocations();
      }
    });
  }

  Future<void> _submit() async {
    final authProvider = context.read<AuthProvider>();
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    try {
      final stateValue = _stateController?.text.trim() ?? _selectedState?.trim() ?? '';
      final districtValue = _districtController?.text.trim() ?? _selectedDistrict?.trim() ?? '';

      await authProvider.register(
        RegisterRequest(
          fullName: _fullNameController.text.trim(),
          email: _emailController.text.trim(),
          phone: _phoneController.text.trim(),
          password: _passwordController.text,
          confirmPassword: _confirmPasswordController.text,
          district: districtValue,
          state: stateValue,
        ),
      );

      if (!mounted) {
        return;
      }

      final completeProfileNow = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (context) {
          return AlertDialog(
            title: const Text('Complete your profile now?'),
            content: const Text(
              'You can fill the rest of your details now or go straight to the dashboard and finish later.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Go to dashboard'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Complete profile now'),
              ),
            ],
          );
        },
      );

      if (!mounted) {
        return;
      }

      if (completeProfileNow == true) {
        Navigator.of(context).pushNamedAndRemoveUntil(
          AppRoutes.editProfile,
          (route) => false,
          arguments: true,
        );
        return;
      }

      Navigator.of(context).pushNamedAndRemoveUntil(AppRoutes.home, (route) => false);
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    }
  }

  Widget _basicSection(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AppTextField(
              controller: _fullNameController,
              label: 'Full name',
              helperText: 'Write your name as it appears on your documents.',
              validator: Validators.fullName,
              prefixIcon: Icons.person_outline,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),
            AppTextField(
              controller: _phoneController,
              label: 'Mobile number',
              helperText: 'We will send updates to this phone number.',
              keyboardType: TextInputType.phone,
              validator: Validators.phone,
              prefixIcon: Icons.phone_outlined,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),
            AppTextField(
              controller: _emailController,
              label: 'Email address',
              helperText: 'Use the email you want to sign in with.',
              keyboardType: TextInputType.emailAddress,
              validator: Validators.email,
              prefixIcon: Icons.email_outlined,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),
            AppTextField(
              controller: _passwordController,
              label: 'Password',
              helperText: 'Use a password you can remember safely.',
              validator: Validators.password,
              obscureText: _obscurePassword,
              keyboardType: TextInputType.visiblePassword,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.newPassword],
              prefixIcon: Icons.lock_outline,
              suffixIcon: _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
              onSuffixTap: () => setState(() => _obscurePassword = !_obscurePassword),
            ),
            const SizedBox(height: 16),
            AppTextField(
              controller: _confirmPasswordController,
              label: 'Confirm password',
              validator: (value) => Validators.confirmPassword(value, _passwordController.text),
              obscureText: _obscureConfirmPassword,
              keyboardType: TextInputType.visiblePassword,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.newPassword],
              prefixIcon: Icons.lock_reset_rounded,
              suffixIcon: _obscureConfirmPassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
              onSuffixTap: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
            ),
            const SizedBox(height: 16),
            Consumer<IndiaLocationProvider>(
              builder: (context, locationProvider, _) {
                final states = locationProvider.states;
                final resolvedState = _currentStateName(states);
                final districts = resolvedState == null ? const <String>[] : locationProvider.districtsFor(resolvedState);

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildAutocompleteField(
                      label: 'State',
                      helperText: 'Type a few letters to see matching states first.',
                      prefixIcon: Icons.map_outlined,
                      enabled: states.isNotEmpty,
                      optionsBuilder: (query) => _rankedMatches(states, query),
                      onControllerReady: (controller) {
                        _stateController = controller;
                      },
                      onSelected: (value) {
                        setState(() {
                          _selectedState = value;
                          _selectedDistrict = null;
                          _districtController?.clear();
                        });
                      },
                      onChanged: (value) {
                        final exactState = _matchedOption(states, value);

                        setState(() {
                          _selectedState = exactState;
                          _selectedDistrict = null;
                          if (_districtController != null) {
                            _districtController!.clear();
                          }
                        });
                      },
                      validator: (value) {
                        if (value.trim().isEmpty) {
                          return 'State is required';
                        }

                        return _matchedOption(states, value) == null ? 'Pick a valid state from the list' : null;
                      },
                    ),
                    const SizedBox(height: 16),
                    _buildAutocompleteField(
                      label: 'District',
                      helperText: resolvedState == null
                          ? 'Select a valid state first.'
                          : 'Type a few letters to see matching districts first.',
                      prefixIcon: Icons.location_city_outlined,
                      enabled: resolvedState != null && districts.isNotEmpty,
                      optionsBuilder: (query) => _rankedMatches(districts, query),
                      onControllerReady: (controller) {
                        _districtController = controller;
                      },
                      onSelected: (value) {
                        setState(() => _selectedDistrict = value);
                      },
                      onChanged: (value) {
                        final exactDistrict = _matchedOption(districts, value);
                        setState(() => _selectedDistrict = exactDistrict);
                      },
                      validator: (value) {
                        if (value.trim().isEmpty) {
                          return 'District is required';
                        }

                        return _matchedOption(districts, value) == null ? 'Pick a valid district from the list' : null;
                      },
                    ),
                    if (locationProvider.isLoading) ...[
                      const SizedBox(height: 12),
                      const LinearProgressIndicator(),
                    ],
                    if (locationProvider.errorMessage != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        'Using offline location list because the server list could not be loaded.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Create your citizen account', style: Theme.of(context).textTheme.headlineMedium),
                          const SizedBox(height: 8),
                          Text(
                            'Start with the basic details. You can add the rest later if you want.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 24),
                          Form(
                            key: _formKey,
                            child: _basicSection(context),
                          ),
                          const SizedBox(height: 16),
                          Consumer<IndiaLocationProvider>(
                            builder: (context, locationProvider, _) {
                              if (locationProvider.states.isEmpty) {
                                return const SizedBox.shrink();
                              }

                              return Text(
                                'Select your state and district from the official list.',
                                style: Theme.of(context).textTheme.bodySmall,
                              );
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Consumer<AuthProvider>(
                    builder: (context, authProvider, _) {
                      return PrimaryButton(
                        label: 'Create account',
                        onPressed: _submit,
                        isLoading: authProvider.isBusy,
                        icon: Icons.verified_user_rounded,
                      );
                    },
                  ),
                  const SizedBox(height: 12),
                  SecondaryButton(
                    label: 'Already have an account? Sign in',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: Icons.login_rounded,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
