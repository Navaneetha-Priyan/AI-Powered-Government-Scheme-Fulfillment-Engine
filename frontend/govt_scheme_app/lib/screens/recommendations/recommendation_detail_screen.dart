import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/widgets/app_states.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendation_provider.dart';
import '../schemes/scheme_detail_screen.dart';

class RecommendationDetailScreen extends StatefulWidget {
  const RecommendationDetailScreen({
    super.key,
    required this.recommendationId,
    this.initialMatch,
  });

  final String recommendationId;
  final RecommendationMatch? initialMatch;

  @override
  State<RecommendationDetailScreen> createState() => _RecommendationDetailScreenState();
}

class _RecommendationDetailScreenState extends State<RecommendationDetailScreen> {
  @override
  void initState() {
    super.initState();
    if (widget.initialMatch == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    }
  }

  Future<void> _load() async {
    final provider = context.read<RecommendationProvider>();
    await provider.loadRecommendationDetail(widget.recommendationId);
    if (!mounted) {
      return;
    }
    final match = provider.recommendationFor(widget.recommendationId);
    if (match == null && provider.errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppStrings.friendlyError(provider.errorMessage!))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<RecommendationProvider>(
      builder: (context, provider, _) {
        final match = provider.recommendationFor(widget.recommendationId) ?? widget.initialMatch;

        if (match == null) {
          if (provider.isLoadingRecommendation(widget.recommendationId)) {
            return const Scaffold(
              body: AppLoadingView(message: 'Loading recommendation...'),
            );
          }
          return Scaffold(
            appBar: AppBar(title: const Text('Recommendation')),
            body: AppErrorView(
              message: provider.errorMessage ?? AppStrings.somethingWrong,
              onRetry: _load,
            ),
          );
        }

        final statusColor = match.isEligible ? const Color(0xFF16803C) : Theme.of(context).colorScheme.error;

        return Scaffold(
          appBar: AppBar(title: Text('Recommendation')),
          body: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(match.schemeName, style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          Chip(
                            backgroundColor: statusColor.withValues(alpha: 0.14),
                            side: BorderSide(color: statusColor),
                            label: Text(
                              match.isEligible ? 'Eligible' : 'Not eligible',
                              style: TextStyle(color: statusColor),
                            ),
                          ),
                          Chip(
                            avatar: const Icon(Icons.percent_rounded, size: 18),
                            label: Text('${match.eligibilityPercentage.toStringAsFixed(0)}% eligibility'),
                          ),
                          Chip(
                            avatar: const Icon(Icons.verified_outlined, size: 18),
                            label: Text('${match.confidenceScore.toStringAsFixed(0)}% confidence'),
                          ),
                          if (match.applicationReady)
                            Chip(
                              avatar: const Icon(Icons.task_alt_rounded, size: 18),
                              label: const Text('Application ready'),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              if (match.recommendationReason != null && match.recommendationReason!.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Why this was recommended',
                  icon: Icons.lightbulb_outline,
                  child: Text(match.recommendationReason!, style: Theme.of(context).textTheme.bodyLarge),
                ),
              ],
              if (match.description != null && match.description!.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Scheme description',
                  icon: Icons.description_outlined,
                  child: Text(match.description!, style: Theme.of(context).textTheme.bodyLarge),
                ),
              ],
              if (match.matchedRules.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Matched profile attributes',
                  icon: Icons.person_pin_circle_outlined,
                  child: _RuleList(
                    items: match.matchedRules,
                    emptyText: 'No matched attributes.',
                  ),
                ),
              ],
              if (match.requiredDocuments.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Matched documents',
                  icon: Icons.folder_copy_outlined,
                  child: _TextList(items: match.requiredDocuments),
                ),
              ],
              if (match.missingRequirements.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Missing requirements',
                  icon: Icons.priority_high_rounded,
                  child: _RuleList(
                    items: match.missingRequirements,
                    emptyText: 'No missing requirements.',
                  ),
                ),
              ],
              if (match.benefits != null && match.benefits!.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Expected benefits',
                  icon: Icons.savings_outlined,
                  child: Text(match.benefits!, style: Theme.of(context).textTheme.bodyLarge),
                ),
              ],
              if (match.estimatedBenefit != null && match.estimatedBenefit!.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Estimated benefit',
                  icon: Icons.payments_outlined,
                  child: Text(match.estimatedBenefit!, style: Theme.of(context).textTheme.titleMedium),
                ),
              ],
              if (match.semanticQuery != null && match.semanticQuery!.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Matched eligibility rules',
                  icon: Icons.rule_folder_outlined,
                  child: Text(match.semanticQuery!, style: Theme.of(context).textTheme.bodyMedium),
                ),
              ],
              const SizedBox(height: 12),
              _DetailSection(
                title: 'Next steps',
                icon: Icons.rocket_launch_outlined,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      match.applicationReady
                          ? 'Your profile is ready. You can apply for this scheme.'
                          : 'Complete your profile and add the missing documents to improve eligibility.',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => SchemeDetailScreen(schemeId: match.schemeId),
                        ),
                      ),
                      icon: const Icon(Icons.article_outlined),
                      label: const Text('View scheme details'),
                    ),
                  ],
                ),
              ),
              if (match.missingRequirements.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Required actions',
                  icon: Icons.checklist_rounded,
                  child: _TextList(
                    items: match.missingRequirements
                        .map((rule) => rule.displayTitle)
                        .toSet()
                        .toList(),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _DetailSection extends StatelessWidget {
  const _DetailSection({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 22, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(title, style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 10),
            child,
          ],
        ),
      ),
    );
  }
}

class _RuleList extends StatelessWidget {
  const _RuleList({required this.items, required this.emptyText});

  final List<RecommendationRule> items;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Text(emptyText, style: Theme.of(context).textTheme.bodyMedium);
    }
    return Column(
      children: items.map((item) {
        final expected = item.expectedValue?.toString();
        final actual = item.actualValue?.toString();
        return ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(item.passed ? Icons.check_circle_rounded : Icons.cancel_rounded),
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
  const _TextList({required this.items});

  final List<String> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Text('No items.', style: Theme.of(context).textTheme.bodyMedium);
    }
    return Column(
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

