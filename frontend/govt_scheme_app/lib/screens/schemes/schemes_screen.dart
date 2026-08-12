import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/localization/app_strings.dart';
import '../../core/widgets/app_states.dart';
import '../../providers/scheme_provider.dart';
import 'scheme_detail_screen.dart';

class SchemesScreen extends StatefulWidget {
  const SchemesScreen({super.key});

  @override
  State<SchemesScreen> createState() => _SchemesScreenState();
}

class _SchemesScreenState extends State<SchemesScreen> {
  final TextEditingController _searchController = TextEditingController();
  bool _filtersExpanded = false;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchTextChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _searchController.removeListener(_onSearchTextChanged);
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchTextChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _load() async {
    final provider = context.read<SchemeProvider>();
    if (_searchController.text != provider.query) {
      _searchController.value = TextEditingValue(
        text: provider.query,
        selection: TextSelection.collapsed(offset: provider.query.length),
      );
    }
    if (!provider.hasLoaded) {
      try {
        await provider.loadSchemes();
      } catch (_) {}
    }
  }

  Future<void> _refresh() async {
    await context.read<SchemeProvider>().loadSchemes(refresh: true);
  }

  Future<void> _loadMore() async {
    await context.read<SchemeProvider>().loadSchemes(append: true);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SchemeProvider>(
      builder: (context, provider, _) {
        return Scaffold(
          appBar: AppBar(title: const Text('Scheme Discovery')),
          body: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                    child: TextField(
                      controller: _searchController,
                      onChanged: provider.search,
                      decoration: InputDecoration(
                        hintText: 'Search schemes',
                        prefixIcon: const Icon(Icons.search_rounded),
                        suffixIcon: _searchController.text.isEmpty
                            ? IconButton(
                                icon: const Icon(Icons.tune_rounded),
                                onPressed: () => setState(
                                  () => _filtersExpanded = !_filtersExpanded,
                                ),
                              )
                            : IconButton(
                                icon: const Icon(Icons.clear_rounded),
                                onPressed: () {
                                  _searchController.clear();
                                  provider.search('');
                                },
                              ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                    ),
                  ),
                  if (_filtersExpanded)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          _FilterChip(
                            label: 'Category',
                            value: provider.filters.category,
                            onTap: () => _showFilterSheet(provider),
                          ),
                          _FilterChip(
                            label: 'State',
                            value: provider.filters.state,
                            onTap: () => _showFilterSheet(provider),
                          ),
                          _FilterChip(
                            label: 'Department',
                            value: provider.filters.department,
                            onTap: () => _showFilterSheet(provider),
                          ),
                          _FilterChip(
                            label: 'Status',
                            value: provider.filters.eligibilityStatus,
                            onTap: () => _showFilterSheet(provider),
                          ),
                        ],
                      ),
                    ),
                  Expanded(
                    child: provider.isLoading && provider.schemes.isEmpty
                        ? const AppLoadingView(message: 'Loading schemes...')
                        : provider.errorMessage != null &&
                              provider.schemes.isEmpty
                        ? AppErrorView(
                            message: AppStrings.friendlyError(
                              provider.errorMessage!,
                            ),
                            onRetry: () => provider.loadSchemes(refresh: true),
                          )
                        : provider.schemes.isEmpty
                        ? EmptyStateView(
                            message: 'No schemes found',
                            subtitle: 'Try a different keyword or filter.',
                            icon: Icons.description_outlined,
                          )
                        : RefreshIndicator(
                            onRefresh: _refresh,
                            child: ListView.separated(
                              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                              itemCount:
                                  provider.schemes.length +
                                  (provider.hasMore ? 1 : 0),
                              separatorBuilder: (_, _) =>
                                  const SizedBox(height: 12),
                              itemBuilder: (context, index) {
                                if (index == provider.schemes.length) {
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(
                                      vertical: 12,
                                    ),
                                    child: Center(
                                      child: provider.isLoadingMore
                                          ? const CircularProgressIndicator()
                                          : TextButton(
                                              onPressed: _loadMore,
                                              child: const Text('Load more'),
                                            ),
                                    ),
                                  );
                                }

                                final scheme = provider.schemes[index];
                                return Card(
                                  child: ListTile(
                                    contentPadding: const EdgeInsets.all(16),
                                    title: Text(
                                      scheme.schemeName,
                                      style: Theme.of(
                                        context,
                                      ).textTheme.titleMedium,
                                    ),
                                    subtitle: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        const SizedBox(height: 8),
                                        Text(
                                          scheme.description,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        const SizedBox(height: 8),
                                        Wrap(
                                          spacing: 8,
                                          runSpacing: 6,
                                          children: [
                                            Chip(label: Text(scheme.category)),
                                            Chip(
                                              label: Text(scheme.department),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                    trailing: const Icon(
                                      Icons.chevron_right_rounded,
                                    ),
                                    onTap: () {
                                      provider.selectScheme(scheme.id);
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => SchemeDetailScreen(
                                            schemeId: scheme.id,
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                                );
                              },
                            ),
                          ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _showFilterSheet(SchemeProvider provider) async {
    final categoryController = TextEditingController(
      text: provider.filters.category ?? '',
    );
    final stateController = TextEditingController(
      text: provider.filters.state ?? '',
    );
    final departmentController = TextEditingController(
      text: provider.filters.department ?? '',
    );
    final statusController = TextEditingController(
      text: provider.filters.eligibilityStatus ?? '',
    );

    try {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (sheetContext) {
          return Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 16,
              bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 16,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Filters', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 16),
                TextField(
                  controller: categoryController,
                  decoration: const InputDecoration(labelText: 'Category'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: stateController,
                  decoration: const InputDecoration(labelText: 'State'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: departmentController,
                  decoration: const InputDecoration(labelText: 'Department'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: statusController,
                  decoration: const InputDecoration(
                    labelText: 'Eligibility status',
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () async {
                          Navigator.pop(sheetContext);
                          await provider.clearFilters();
                        },
                        child: const Text('Clear'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton(
                        onPressed: () async {
                          Navigator.pop(sheetContext);
                          await provider.setFilters(
                            category: categoryController.text.trim(),
                            state: stateController.text.trim(),
                            department: departmentController.text.trim(),
                            eligibilityStatus: statusController.text.trim(),
                          );
                        },
                        child: const Text('Apply'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      );
    } finally {
      categoryController.dispose();
      stateController.dispose();
      departmentController.dispose();
      statusController.dispose();
    }
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.value,
    required this.onTap,
  });

  final String label;
  final String? value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(value == null || value!.isEmpty ? label : '$label: $value'),
      onPressed: onTap,
      avatar: const Icon(Icons.filter_list_rounded, size: 18),
    );
  }
}
