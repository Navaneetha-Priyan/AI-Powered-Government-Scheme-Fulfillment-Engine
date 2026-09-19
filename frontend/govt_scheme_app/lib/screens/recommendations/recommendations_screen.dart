import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/presentation/eligibility_presenter.dart';
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

  /// Shows the precise timeout message for slow first-time generation
  /// instead of the generic connectivity text, so users know a retry is
  /// meaningful (the server keeps working / warms up in the meantime).
  String _displayError(String raw) {
    if (raw.toLowerCase().contains('timed out while generating')) {
      return raw;
    }
    return AppStrings.friendlyError(raw);
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
          body: (p.isLoading || p.isRefreshing) && summary == null
              ? const AppLoadingView(message: 'Finding the best schemes for you...')
              : summary == null && p.errorMessage != null
                  ? AppErrorView(
                      message: _displayError(p.errorMessage!),
                      // Retry the load instead of forcing a generate, so the
                      // button behaves identically on first and second taps.
                      onRetry: _load,
                    )
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
                        Text(match.displayTitle,
                            softWrap: true,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        _StatusPill(
                            status: cardStatusLine(match.eligibilityStatus),
                            color: eligColor),
                        if (isEligible)
                          const Text('Highly Recommended',
                              style: TextStyle(color: Color(0xFF16803C), fontWeight: FontWeight.w700, fontSize: 12)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              // ── Citizen-facing sections (sanitized, wrapped, bounded) ──
              // Raw retrieval metadata (semantic_query chunks, file refs,
              // page markers) and the raw recommendation_reason log string
              // are intentionally never rendered on the card. The short
              // description comes from the curated presentation metadata.
              if (match.cleanShortDescription != null) ...[
                Text(match.cleanShortDescription!,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    softWrap: true,
                    style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 4),
              ],
              if (match.cardMatchBullets.isNotEmpty) ...[
                Text('Why this may be useful for you:',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                for (final bullet in match.cardMatchBullets)
                  _Bullet(icon: Icons.check_circle_outline, text: bullet),
              ],
              // Benefits come from the curated presentation metadata only.
              // The raw DB/RAG-derived benefit string is never rendered, and
              // an empty list omits the section entirely.
              if (match.benefitBullets.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text('Benefits:',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                for (final bullet in match.benefitBullets.take(3))
                  _Bullet(icon: Icons.check_circle_outline, text: bullet),
              ],
              if (match.cardMissingBullets.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text('More information needed:',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                for (final bullet in match.cardMissingBullets)
                  _Bullet(icon: Icons.info_outline_rounded, text: bullet),
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

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status, required this.color});
  final String status;
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
      // Constrain long statuses so they wrap instead of overflowing.
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 220),
        child: Text(
          // Already a citizen label from the presentation layer.
          status,
          softWrap: true,
          style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700, color: color),
        ),
      ),
    );
  }
}

/// Bullet row safe inside narrow cards: icon + expanded wrapped text.
class _Bullet extends StatelessWidget {
  const _Bullet({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon,
                size: 15, color: Theme.of(context).colorScheme.primary),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

String cardStatusLine(String statusLabel) {
  // Delegate to the shared presentation layer: raw backend statuses
  // ("potentially_eligible", "insufficient_information", ...) become
  // citizen phrases and internal names are never leaked.
  return EligibilityPresentationPresenter.citizenStatusLabel(statusLabel);
}

/// Public, testable vertical list of recommendation cards.
///
/// Used by widget tests to pump a single card at a fixed narrow width
/// (e.g. 360px) and assert no overflow + no raw RAG dump.
class RecommendationsListView extends StatelessWidget {
  const RecommendationsListView({super.key, required this.matches});
  final List<RecommendationMatch> matches;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: matches.length,
      itemBuilder: (context, i) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: _SchemeCard(match: matches[i]),
      ),
    );
  }
}
