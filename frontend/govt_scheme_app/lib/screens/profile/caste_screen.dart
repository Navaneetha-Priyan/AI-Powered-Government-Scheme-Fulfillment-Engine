import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../providers/citizen_provider.dart';

class CasteScreen extends StatefulWidget {
  const CasteScreen({super.key});

  @override
  State<CasteScreen> createState() => _CasteScreenState();
}

class _CasteScreenState extends State<CasteScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<CitizenProvider>();
    if (provider.caste == null) {
      try {
        await provider.loadCaste();
      } catch (_) {}
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<CitizenProvider>(
      builder: (context, provider, _) {
        final caste = provider.caste;
        return Scaffold(
          appBar: AppBar(title: const Text('Community Details')),
          body: provider.isLoading && caste == null
              ? const AppLoadingView(message: 'Loading your community details...')
              : caste == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => provider.loadCaste(),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        InfoCard(
                          label: 'Community',
                          value: AppFormatters.titleCase(caste.community),
                          icon: Icons.groups_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Category',
                          value: AppFormatters.titleCase(caste.category),
                          icon: Icons.category_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Caste',
                          value: AppFormatters.titleCase(caste.caste),
                          icon: Icons.diversity_3_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Religion',
                          value: AppFormatters.titleCase(caste.religion),
                          icon: Icons.account_balance_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Community Certificate',
                          value: caste.communityCertificate?.documentName ?? 'Not available',
                          icon: Icons.description_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Certificate Status',
                          value: AppFormatters.titleCase(
                            caste.communityCertificate?.verificationStatus,
                          ),
                          icon: Icons.verified_outlined,
                        ),
                      ],
                    ),
        );
      },
    );
  }
}
