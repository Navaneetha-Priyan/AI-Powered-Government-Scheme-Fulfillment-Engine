import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/app_states.dart';
import '../../models/citizen_models.dart';
import '../../providers/dashboard_provider.dart';
import '../../routes/app_routes.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final provider = context.read<DashboardProvider>();
    if (provider.dashboard == null) {
      try {
        await provider.loadDashboard();
      } catch (_) {}
    }
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    final provider = context.read<DashboardProvider>();
    if (provider.isLoading) return;
    await provider.refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DashboardProvider>(
      builder: (context, provider, _) {
        final dashboard = provider.dashboard;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Home'),
            actions: [
              IconButton(
                tooltip: 'Refresh',
                onPressed: provider.isLoading ? null : _refresh,
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body: provider.isLoading && dashboard == null
              ? const AppLoadingView(message: 'Loading your information...')
              : dashboard == null
              ? AppErrorView(
                  message: provider.errorMessage ?? 'Something went wrong.',
                  onRetry: () => provider.loadDashboard(),
                )
              : RefreshIndicator(
                  onRefresh: _refresh,
                  child: _DashboardContent(dashboard: dashboard),
                ),
        );
      },
    );
  }
}

class _DashboardContent extends StatelessWidget {
  const _DashboardContent({required this.dashboard});

  final CitizenDashboard dashboard;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final completion = dashboard.profileCompletionPercentage;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── Greeting card ──────────────────────────────────────────
              _GreetingCard(dashboard: dashboard, completion: completion),
              const SizedBox(height: 20),

              // ── Profile setup CTA (if incomplete) ─────────────────────
              if (completion < 80) ...[
                _SetupCta(
                  completion: completion,
                  onTap: () => Navigator.of(context).pushNamed(
                    AppRoutes.documents,
                  ),
                ),
                const SizedBox(height: 20),
              ],

              // ── Quick actions ──────────────────────────────────────────
              Text(
                'What would you like to do?',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              _QuickAction(
                icon: Icons.auto_awesome_rounded,
                label: 'Check My Eligibility',
                subtitle: 'AI-powered scheme recommendations for you',
                color: cs.primary,
                onTap: () => Navigator.of(context).pushNamed(
                  AppRoutes.recommendations,
                ),
              ),
              const SizedBox(height: 10),
              _QuickAction(
                icon: Icons.folder_copy_outlined,
                label: 'My Documents',
                subtitle: '${dashboard.totalDocuments} documents linked',
                color: const Color(0xFF1B8A5A),
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.documents),
              ),
              const SizedBox(height: 10),
              _QuickAction(
                icon: Icons.search_rounded,
                label: 'Browse Schemes',
                subtitle: 'Explore all available government schemes',
                color: const Color(0xFF6A3DE8),
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.schemes),
              ),
              const SizedBox(height: 10),
              _QuickAction(
                icon: Icons.mic_rounded,
                label: 'Voice Assistant',
                subtitle: 'Ask about schemes using your voice',
                color: const Color(0xFFD97706),
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.chat),
              ),

              // ── Document summary ───────────────────────────────────────
              const SizedBox(height: 24),
              Text(
                'Document Summary',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _StatCard(
                      label: 'Total',
                      value: '${dashboard.totalDocuments}',
                      icon: Icons.description_outlined,
                      color: cs.primary,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _StatCard(
                      label: 'Verified',
                      value: '${dashboard.verifiedDocuments}',
                      icon: Icons.verified_outlined,
                      color: const Color(0xFF16803C),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _StatCard(
                      label: 'Pending',
                      value:
                          '${dashboard.totalDocuments - dashboard.verifiedDocuments}',
                      icon: Icons.pending_outlined,
                      color: const Color(0xFF9A6B00),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Greeting card ─────────────────────────────────────────────────────────────

class _GreetingCard extends StatelessWidget {
  const _GreetingCard({required this.dashboard, required this.completion});
  final CitizenDashboard dashboard;
  final int completion;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(22),
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
                    Icons.person_rounded,
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
                        'Hello, ${dashboard.fullName.split(' ').first}',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      Text(
                        '${dashboard.district}, ${dashboard.state}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Profile $completion% complete',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                ),
                Text(
                  '$completion%',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    color: cs.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: LinearProgressIndicator(
                minHeight: 10,
                value: completion / 100,
                backgroundColor: cs.surfaceContainerHighest,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Setup CTA ─────────────────────────────────────────────────────────────────

class _SetupCta extends StatelessWidget {
  const _SetupCta({required this.completion, required this.onTap});
  final int completion;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              cs.primary,
              const Color(0xFF1B8A5A),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.upload_file_rounded,
              color: Colors.white,
              size: 32,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Complete Your Profile',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 17,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    'Upload your documents to unlock scheme recommendations.',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.88),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.arrow_forward_rounded,
              color: Colors.white,
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Quick action card ─────────────────────────────────────────────────────────

class _QuickAction extends StatelessWidget {
  const _QuickAction({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label, subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Container(
                height: 52,
                width: 52,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: color, size: 26),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: Theme.of(context).colorScheme.outline,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Stat card ─────────────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });
  final String label, value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Icon(icon, color: color, size: 26),
            const SizedBox(height: 6),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
