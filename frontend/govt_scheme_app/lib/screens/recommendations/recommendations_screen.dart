import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendation_provider.dart';
import 'recommendation_detail_screen.dart';
import 'recommendation_history_screen.dart';

class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({super.key});

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<RecommendationProvider>();
    if (!provider.hasLoaded) {
      try {
        await provider.loadRecommendations();
      } catch (_) {
        // handled by provider state
      }
    }
  }

  Future<void> _refresh() async {
    final provider = context.read<RecommendationProvider>();
    if (provider.isLoading || provider.isRefreshing) {
      return;
    }
    await provider.loadRecommendations(refresh: true);
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Recommendations refreshed.')),
    );
  }

  Future<void> _generate() async {
    final provider = context.read<RecommendationProvider>();
    if (provider.isLoading || provider.isRefreshing) {
      return;
    }
    await provider.generateRecommendations();
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Recommendations generated.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<RecommendationProvider>(
      builder: (context, provider, _) {
        final summary = provider.summary;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Recommended Schemes'),
            actions: [
              IconButton(
                tooltip: 'Recommendation history',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const RecommendationHistoryScreen()),
                ),
                icon: const Icon(Icons.history_rounded),
              ),
              IconButton(
                tooltip: 'Refresh recommendations',
                onPressed: (provider.isLoading || provider.isRefreshing) ? null : _refresh,
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body: provider.isLoading && summary == null
              ? const AppLoadingView(message: 'Generating your recommendations...')
              : summary == null && provider.errorMessage != null
                  ? AppErrorView(
                      message: AppStrings.friendlyError(provider.errorMessage!),
                      onRetry: _generate,
                    )
                  : summary == null
                      ? EmptyStateView(
                          message: 'No recommendations yet',
                          subtitle: 'Generate recommendations based on your profile.',
                          icon: Icons.auto_awesome_outlined,
                          actionLabel: 'Generate recommendations',
                          onAction: _generate,
                        )
                      : summary.recommendations.isEmpty
                          ? RefreshIndicator(
                              onRefresh: _refresh,
                              child: EmptyStateView(
                                message: 'No eligible schemes found',
                                subtitle: 'Update your profile or documents and try again.',
                                icon: Icons.search_off_rounded,
                                actionLabel: 'Refresh recommendations',
                                onAction: _refresh,
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: _refresh,
                              child: ListView(
                                physics: const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                                children: [
                                  _SummaryHeader(summary: summary, isRefreshing: provider.isRefreshing),
                                  const SizedBox(height: 16),
                                  ...summary.recommendations.map((match) {
                                    return Padding(
                                      padding: const EdgeInsets.only(bottom: 12),
                                      child: _RecommendationCard(match: match),
                                    );
                                  }),
                                ],
                              ),
                            ),
        );
      },
    );
  }
}

class _SummaryHeader extends StatelessWidget {
  const _SummaryHeader({required this.summary, required this.isRefreshing});

  final RecommendationSummary summary;
  final bool isRefreshing;

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
                Expanded(
                  child: Text('Your Recommendations', style: Theme.of(context).textTheme.titleLarge),
                ),
                if (isRefreshing)
                  const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2.4),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                Chip(
                  avatar: const Icon(Icons.auto_awesome_rounded, size: 18),
                  label: Text('${summary.eligibleCount} eligible'),
                ),
                Chip(
                  avatar: const Icon(Icons.percent_rounded, size: 18),
                  label: Text('${summary.overallConfidence.toStringAsFixed(0)}% confidence'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Generated ${summary.generatedAt == null ? '' : AppFormatters.displayDateTime(summary.generatedAt)}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.match});

  final RecommendationMatch match;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final statusColor = match.isEligible ? const Color(0xFF16803C) : colorScheme.error;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => RecommendationDetailScreen(
              recommendationId: match.id,
              initialMatch: match,
            ),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    height: 34,
                    width: 34,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: colorScheme.primary.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      '${match.rankingPosition}',
                      style: TextStyle(
                        color: colorScheme.primary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      match.schemeName,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  Chip(
                    backgroundColor: statusColor.withValues(alpha: 0.14),
                    side: BorderSide(color: statusColor),
                    label: Text(
                      '${match.eligibilityPercentage.toStringAsFixed(0)}% eligible',
                      style: TextStyle(color: statusColor),
                    ),
                  ),
                  Chip(
                    avatar: const Icon(Icons.verified_outlined, size: 18),
                    label: Text('${match.confidenceScore.toStringAsFixed(0)}% confidence'),
                  ),
                  if (match.estimatedBenefit != null && match.estimatedBenefit!.isNotEmpty)
                    Chip(
                      avatar: const Icon(Icons.savings_outlined, size: 18),
                      label: Text(match.estimatedBenefit!),
                    ),
                ],
              ),
              if (match.recommendationReason != null && match.recommendationReason!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  match.recommendationReason!,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

