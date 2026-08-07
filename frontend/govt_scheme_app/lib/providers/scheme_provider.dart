import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/government_scheme.dart';
import '../repositories/scheme_repository.dart';

enum SchemeSort { relevance, nameAsc, recentlyUpdated, benefitAmountDesc }

class SchemeFilters {
  const SchemeFilters({
    this.category,
    this.state,
    this.department,
    this.beneficiaryType,
    this.eligibilityStatus,
  });

  final String? category;
  final String? state;
  final String? department;
  final String? beneficiaryType;
  final String? eligibilityStatus;

  SchemeFilters copyWith({
    String? category,
    String? state,
    String? department,
    String? beneficiaryType,
    String? eligibilityStatus,
  }) {
    return SchemeFilters(
      category: category ?? this.category,
      state: state ?? this.state,
      department: department ?? this.department,
      beneficiaryType: beneficiaryType ?? this.beneficiaryType,
      eligibilityStatus: eligibilityStatus ?? this.eligibilityStatus,
    );
  }
}

class SchemeProvider extends ChangeNotifier {
  SchemeProvider(this._repository);

  static const int _pageSize = 20;

  final SchemeRepository _repository;

  List<GovernmentScheme> _allSchemes = const [];
  List<GovernmentScheme> _visibleSchemes = const [];
  final Map<String, GovernmentScheme> _schemeCache = {};
  bool _isLoading = false;
  String? _errorMessage;
  bool _hasLoaded = false;
  String _query = '';
  SchemeFilters _filters = const SchemeFilters();
  SchemeSort _sort = SchemeSort.relevance;
  int _nextSkip = 0;
  bool _isLoadingMore = false;
  bool _hasMore = true;
  Timer? _searchDebounce;
  String? _selectedSchemeId;
  int _requestVersion = 0;

  List<GovernmentScheme> get schemes => _visibleSchemes;
  List<GovernmentScheme> get filteredSchemes => _visibleSchemes;
  bool get isLoading => _isLoading;
  bool get isLoadingMore => _isLoadingMore;
  String? get errorMessage => _errorMessage;
  bool get hasLoaded => _hasLoaded;
  String get query => _query;
  SchemeFilters get filters => _filters;
  SchemeSort get sort => _sort;
  bool get hasMore => _hasMore;
  String? get selectedSchemeId => _selectedSchemeId;
  GovernmentScheme? get selectedScheme => _selectedSchemeId == null ? null : _schemeCache[_selectedSchemeId];

  GovernmentScheme? schemeById(String schemeId) => _schemeCache[schemeId];

  Future<void> loadSchemes({bool refresh = false, bool append = false}) async {
    if (_isLoading || _isLoadingMore) {
      return;
    }

    if (refresh) {
      _nextSkip = 0;
      _hasMore = true;
      _errorMessage = null;
    }

    if (append && (!_hasMore || _query.isNotEmpty)) {
      return;
    }

    final requestVersion = ++_requestVersion;
    _searchDebounce?.cancel();

    if (append) {
      _isLoadingMore = true;
    } else {
      _isLoading = true;
      _errorMessage = null;
    }
    notifyListeners();

    try {
      final response = await _repository.listSchemes(
        skip: append ? _nextSkip : 0,
        limit: _pageSize,
        category: _filters.category,
        status: _filters.eligibilityStatus,
      );
      if (requestVersion != _requestVersion) {
        return;
      }

      final incoming = response.items;
      if (refresh || !append) {
        _allSchemes = incoming;
      } else {
        _allSchemes = [..._allSchemes, ...incoming];
      }
      _cacheSchemes(incoming);

      _nextSkip = response.skip + incoming.length;
      _hasMore = incoming.isNotEmpty && _nextSkip < response.total;
      _applyFiltersAndSort();
      _hasLoaded = true;
      _errorMessage = null;
    } catch (error) {
      if (requestVersion != _requestVersion) {
        return;
      }
      _errorMessage = error.toString();
      if (!refresh && !append && _allSchemes.isEmpty) {
        _visibleSchemes = const [];
      }
      rethrow;
    } finally {
      if (requestVersion == _requestVersion) {
        _isLoading = false;
        _isLoadingMore = false;
        notifyListeners();
      }
    }
  }

  Future<void> search(String value, {bool refresh = false}) async {
    _query = value.trim();
    _nextSkip = 0;
    _hasMore = true;
    final requestVersion = ++_requestVersion;
    _searchDebounce?.cancel();

    if (_query.isEmpty) {
      await loadSchemes(refresh: true);
      return;
    }

    if (_query.length < 3) {
      _hasMore = false;
      _applyFiltersAndSort();
      notifyListeners();
      return;
    }

    _searchDebounce = Timer(const Duration(milliseconds: 400), () async {
      try {
        _isLoading = true;
        notifyListeners();
        final response = await _repository.searchSchemes(_query, limit: _pageSize);
        if (requestVersion != _requestVersion) {
          return;
        }
        _allSchemes = response.items;
        _cacheSchemes(response.items);
        _applyFiltersAndSort();
        _hasLoaded = true;
        _hasMore = false;
        _errorMessage = null;
      } catch (error) {
        if (requestVersion != _requestVersion) {
          return;
        }
        _errorMessage = error.toString();
      } finally {
        if (requestVersion == _requestVersion) {
          _isLoading = false;
          notifyListeners();
        }
      }
    });
  }

