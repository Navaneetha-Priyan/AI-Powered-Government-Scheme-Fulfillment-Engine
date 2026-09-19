import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/presentation/eligibility_presenter.dart';
import '../../core/utils/evidence_mapping.dart';
import '../../core/utils/formatters.dart';
import '../../core/utils/presentation_text.dart';
import '../../core/widgets/app_states.dart';
import '../../models/eligibility.dart';
import '../../models/government_scheme.dart';
import '../../providers/eligibility_provider.dart';
import '../../providers/scheme_provider.dart';
import '../recommendations/widgets/citizen_rule_list.dart';

/// Human-readable document labels from the centralized evidence mapping —
/// raw snake_case requirement keys are never shown to citizens.
List<String> checkHumanizedDocuments(EligibilityCheck check) {
  final labels = <String>[];
  for (final doc in check.requiredDocuments) {
    final label =
        humanizeEvidenceRequirement(doc.trim().toLowerCase());
    if (label.isNotEmpty && !labels.contains(label)) labels.add(label);
  }
  return labels;
}

/// Safe citizen-facing fallback (shared with the presentation validator).
/// Raw PDF extraction is never used as a fallback — the section shows this
/// text instead.
const String _aboutFallback = schemeAboutFallback;

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

  /// "About this scheme": curated presentation text only. The legacy raw
  /// `description` column (PDF extraction) is NEVER used as a fallback.
  String _aboutText(GovernmentScheme scheme) =>
      scheme.cleanAbout ?? _aboutFallback;

  /// "What you get": validated curated benefit bullets. When none exist the
  /// section is omitted entirely — raw extraction is never displayed.
  List<String> _benefitsBullets(GovernmentScheme scheme) => scheme.cleanBenefits;

  /// "Documents you may need": curated human-readable document names only.
  /// The raw `required_documents` column is never used as a fallback.
  String _documentsBody(GovernmentScheme scheme) {
    final docs = scheme.cleanDocuments;
    return docs.isEmpty ? 'Not specified' : docs.join('\n');
  }

  /// "How to apply": curated application steps only. The raw
  /// `application_process` column is never used as a fallback.
  String _applicationBody(GovernmentScheme scheme) {
    final steps = scheme.cleanApplication;
    return steps.isEmpty ? 'Not specified' : steps.join('\n');
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
          return const Scaffold(
            body: AppLoadingView(message: 'Loading scheme details...'),
          );
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
          appBar: AppBar(title: Text(selected.displayTitle)),
          body: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              // "About this scheme": curated presentation text only. Raw PDF
              // extraction (the legacy `description` column) is never used as a
              // fallback; the safe fallback text is shown instead.
              _InfoSection(
                title: 'About this scheme',
                body: _aboutText(selected),
              ),
              _EligibilitySection(
                eligibility: eligibilityProvider.eligibilityFor(
                  widget.schemeId,
                ),
                isLoading: eligibilityProvider.isLoadingScheme(widget.schemeId),
                errorMessage: eligibilityProvider.errorFor(widget.schemeId),
                onRefresh: () => _loadEligibility(refresh: true),
              ),
              if (selected.cleanWhoItIsFor != null)
                _InfoSection(
                  title: 'Who this is for',
                  body: selected.cleanWhoItIsFor!,
                ),
              _InfoSection(
                title: 'Eligibility criteria',
                body: selected.cleanEligibilitySummary ?? 'Not specified',
              ),
              _InfoSection(
                title: 'Documents you may need',
                body: _documentsBody(selected),
              ),
              // "What you get": only rendered when curated, validated benefit
              // bullets exist. Raw PDF benefits are never displayed, and an
              // empty list omits the section entirely.
              if (_benefitsBullets(selected).isNotEmpty)
                _InfoSection(
                  title: 'What you get',
                  body: _benefitsBullets(selected)
                      .map((benefit) => '• $benefit')
                      .join('\n'),
                ),
              _InfoSection(
                title: 'How to apply',
                body: _applicationBody(selected),
              ),
              _InfoSection(title: 'Department', body: selected.department),
              _InfoSection(
                  title: 'State', body: selected.state ?? 'All India'),
              _InfoSection(
                title: 'Last updated',
                body: AppFormatters.displayDateTime(
                  selected.updatedAt ?? selected.createdAt,
                ),
              ),
              _InfoSection(
                title: 'Contact information',
                body: selected.officialLink ?? 'Not available',
              ),
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
            subtitle:
                'Refresh to evaluate this scheme with your current profile.',
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
    // Citizen-facing presentation: raw percentages, rule internals
    // ("Expected: true / Current: true") and log-style reasoning are
    // replaced with structured, human-readable content.
    final presentation =
        const EligibilityPresentationPresenter().present(result);
    final statusColor = switch (presentation.status) {
      EligibilityStatus.eligible => const Color(0xFF16803C),
      EligibilityStatus.notEligible => colorScheme.error,
      EligibilityStatus.insufficientInformation => colorScheme.tertiary,
      EligibilityStatus.manualReviewRequired => colorScheme.secondary,
      EligibilityStatus.unknown => colorScheme.outline,
    };
    final counts = result.mandatoryConditionCounts;
    final progress =
        counts == null || counts.total == 0 ? null : counts.passed / counts.total;

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
                  child: Text(
                    'Your eligibility',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
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
                    presentation.status == EligibilityStatus.eligible
                        ? Icons.check_circle_rounded
                        : presentation.status ==
                                EligibilityStatus.insufficientInformation
                        ? Icons.help_outline_rounded
                        : presentation.status == EligibilityStatus.notEligible
                        ? Icons.cancel_rounded
                        : Icons.fact_check_outlined,
                    color: statusColor,
                  ),
                  side: BorderSide(color: statusColor),
                  backgroundColor: statusColor.withValues(alpha: 0.12),
                  label: Text(
                    presentation.statusLabel,
                    softWrap: true,
                  ),
                ),
                Chip(
                  avatar: Icon(
                    result.applicationReady
                        ? Icons.task_alt_rounded
                        : Icons.pending_actions_rounded,
                    color: result.applicationReady
                        ? colorScheme.primary
                        : colorScheme.tertiary,
                  ),
                  label: Text(
                    result.applicationReady
                        ? 'Application ready'
                        : 'Action needed',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (presentation.conditionSummary != null) ...[
              Text(
                presentation.conditionSummary!,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              LinearProgressIndicator(value: progress, minHeight: 10),
              const SizedBox(height: 16),
            ],
            // The backend `reasoning` field is an internal log string
            // ("SMAM: Not Eligible | Matched: land_record, ... | 7%") and is
            // intentionally never rendered to citizens.
            CitizenRuleList(
              title: 'Why this may be useful for you',
              passed: presentation.whyYouMatch,
              missingDocuments: const [],
              missingInformation: const [],
              emptyText:
                  'Check back after updating your profile or documents.',
            ),
            CitizenRuleList(
              title: 'What information is missing',
              passed: const [],
              missingDocuments: presentation.missingDocuments,
              missingInformation: presentation.missingInformation,
              emptyText: 'Nothing missing — your profile covers this scheme.',
            ),
            _TextList(
              title: 'Documents you may need',
              items: checkHumanizedDocuments(result),
              emptyText: 'No documents are listed for this scheme.',
            ),
          ],
        ),
      ),
    );
  }
}

class _TextList extends StatelessWidget {
  const _TextList({
    required this.title,
    required this.items,
    required this.emptyText,
  });

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
  const _ListBlock({
    required this.title,
    required this.children,
    required this.emptyText,
  });

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
