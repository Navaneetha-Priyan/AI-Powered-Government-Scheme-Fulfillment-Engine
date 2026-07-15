import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../core/widgets/cards.dart';
import '../../providers/citizen_provider.dart';

class IncomeScreen extends StatefulWidget {
  const IncomeScreen({super.key});

  @override
  State<IncomeScreen> createState() => _IncomeScreenState();
}

class _IncomeScreenState extends State<IncomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<CitizenProvider>();
    if (provider.income == null) {
      try {
        await provider.loadIncome();
      } catch (_) {}
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<CitizenProvider>(
      builder: (context, provider, _) {
        final income = provider.income;
        return Scaffold(
          appBar: AppBar(title: const Text(AppStrings.incomeDetails)),
          body: provider.isLoading && income == null
              ? const AppLoadingView(message: 'Loading your income details...')
              : income == null
                  ? AppErrorView(
                      message: provider.errorMessage ?? AppStrings.somethingWrong,
                      onRetry: () => provider.loadIncome(),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        DashboardTile(
                          title: 'Annual Income',
                          value: AppFormatters.money(income.annualIncome),
                          subtitle: AppFormatters.titleCase(income.incomeCategory),
                          icon: Icons.account_balance_wallet_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Occupation',
                          value: AppFormatters.titleCase(income.occupation),
                          icon: Icons.work_outline,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Farmer Status',
                          value: income.isFarmer ? 'Farmer' : 'Not marked as farmer',
                          icon: Icons.agriculture_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Farmer Number',
                          value: AppFormatters.displayValue(income.farmerId),
                          icon: Icons.badge_outlined,
                        ),
                        const SizedBox(height: 12),
                        InfoCard(
                          label: 'Income Certificate',
                          value: income.incomeCertificate?.documentName ?? 'Not available',
                          icon: Icons.description_outlined,
                        ),
                      ],
                    ),
        );
      },
    );
  }
}