  Future<void> setFilters({
    String? category,
    String? state,
    String? department,
    String? beneficiaryType,
    String? eligibilityStatus,
  }) async {
    _filters = SchemeFilters(
      category: _cleanFilterValue(category),
      state: _cleanFilterValue(state),
      department: _cleanFilterValue(department),
      beneficiaryType: _cleanFilterValue(beneficiaryType),
      eligibilityStatus: _cleanFilterValue(eligibilityStatus),
    );
    _applyFiltersAndSort();
    notifyListeners();
    await loadSchemes(refresh: true);
  }

  Future<void> clearFilters() async {
    _filters = const SchemeFilters();
    _applyFiltersAndSort();
    notifyListeners();
    await loadSchemes(refresh: true);
  }

  void setSort(SchemeSort sort) {
    _sort = sort;
    _applyFiltersAndSort();
    notifyListeners();
  }

  void selectScheme(String? schemeId) {
    _selectedSchemeId = schemeId;
    if (hasListeners) {
      notifyListeners();
    }
  }

  Future<GovernmentScheme?> loadSchemeDetail(String schemeId) async {
    selectScheme(schemeId);
    final cached = _schemeCache[schemeId];
    if (cached != null && cached.hasDetailFields) {
      return cached;
    }

    final requestVersion = ++_requestVersion;
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final scheme = await _repository.getScheme(schemeId);
      if (requestVersion != _requestVersion) {
        return _schemeCache[schemeId];
      }
      _cacheSchemes([scheme]);
      _hasLoaded = true;
      _errorMessage = null;
      return scheme;
    } catch (error) {
      if (requestVersion == _requestVersion) {
        _errorMessage = error.toString();
      }
      return null;
    } finally {
      if (requestVersion == _requestVersion) {
        _isLoading = false;
        notifyListeners();
      }
    }
  }

  void _applyFiltersAndSort() {
    var items = List<GovernmentScheme>.from(_allSchemes);

    if (_query.isNotEmpty) {
      final query = _query.toLowerCase();
      items = items.where((scheme) {
        final haystack = '${scheme.schemeName} ${scheme.description} ${scheme.department} ${scheme.category}'.toLowerCase();
        return haystack.contains(query);
      }).toList();
    }

    if (_filters.category != null && _filters.category!.isNotEmpty) {
      items = items.where((scheme) => scheme.category.toLowerCase() == _filters.category!.toLowerCase()).toList();
    }

    if (_filters.state != null && _filters.state!.isNotEmpty) {
      items = items.where((scheme) => (scheme.state ?? '').toLowerCase() == _filters.state!.toLowerCase()).toList();
    }

    if (_filters.department != null && _filters.department!.isNotEmpty) {
      items = items.where((scheme) => scheme.department.toLowerCase() == _filters.department!.toLowerCase()).toList();
    }

    if (_filters.beneficiaryType != null && _filters.beneficiaryType!.isNotEmpty) {
      items = items.where((scheme) => (scheme.description).toLowerCase().contains(_filters.beneficiaryType!.toLowerCase())).toList();
    }

    if (_filters.eligibilityStatus != null && _filters.eligibilityStatus!.isNotEmpty) {
      items = items.where((scheme) => scheme.status.toLowerCase() == _filters.eligibilityStatus!.toLowerCase()).toList();
    }

    items.sort((a, b) {
      switch (_sort) {
        case SchemeSort.nameAsc:
          return a.schemeName.toLowerCase().compareTo(b.schemeName.toLowerCase());
        case SchemeSort.recentlyUpdated:
          final aDate = a.updatedAt ?? a.createdAt;
          final bDate = b.updatedAt ?? b.createdAt;
          if (aDate == null && bDate == null) {
            return 0;
          }
          if (aDate == null) {
            return 1;
          }
          if (bDate == null) {
            return -1;
          }
          return bDate.compareTo(aDate);
        case SchemeSort.benefitAmountDesc:
          final aValue = _extractBenefitAmount(a.benefits);
          final bValue = _extractBenefitAmount(b.benefits);
          return bValue.compareTo(aValue);
        case SchemeSort.relevance:
          return 0;
      }
    });

    _visibleSchemes = items;
  }

  void _cacheSchemes(List<GovernmentScheme> schemes) {
    for (final scheme in schemes) {
      if (scheme.id.isNotEmpty) {
        _schemeCache[scheme.id] = scheme;
      }
    }
  }

  String? _cleanFilterValue(String? value) {
    final trimmed = value?.trim();
    return trimmed == null || trimmed.isEmpty ? null : trimmed;
  }

  int _extractBenefitAmount(String? value) {
    if (value == null || value.isEmpty) {
      return 0;
    }
    final match = RegExp(r'\d+').firstMatch(value);
    return int.tryParse(match?.group(0) ?? '') ?? 0;
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    super.dispose();
  }
}
