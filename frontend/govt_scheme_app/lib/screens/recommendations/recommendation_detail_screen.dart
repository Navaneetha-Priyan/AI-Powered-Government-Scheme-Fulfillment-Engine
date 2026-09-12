import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/evidence_mapping.dart';
import '../../core/widgets/app_states.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendation_provider.dart';
import '../../routes/app_routes.dart';
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
  State<RecommendationDetailScreen> createState() =>
      _RecommendationDetailScreenState();
}

class _RecommendationDetailScreenState
    extends State<RecommendationDetailScreen> {
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
        SnackBar(
          content: Text(AppStrings.friendlyError(provider.errorMessage!)),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<RecommendationProvider>(
      builder: (context, provider, _) {
        final match =
            provider.recommendationFor(widget.recommendationId) ??
            widget.initialMatch;

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

        final statusColor = match.isEligible
            ? const Color(0xFF16803C)
            : Theme.of(context).colorScheme.error;

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
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        match.schemeName,
                        softWrap: true,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Chip(
                            backgroundColor: statusColor.withValues(
                              alpha: 0.14,
                            ),
                            side: BorderSide(color: statusColor),
                            label: ConstrainedBox(
                              constraints:
                                  const BoxConstraints(maxWidth: 220),
                              child: Text(
                                match.isEligible ? 'Eligible' : 'Not eligible',
                                softWrap: true,
                                style: TextStyle(color: statusColor),
                              ),
                            ),
                          ),
                          Chip(
                            avatar: const Icon(Icons.percent_rounded, size: 18),
                            label: Text(
                              '${match.eligibilityPercentage.toStringAsFixed(0)}% eligibility',
                            ),
                          ),
                          Chip(
                            avatar: const Icon(
                              Icons.verified_outlined,
                              size: 18,
                            ),
                            label: Text(
                              '${match.confidenceScore.toStringAsFixed(0)}% confidence',
                            ),
                          ),
                          if (match.applicationReady)
                            Chip(
                              avatar: const Icon(
                                Icons.task_alt_rounded,
                                size: 18,
                              ),
                              label: const Text('Application ready'),
                            ),
                        ],
                      ),
                      // Sanitized citizen summary lives on the header card.
                      // Full raw backend text is never dumped here.
                      if (match.cardReason != null) ...[
                        const SizedBox(height: 12),
                        Text('Why you match:',
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        Text(match.cardReason!,
                            style: Theme.of(context).textTheme.bodyLarge),
                      ],
                    ],
                  ),
                ),
              ),
              if (match.cardReason != null) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Why this was recommended',
                  icon: Icons.lightbulb_outline,
                  child: Text(
                    match.cardReason!,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                ),
              ],
              if (match.description != null &&
                  match.description!.isNotEmpty) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Scheme description',
                  icon: Icons.description_outlined,
                  child: Text(
                    match.description!,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
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
              if (match.requiredDocuments.isNotEmpty ||
                  match.missingRequirements.isNotEmpty) ...[
                const SizedBox(height: 12),
                _EvidenceChecklistCard(match: match),
              ],
              // NOT shown here: a raw \"Missing requirements\" list would leak
              // internal field names (income_tax_payer, farmer_registration,
              // ...). _EvidenceChecklistCard above already surfaces every
              // missing item with a human-readable label + next action.
              // Never fall back to the raw `benefits` string here: when
              // `cardBenefit` is null the backend text was classified as
              // retrieval noise, and showing it would reintroduce the dump.
              if (match.cardBenefit != null) ...[
                const SizedBox(height: 12),
                _DetailSection(
                  title: 'Expected benefits',
                  icon: Icons.savings_outlined,
                  child: Text(
                    match.cardBenefit!,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                ),
              ],
              // 'Estimated benefit' raw string is NOT shown separately:
              // cardBenefit (sanitized estimatedBenefit/benefits) is already
              // rendered above as 'Expected benefits'.
              // Raw retrieval text (semantic_query) is internal debug info and
              // is NEVER shown to citizens.
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
                          builder: (_) =>
                              SchemeDetailScreen(schemeId: match.schemeId),
                        ),
                      ),
                      icon: const Icon(Icons.article_outlined),
                      label: const Text('View scheme details'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _EvidenceChecklistCard extends StatelessWidget {
  const _EvidenceChecklistCard({required this.match});
  final RecommendationMatch match;

  @override
  Widget build(BuildContext context) {
    final items = match.evidenceItems;
    if (items.isEmpty) return const SizedBox.shrink();
    final available =
        items.where((e) => e.status == EvidenceStatus.available).toList();
    final neededDocs = items
        .where((e) =>
            e.kind == EvidenceKind.document &&
            e.status == EvidenceStatus.needed)
        .toList();
    final neededProfile = items
        .where((e) =>
            e.kind == EvidenceKind.profileInfo &&
            e.status == EvidenceStatus.needed)
        .toList();
    final manual = items
        .where((e) => e.status == EvidenceStatus.manual)
        .toList();
    return _DetailSection(
      title: 'Documents & evidence',
      icon: Icons.folder_copy_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (available.isNotEmpty) ...[
            _SectionLabel('Documents'),
            for (final entry in available)
              _ChecklistRow(
                icon: Icons.check_circle_rounded,
                iconColor: const Color(0xFF16803C),
                label: '✓ ${entry.label}',
              ),
            const SizedBox(height: 8),
          ],
          if (neededDocs.isNotEmpty) ...[
            _SectionLabel('Still needed'),
            for (final entry in neededDocs)
              _ChecklistRow(
                icon: Icons.upload_rounded,
                iconColor: Theme.of(context).colorScheme.primary,
                label: '• ${entry.label}',
                note: entry.note,
                actionLabel: 'Upload document',
                actionRoute: AppRoutes.documents,
              ),
            const SizedBox(height: 8),
          ],
          if (neededProfile.isNotEmpty) ...[
            _SectionLabel('Information needed'),
            for (final entry in neededProfile)
              _ChecklistRow(
                icon: Icons.person_pin_circle_outlined,
                iconColor: Theme.of(context).colorScheme.secondary,
                label: '• ${entry.profilePrompt ?? entry.label}',
                actionLabel: 'Complete profile',
                actionRoute: AppRoutes.editProfile,
              ),
            const SizedBox(height: 8),
          ],
          if (manual.isNotEmpty) ...[
            _SectionLabel('Manual verification'),
            for (final entry in manual)
              _ChecklistRow(
                icon: Icons.description_outlined,
                iconColor: Theme.of(context).colorScheme.outline,
                label: '• ${entry.label}',
                note: entry.note ??
                    'Additional scheme-specific evidence may be required.',
              ),
          ],
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text(text,
          style: Theme.of(context)
              .textTheme
              .labelLarge
              ?.copyWith(fontWeight: FontWeight.w700)),
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({
    required this.icon,
    required this.iconColor,
    required this.label,
    this.note,
    this.actionLabel,
    this.actionRoute,
  });
  final IconData icon; final Color iconColor; final String label;
  final String? note; final String? actionLabel; final String? actionRoute;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon, size: 16, color: iconColor),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label,
                    softWrap: true,
                    style: Theme.of(context).textTheme.bodyMedium),
                if (note != null && note!.isNotEmpty)
                  Text(note!,
                      softWrap: true,
                      style: Theme.of(context).textTheme.bodySmall),
                if (actionLabel != null && actionRoute != null)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        minimumSize: const Size(0, 32),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      // Reuses the EXISTING upload/profile flows via their
                      // named routes; no duplicate upload logic is created.
                      onPressed: () =>
                          Navigator.of(context).pushNamed(actionRoute!),
                      icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                      label: Text(actionLabel!),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
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
                Icon(
                  icon,
                  size: 22,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(title,
                      style: Theme.of(context).textTheme.titleMedium),
                ),
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
      mainAxisSize: MainAxisSize.min,
      children: items.map((item) {
        final expected = item.expectedValue?.toString();
        final actual = item.actualValue?.toString();
        return ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(
            item.passed ? Icons.check_circle_rounded : Icons.cancel_rounded,
          ),
          // Title wraps; raw rule internals are never single-line-clamped
          // into an overflow.
          title: Text(item.displayTitle, softWrap: true),
          subtitle: expected == null && actual == null
              ? null
              : Text(
                  [
                    if (expected != null && expected.isNotEmpty)
                      'Expected: $expected',
                    if (actual != null && actual.isNotEmpty) 'Current: $actual',
                  ].join('\n'),
                  softWrap: true,
                ),
        );
      }).toList(),
    );
  }
}
