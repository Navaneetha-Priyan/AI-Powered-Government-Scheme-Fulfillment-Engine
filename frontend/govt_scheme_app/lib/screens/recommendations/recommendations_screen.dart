import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

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
    final p = context.read<RecommendationProvider>();
    if (!p.hasLoaded) {
      try { await p.loadRecommendations(); } catch (_) {}
    }
  }

  Future<void> _refresh() async {
    final p = context.read<RecommendationProvider>();
    if (p.isLoading || p.isRefreshing) return;
    await p.loadRecommendations(refresh: true);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Recommendations refreshed.')),
      );
    }
  }

  Future<void> _generate() async {
    final p = context.read<RecommendationProvider>();
    if (p.isLoading || p.isRefreshing) return;
    await p.generateRecommendations();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<RecommendationProvider>(
      builder: (context, p, _) {
        final summary = p.summary;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Recommended Schemes'),
            actions: [
              IconButton(
                tooltip: 'History',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const RecommendationHistoryScreen()),
                ),
                icon: const Icon(Icons.history_rounded),
              ),
              IconButton(
                tooltip: 'Refresh',
                onPressed: (p.isLoading || p.isRefreshing) ? null : _refresh,
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body: p.isLoading && summary == null
              ? const AppLoadingView(message: 'Finding the best schemes for you...')
              : summary == null && p.errorMessage != null
                  ? AppErrorView(message: p.errorMessage!, onRetry: _generate)
                  : summary == null
                      ? EmptyStateView(
                          message: 'No recommendations yet',
                          subtitle: 'Generate AI-powered scheme recommendations based on your profile.',
                          icon: Icons.auto_awesome_outlined,
                          actionLabel: 'Generate Recommendations',
                          onAction: _generate,
                        )
                      : summary.recommendations.isEmpty
                          ? RefreshIndicator(
                              onRefresh: _refresh,
                              child: EmptyStateView(
                                message: 'No eligible schemes found',
                                subtitle: 'Upload more documents or update your profile and try again.',
                                icon: Icons.search_off_rounded,
                                actionLabel: 'Refresh',
                                onAction: _refresh,
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: _refresh,
                              child: CustomScrollView(
                                physics: const AlwaysScrollableScrollPhysics(),
                                slivers: [
                                  SliverToBoxAdapter(
                                    child: Padding(
                                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                                      child: _SummaryHeader(summary: summary, isRefreshing: p.isRefreshing),
                                    ),
                                  ),
                                  SliverPadding(
                                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                                    sliver: SliverList(
                                      delegate: SliverChildBuilderDelegate(
                                        (context, i) => Padding(
                                          padding: const EdgeInsets.only(bottom: 12),
                                          child: _SchemeCard(match: summary.recommendations[i]),
                                        ),
                                        childCount: summary.recommendations.length,
                                      ),
                                    ),
                                  ),
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
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text('Your Recommendations', style: Theme.of(context).textTheme.titleLarge)),
                if (isRefreshing)
                  const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2.4)),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _Chip(icon: Icons.check_circle_outline, label: '${summary.eligibleCount} eligible', color: const Color(0xFF16803C)),
                _Chip(icon: Icons.auto_awesome_rounded, label: '${summary.overallConfidence.toStringAsFixed(0)}% confidence', color: cs.primary),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Generated ${AppFormatters.displayDateTime(summary.generatedAt)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.icon, required this.label, required this.color});
  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color)),
        ],
      ),
    );
  }
}

class _SchemeCard extends StatelessWidget {
  const _SchemeCard({required this.match});
  final RecommendationMatch match;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isEligible = match.isEligible;
    final eligColor = isEligible ? const Color(0xFF16803C) : const Color(0xFF9A6B00);

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => RecommendationDetailScreen(recommendationId: match.id, initialMatch: match),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    height: 40, width: 40,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: cs.primary.withValues(alpha: 0.12), shape: BoxShape.circle),
                    child: Text('#${match.rankingPosition}',
                        style: TextStyle(color: cs.primary, fontWeight: FontWeight.w800, fontSize: 13)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(match.schemeName, style: Theme.of(context).textTheme.titleMedium),
                        if (isEligible)
                          const Text('Highly Recommended',
                              style: TextStyle(color: Color(0xFF16803C), fontWeight: FontWeight.w700, fontSize: 12)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8, runSpacing: 8,
                children: [
                  _ScoreChip(label: 'Eligibility', value: '${match.eligibilityPercentage.toStringAsFixed(0)}%', color: eligColor),
                  _ScoreChip(label: 'Match', value: '${match.confidenceScore.toStringAsFixed(0)}%', color: cs.primary),
                  if (match.estimatedBenefit != null && match.estimatedBenefit!.isNotEmpty)
                    _BenefitChip(benefit: match.estimatedBenefit!),
                ],
              ),
              if (match.recommendationReason != null && match.recommendationReason!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(match.recommendationReason!, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium),
              ],
              if (match.matchedRules.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12, runSpacing: 4,
                  children: match.matchedRules.take(3)
                      .map((r) => _RuleChip(label: r.displayTitle, passed: r.passed))
                      .toList(),
                ),
              ],
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => RecommendationDetailScreen(recommendationId: match.id, initialMatch: match),
                    ),
                  ),
                  icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                  label: const Text('View Scheme'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScoreChip extends StatelessWidget {
  const _ScoreChip({required this.label, required this.value, required this.color});
  final String label, value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text('$label  $value',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color)),
    );
  }
}

class _BenefitChip extends StatelessWidget {
  const _BenefitChip({required this.benefit});
  final String benefit;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFF1B8A5A).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF1B8A5A).withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.savings_outlined, size: 13, color: Color(0xFF1B8A5A)),
          const SizedBox(width: 4),
          Text(benefit,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF1B8A5A))),
        ],
      ),
    );
  }
}

class _RuleChip extends StatelessWidget {
  const _RuleChip({required this.label, required this.passed});
  final String label;
  final bool passed;

  @override
  Widget build(BuildContext context) {
    final color = passed ? const Color(0xFF16803C) : const Color(0xFF9A6B00);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(passed ? Icons.check_circle_outline : Icons.radio_button_unchecked, size: 14, color: color),
        const SizedBox(width: 3),
        Text(label, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
