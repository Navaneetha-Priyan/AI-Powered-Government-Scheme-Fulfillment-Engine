import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../models/eligibility.dart';
import '../../providers/eligibility_provider.dart';
import '../../providers/scheme_provider.dart';

class SchemeDetailScreen extends StatefulWidget {
  const SchemeDetailScreen({super.key, required this.schemeId});

  final String schemeId;

  @override
  State<SchemeDetailScreen> createState() => _SchemeDetailScreenState();
}

class _SchemeDetailScreenState extends State<SchemeDetailScreen> {
  int? _loadedEligibilityVersion;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    await Future.wait<void>([
      context.read<SchemeProvider>().loadSchemeDetail(widget.schemeId),
      _loadEligibility(),
    ]);
  }

  Future<void> _loadEligibility({bool refresh = false}) async {
    final provider = context.read<EligibilityProvider>();
    _loadedEligibilityVersion = provider.cacheVersion;
    await provider.loadEligibility(widget.schemeId, refresh: refresh);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<SchemeProvider, EligibilityProvider>(
      builder: (context, schemeProvider, eligibilityProvider, _) {
        if (_loadedEligibilityVersion != eligibilityProvider.cacheVersion &&
            !eligibilityProvider.isLoadingScheme(widget.schemeId)) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              _loadEligibility(refresh: true);
            }
          });
        }

        final selected = schemeProvider.schemeById(widget.schemeId);
        if (selected == null && schemeProvider.isLoading) {
          return const Scaffold(body: AppLoadingView(message: 'Loading scheme details...'));
        }

        if (selected == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Scheme Details')),
            body: AppErrorView(
              message: schemeProvider.errorMessage ?? AppStrings.somethingWrong,
              onRetry: _load,
            ),
          );
        }

        return Scaffold(
          appBar: AppBar(title: Text(selected.schemeName)),
          body: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              _InfoSection(title: 'Description', body: selected.description),
              _EligibilitySection(
                eligibility: eligibilityProvider.eligibilityFor(widget.schemeId),
                isLoading: eligibilityProvider.isLoadingScheme(widget.schemeId),
                errorMessage: eligibilityProvider.errorFor(widget.schemeId),
                onRefresh: () => _loadEligibility(refresh: true),
              ),
              _InfoSection(title: 'Eligibility criteria', body: selected.eligibilitySummary ?? 'Not specified'),
              _InfoSection(title: 'Required documents', body: selected.requiredDocuments ?? 'Not specified'),
              _InfoSection(title: 'Benefits', body: selected.benefits ?? 'Not specified'),
              _InfoSection(title: 'Application process', body: selected.applicationProcess ?? 'Not specified'),
              _InfoSection(title: 'Department', body: selected.department),
              _InfoSection(title: 'State', body: selected.state ?? 'All India'),
              _InfoSection(title: 'Last updated', body: AppFormatters.displayDateTime(selected.updatedAt ?? selected.createdAt)),
              _InfoSection(title: 'Contact information', body: selected.officialLink ?? 'Not available'),
            ],
          ),
        );
      },
    );
  }
}

class _EligibilitySection extends StatelessWidget {
  const _EligibilitySection({
    required this.eligibility,
    required this.isLoading,
    required this.errorMessage,
    required this.onRefresh,
  });

