import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/app_states.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendation_provider.dart';
import 'recommendation_detail_screen.dart';

class RecommendationHistoryScreen extends StatefulWidget {
  const RecommendationHistoryScreen({super.key});

  @override
  State<RecommendationHistoryScreen> createState() => _RecommendationHistoryScreenState();
}

class _RecommendationHistoryScreenState extends State<RecommendationHistoryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<RecommendationProvider>();
    try {
      await provider.loadHistory();
    } catch (_) {
      // handled by provider state
    }
  }

  Future<void> _refresh() async {
    final provider = context.read<RecommendationProvider>();
    if (provider.isHistoryLoading) {
      return;
    }
    await provider.loadHistory(refresh: true);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<RecommendationProvider>(
      builder: (context, provider, _) {
        final history = provider.history;
        return Scaffold(
          appBar: AppBar(title: const Text('Recommendation History')),
          body: provider.isHistoryLoading && history.isEmpty
              ? const AppLoadingView(message: 'Loading history...')
              : history.isEmpty && provider.historyError != null
                  ? AppErrorView(
                      message: AppStrings.friendlyError(provider.historyError!),
                      onRetry: _load,
                    )
                  : history.isEmpty
                      ? EmptyStateView(
                          message: 'No recommendation history yet',
                          subtitle: 'Generate recommendations to see them here.',
                          icon: Icons.history_rounded,
                        )
                      : RefreshIndicator(
                          onRefresh: _refresh,
                          child: ListView.builder(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                            itemCount: history.length,
                            itemBuilder: (context, index) {
                              final entry = history[index];
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: _HistoryCard(entry: entry),
                              );
                            },
                          ),
                        ),
        );
      },
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.entry});

  final RecommendationHistory entry;

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
                  child: Text(
                    AppFormatters.titleCase(entry.requestType),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Chip(
                  avatar: const Icon(Icons.auto_awesome_rounded, size: 16),
                  label: Text('${entry.overallConfidence.toStringAsFixed(0)}%'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${entry.eligibleCount} eligible of ${entry.totalCandidates} candidates • ${entry.status}',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (entry.createdAt != null) ...[
              const SizedBox(height: 4),
              Text(
                AppFormatters.displayDateTime(entry.createdAt),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            if (entry.matches.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: entry.matches.map((match) {
                  return ActionChip(
                    avatar: const Icon(Icons.arrow_forward_rounded, size: 16),
                    label: Text(match.schemeName),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => RecommendationDetailScreen(
                          recommendationId: match.id,
                          initialMatch: match,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

