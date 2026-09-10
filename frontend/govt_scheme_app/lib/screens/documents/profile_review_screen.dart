import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/network/api_exception.dart';
import '../../core/widgets/app_buttons.dart';
import '../../core/widgets/app_states.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/document_intelligence_provider.dart';
import '../../routes/app_routes.dart';

class ProfileReviewScreen extends StatefulWidget {
  const ProfileReviewScreen({super.key});

  @override
  State<ProfileReviewScreen> createState() => _ProfileReviewScreenState();
}

class _ProfileReviewScreenState extends State<ProfileReviewScreen> {
  bool _isConfirming = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<DocumentIntelligenceProvider>().loadProfileReview(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DocumentIntelligenceProvider>(
      builder: (context, provider, _) {
        final preview = provider.preview;
        if (preview == null) {
          return const Scaffold(
            body: AppLoadingView(message: 'Preparing your digital profile...'),
          );
        }

        final overall = provider.completeness?['overall'] ?? 0;
        final hasConflicts = preview.conflicts.isNotEmpty;
        final conflictFields = preview.conflicts
          .map((conflict) => conflict['field_name']?.toString())
          .whereType<String>()
          .toSet();

        return Scaffold(
          appBar: AppBar(title: const Text('Review Your Profile')),
          body: ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
            children: [
              // ── Completeness card ──────────────────────────────────────
              _CompletenessCard(
                overall: overall,
                fieldCount: preview.fields.length,
                conflictCount: preview.conflicts.length,
              ),
              const SizedBox(height: 20),

              // ── Conflicts ──────────────────────────────────────────────
              if (hasConflicts) ...[
                _ConflictBanner(count: preview.conflicts.length),
                const SizedBox(height: 12),
                ...preview.conflicts.map(
                  (c) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _ConflictCard(
                      conflict: c,
                      onEdit: (field, value) => provider.correct(field, value),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
              ],

              // ── Extracted fields ───────────────────────────────────────
              if (preview.fields.isNotEmpty) ...[
                Text(
                  'Extracted Information',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                ..._groupedFields(preview.fields).entries.map(
                  (group) => _FieldGroup(
                    groupName: group.key,
                    fields: group.value,
                    reviewFields: conflictFields,
                    onCorrect: (key, value) => provider.correct(key, value),
                  ),
                ),
              ],

              const SizedBox(height: 24),

              // ── Confirm button ─────────────────────────────────────────
              if (hasConflicts)
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Theme.of(
                      context,
                    ).colorScheme.error.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: Theme.of(
                        context,
                      ).colorScheme.error.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Text(
                    'Resolve the fields marked Needs review, then confirm your profile. Other extracted fields are ready to use.',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                      fontWeight: FontWeight.w600,
                    ),
                    textAlign: TextAlign.center,
                  ),
                )
              else
                PrimaryButton(
                  label: provider.showingPersistedProfile
                      ? 'Continue to Dashboard'
                      : 'Confirm & Continue',
                  icon: Icons.verified_user_rounded,
                  isLoading: _isConfirming,
                  onPressed: provider.showingPersistedProfile
                      ? _continueToDashboard
                      : _confirm,
                ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _confirm() async {
    final documentProvider = context.read<DocumentIntelligenceProvider>();
    final dashboardProvider = context.read<DashboardProvider>();
    setState(() => _isConfirming = true);
    try {
      await documentProvider.confirm();
      await dashboardProvider.refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Profile confirmed successfully!'),
            backgroundColor: Color(0xFF16803C),
          ),
        );
        Navigator.of(context).pushNamedAndRemoveUntil(
          AppRoutes.home,
          (route) => false,
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error is ApiException
                  ? error.message
                  : 'We could not save your profile. Please review the fields marked Needs review.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isConfirming = false);
    }
  }

  Future<void> _continueToDashboard() async {
    final dashboardProvider = context.read<DashboardProvider>();
    setState(() => _isConfirming = true);
    try {
      await dashboardProvider.refresh();
      if (mounted) {
        Navigator.of(context).pushNamedAndRemoveUntil(
          AppRoutes.home,
          (route) => false,
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error is ApiException ? error.message : 'Could not load your saved profile.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isConfirming = false);
    }
  }

  /// Groups fields by prefix (e.g. "name_*" → "Identity", "income_*" → "Financial")
  Map<String, Map<String, dynamic>> _groupedFields(
    Map<String, dynamic> fields,
  ) {
    final groups = <String, Map<String, dynamic>>{};
    for (final entry in fields.entries) {
      final group = _groupFor(entry.key);
      groups.putIfAbsent(group, () => {})[entry.key] = entry.value;
    }
    return groups;
  }

  String _groupFor(String key) {
    final k = key.toLowerCase();
    if (k.contains('name') || k.contains('dob') || k.contains('gender') ||
        k.contains('aadhaar') || k.contains('birth')) {
      return 'Identity';
    }
    if (k.contains('income') || k.contains('earning') ||
        k.contains('salary')) {
      return 'Financial';
    }
    if (k.contains('caste') || k.contains('community') ||
        k.contains('religion')) {
      return 'Social';
    }
    if (k.contains('land') || k.contains('farm') ||
        k.contains('survey') || k.contains('patta')) {
      return 'Agriculture';
    }
    if (k.contains('address') || k.contains('village') ||
        k.contains('district') || k.contains('state') ||
        k.contains('pincode')) {
      return 'Address';
    }
    if (k.contains('bank') || k.contains('account') ||
        k.contains('ifsc')) {
      return 'Banking';
    }
    if (k.contains('education') || k.contains('school') ||
        k.contains('degree')) {
      return 'Education';
    }
    if (k.contains('disability')) {
      return 'Special Category';
    }
    return 'Other';
  }
}

// ─── Completeness card ─────────────────────────────────────────────────────────

class _CompletenessCard extends StatelessWidget {
  const _CompletenessCard({
    required this.overall,
    required this.fieldCount,
    required this.conflictCount,
  });
  final int overall, fieldCount, conflictCount;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  height: 52,
                  width: 52,
                  decoration: BoxDecoration(
                    color: cs.primary.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.person_pin_rounded,
                    color: cs.primary,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Your Digital Profile',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        '$fieldCount fields extracted',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                Text(
                  '$overall%',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: cs.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: LinearProgressIndicator(
                value: overall / 100,
                minHeight: 10,
                backgroundColor: cs.surfaceContainerHighest,
              ),
            ),
            if (conflictCount > 0) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Icon(
                    Icons.warning_amber_rounded,
                    size: 16,
                    color: cs.error,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '$conflictCount conflict${conflictCount > 1 ? 's' : ''} need your attention',
                    style: TextStyle(
                      color: cs.error,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── Conflict banner ───────────────────────────────────────────────────────────

class _ConflictBanner extends StatelessWidget {
  const _ConflictBanner({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: cs.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cs.error.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: cs.error, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '$count information conflict${count > 1 ? 's' : ''} detected. Review and resolve before confirming.',
              style: TextStyle(
                color: cs.error,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Conflict card ─────────────────────────────────────────────────────────────

class _ConflictCard extends StatelessWidget {
  const _ConflictCard({required this.conflict, required this.onEdit});
  final Map<String, dynamic> conflict;
  final Future<void> Function(String field, String value) onEdit;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final field = conflict['field_name']?.toString() ?? 'Unknown field';
    final v1 = conflict['primary_value']?.toString() ?? '';
    final v2 = conflict['conflicting_value']?.toString() ?? '';

    return Card(
      color: cs.error.withValues(alpha: 0.04),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: cs.error.withValues(alpha: 0.25)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.compare_arrows_rounded, color: cs.error, size: 18),
                const SizedBox(width: 6),
                Text(
                  field.replaceAll('_', ' ').toUpperCase(),
                  style: TextStyle(
                    color: cs.error,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _ConflictValue(label: 'Source 1', value: v1),
            const SizedBox(height: 6),
            _ConflictValue(label: 'Source 2', value: v2),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => _edit(context, field, v1),
                icon: const Icon(Icons.edit_outlined, size: 18),
                label: const Text('Edit and confirm'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _edit(BuildContext context, String field, String value) async {
    final controller = TextEditingController(text: value);
    final next = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Confirm ${field.replaceAll('_', ' ')}'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'Enter the correct value'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, controller.text), child: const Text('Save')),
        ],
      ),
    );
    controller.dispose();
    if (next != null && next.trim().isNotEmpty) {
      await onEdit(field, next.trim());
    }
  }
}

class _ConflictValue extends StatelessWidget {
  const _ConflictValue({required this.label, required this.value});
  final String label, value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 64,
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(
          child: Text(value, style: const TextStyle(fontSize: 13)),
        ),
      ],
    );
  }
}

// ─── Field group ───────────────────────────────────────────────────────────────

class _FieldGroup extends StatelessWidget {
  const _FieldGroup({
    required this.groupName,
    required this.fields,
    required this.reviewFields,
    required this.onCorrect,
  });
  final String groupName;
  final Map<String, dynamic> fields;
  final Set<String> reviewFields;
  final Future<void> Function(String key, String value) onCorrect;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text(
            groupName.toUpperCase(),
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              letterSpacing: 1.2,
            ),
          ),
        ),
        Card(
          child: Column(
            children: fields.entries.map((entry) {
              return _FieldTile(
                fieldKey: entry.key,
                value: entry.value?.toString() ?? '',
                needsReview: reviewFields.contains(entry.key),
                onCorrect: (v) => onCorrect(entry.key, v),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }
}

// ─── Field tile ────────────────────────────────────────────────────────────────

class _FieldTile extends StatelessWidget {
  const _FieldTile({
    required this.fieldKey,
    required this.value,
    required this.needsReview,
    required this.onCorrect,
  });
  final String fieldKey, value;
  final bool needsReview;
  final Future<void> Function(String) onCorrect;

  @override
  Widget build(BuildContext context) {
    final label = fieldKey
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isEmpty ? '' : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');

    final status = needsReview ? 'Needs review' : (value.isEmpty ? 'Missing' : 'Verified');
    final statusColor = needsReview
        ? Theme.of(context).colorScheme.error
        : Theme.of(context).colorScheme.primary;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 3),
                Text(
                  value.isEmpty ? '—' : value,
                  style: const TextStyle(fontSize: 15),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                status,
                textAlign: TextAlign.right,
                style: TextStyle(
                  color: statusColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
              TextButton(
                style: TextButton.styleFrom(
                  minimumSize: const Size(56, 30),
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                onPressed: () => _edit(context),
                child: Text(needsReview ? 'Edit' : 'Correct'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _edit(BuildContext context) async {
    final controller = TextEditingController(text: value);
    final next = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          'Correct ${fieldKey.replaceAll('_', ' ')}',
          style: const TextStyle(fontSize: 17),
        ),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'Enter correct value'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (next != null && next.trim().isNotEmpty) await onCorrect(next.trim());
  }
}