  final EligibilityCheck? eligibility;
  final bool isLoading;
  final String? errorMessage;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    if (isLoading && eligibility == null) {
      return const Card(
        margin: EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: EdgeInsets.all(16),
          child: AppLoadingView(message: 'Checking eligibility...'),
        ),
      );
    }

    if (eligibility == null && errorMessage != null) {
      return Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: AppErrorView(
            message: AppStrings.friendlyError(errorMessage!),
            onRetry: onRefresh,
          ),
        ),
      );
    }

    if (eligibility == null) {
      return Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: EmptyStateView(
            message: 'Eligibility not checked yet',
            subtitle: 'Refresh to evaluate this scheme with your current profile.',
            icon: Icons.fact_check_outlined,
            actionLabel: 'Check eligibility',
            onAction: onRefresh,
          ),
        ),
      );
    }

    final result = eligibility!;
    if (result.totalRules == 0) {
      return Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: EmptyStateView(
            message: 'No eligibility rules found',
            subtitle: 'Refresh after updating your profile or documents.',
            icon: Icons.rule_folder_outlined,
            actionLabel: 'Refresh eligibility',
            onAction: onRefresh,
          ),
        ),
      );
    }

    final colorScheme = Theme.of(context).colorScheme;
    final statusColor = result.eligible ? const Color(0xFF16803C) : colorScheme.error;
    final percent = result.eligibilityPercentage.clamp(0, 100) / 100;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('Your eligibility', style: Theme.of(context).textTheme.titleLarge),
                ),
                IconButton(
                  tooltip: 'Refresh eligibility',
                  onPressed: isLoading ? null : onRefresh,
                  icon: const Icon(Icons.refresh_rounded),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Chip(
                  avatar: Icon(
                    result.eligible ? Icons.check_circle_rounded : Icons.cancel_rounded,
                    color: statusColor,
                  ),
                  side: BorderSide(color: statusColor),
                  backgroundColor: statusColor.withValues(alpha: 0.12),
                  label: Text(result.eligible ? 'Eligible' : 'Not Eligible'),
                ),
                Chip(
                  avatar: Icon(
                    result.applicationReady ? Icons.task_alt_rounded : Icons.pending_actions_rounded,
                    color: result.applicationReady ? colorScheme.primary : colorScheme.tertiary,
                  ),
                  label: Text(result.applicationReady ? 'Application ready' : 'Action needed'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text('${result.eligibilityPercentage.toStringAsFixed(0)}%', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: percent.toDouble(), minHeight: 10),
            const SizedBox(height: 16),
            if (result.reasoning.isNotEmpty) ...[
              Text(result.reasoning, style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 16),
            ],
            _RuleList(title: 'Matched rules', items: result.matchedRules, emptyText: 'No matched rules were returned.'),
            _RuleList(title: 'Failed rules', items: result.failedRules, emptyText: 'No failed rules.'),
            _RuleList(
              title: 'Missing profile information',
              items: result.missingProfileInformation,
              emptyText: 'No missing profile information detected.',
            ),
            _TextList(
              title: 'Missing documents',
              items: result.missingDocuments,
              emptyText: 'No missing documents detected.',
            ),
            _TextList(
              title: 'Required documents',
              items: result.requiredDocuments,
              emptyText: 'No required documents were returned.',
            ),
          ],
        ),
      ),
    );
  }
}

class _RuleList extends StatelessWidget {
  const _RuleList({required this.title, required this.items, required this.emptyText});

  final String title;
  final List<EligibilityRuleResult> items;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    return _ListBlock(
      title: title,
      emptyText: emptyText,
      children: items.map((item) {
        final expected = item.expectedValue?.toString();
        final actual = item.actualValue?.toString();
        return ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(item.passed ? Icons.check_rounded : Icons.close_rounded),
          title: Text(item.displayTitle),
          subtitle: expected == null && actual == null
              ? null
              : Text([
                  if (expected != null && expected.isNotEmpty) 'Expected: $expected',
                  if (actual != null && actual.isNotEmpty) 'Current: $actual',
                ].join('\n')),
        );
      }).toList(),
    );
  }
}

class _TextList extends StatelessWidget {
  const _TextList({required this.title, required this.items, required this.emptyText});

  final String title;
  final List<String> items;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    return _ListBlock(
      title: title,
      emptyText: emptyText,
      children: items.map((item) {
        return ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.description_outlined),
          title: Text(item),
        );
      }).toList(),
    );
  }
}

class _ListBlock extends StatelessWidget {
  const _ListBlock({required this.title, required this.children, required this.emptyText});

  final String title;
  final List<Widget> children;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          if (children.isEmpty)
            Text(emptyText, style: Theme.of(context).textTheme.bodyMedium)
          else
            ...children,
        ],
      ),
    );
  }
}

class _InfoSection extends StatelessWidget {
  const _InfoSection({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(body, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ),
      ),
    );
  }
}
