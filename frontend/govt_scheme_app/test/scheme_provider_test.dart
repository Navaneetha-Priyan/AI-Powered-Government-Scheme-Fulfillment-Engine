import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/models/government_scheme.dart';
import 'package:govt_scheme_app/providers/scheme_provider.dart';
import 'package:govt_scheme_app/repositories/scheme_repository.dart';

class _FakeSchemeRepository extends SchemeRepository {
  _FakeSchemeRepository() : super(null);

  int listCalls = 0;
  int searchCalls = 0;
  int detailCalls = 0;
  String? lastSearchQuery;

  final List<GovernmentScheme> _items = const [
    GovernmentScheme(
      id: '1',
      schemeName: 'Farmers Support Scheme',
      description: 'Support for farmers',
      category: 'agriculture',
      department: 'Agriculture',
      governmentLevel: 'state',
      state: 'Tamil Nadu',
      benefits: 'Rs 50000 annual support',
      eligibilitySummary: 'Farmer families only',
      requiredDocuments: 'Aadhaar, land records',
      applicationProcess: 'Apply online',
      officialLink: 'https://example.com',
      language: 'en',
      status: 'active',
      createdAt: null,
      updatedAt: null,
    ),
    GovernmentScheme(
      id: '2',
      schemeName: 'Women Empowerment Scheme',
      description: 'Support for women',
      category: 'social',
      department: 'Social Welfare',
      governmentLevel: 'central',
      state: 'Tamil Nadu',
      benefits: 'Rs 25000 one-time support',
      eligibilitySummary: 'Women residents only',
      requiredDocuments: 'Aadhaar, income certificate',
      applicationProcess: 'Apply online',
      officialLink: 'https://example.com',
      language: 'en',
      status: 'active',
      createdAt: null,
      updatedAt: null,
    ),
  ];

  @override
  Future<SchemeListResponse> listSchemes({
    int skip = 0,
    int limit = 20,
    String? category,
    String? status,
    String? query,
  }) async {
    listCalls += 1;
    return SchemeListResponse(
      items: _items.skip(skip).take(limit).toList(),
      total: 2,
      skip: skip,
      limit: limit,
    );
  }

  @override
  Future<SchemeListResponse> searchSchemes(String query, {int limit = 10}) async {
    searchCalls += 1;
    lastSearchQuery = query;
    return SchemeListResponse(
      items: [
        GovernmentScheme.fromJson({
          'scheme_id': '1',
          'scheme_name': 'Farmers Support Scheme',
          'category': 'agriculture',
          'department': 'Agriculture',
          'matched_content': 'Support for farmers',
        }),
      ],
      total: 1,
      skip: 0,
      limit: limit,
    );
  }

  @override
  Future<GovernmentScheme> getScheme(String schemeId) async {
    detailCalls += 1;
    return _items.firstWhere((scheme) => scheme.id == schemeId);
  }
}

void main() {
  test('filters and sorts schemes correctly', () async {
    final provider = SchemeProvider(_FakeSchemeRepository());

    await provider.loadSchemes();
    await provider.setFilters(category: 'agriculture', state: 'Tamil Nadu');
    provider.setSort(SchemeSort.benefitAmountDesc);

    final filtered = provider.filteredSchemes;

    expect(filtered.length, 1);
    expect(filtered.first.schemeName, 'Farmers Support Scheme');
    expect(provider.filters.category, 'agriculture');
  });

  test('does not request more pages after the total is loaded', () async {
    final repository = _FakeSchemeRepository();
    final provider = SchemeProvider(repository);

    await provider.loadSchemes();
    await provider.loadSchemes(append: true);

    expect(repository.listCalls, 1);
    expect(provider.hasMore, isFalse);
  });

  test('debounces search requests and ignores short queries', () async {
    final repository = _FakeSchemeRepository();
    final provider = SchemeProvider(repository);

    await provider.search('fa');
    await Future<void>.delayed(const Duration(milliseconds: 450));
    expect(repository.searchCalls, 0);

    await provider.search('farm');
    await provider.search('farmer');
    await Future<void>.delayed(const Duration(milliseconds: 450));

    expect(repository.searchCalls, 1);
    expect(repository.lastSearchQuery, 'farmer');
    expect(provider.hasMore, isFalse);
  });

  test('loads full scheme details when search cache is partial', () async {
    final repository = _FakeSchemeRepository();
    final provider = SchemeProvider(repository);

    await provider.search('farmers');
    await Future<void>.delayed(const Duration(milliseconds: 450));
    final partial = provider.schemeById('1');
    expect(partial, isNotNull);
    expect(partial!.hasDetailFields, isFalse);

    final detail = await provider.loadSchemeDetail('1');

    expect(repository.detailCalls, 1);
    expect(detail?.eligibilitySummary, 'Farmer families only');
    expect(provider.schemeById('1')?.hasDetailFields, isTrue);
  });
}
