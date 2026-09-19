/// Conservative validation for citizen-facing scheme presentation text.
///
/// Mirrors the backend `scheme_presentation_service.is_valid_presentation_text`
/// so the API and the app agree on what counts as corrupted PDF/OCR
/// extraction. A field that fails validation is *never* rendered and is never
/// replaced by raw PDF/RAG content — callers hide the section instead.
///
/// Deliberately conservative: legitimate Indian-language text (Tamil,
/// Devanagari, ...) is never rejected just for being non-ASCII. All symbol and
/// token heuristics below are ASCII-scoped for exactly that reason.
library;

/// Safe fallback shown when no clean description exists. Raw PDF extraction is
/// never used as a fallback.
const String schemeAboutFallback =
    'Information about this scheme is being prepared.';

/// Symbols that never appear in curated citizen-facing prose but are common in
/// broken extraction. Parentheses/brackets, `&`, `%`, `/`, `-` and em dashes
/// are intentionally allowed — real scheme text uses them.
final RegExp _unusualSymbols = RegExp(r'[{}|\\^`]');

/// Four or more consecutive *ASCII* punctuation characters ("^,,-"). The class
/// is ASCII-only so Tamil/Devanagari text can never match it.
final RegExp _asciiSymbolRun = RegExp(r'[!-/:-@\[-`{-~]{4,}');

/// Classic OCR letter substitutions that are never valid English words.
const List<String> _ocrMisspellings = <String>[
  'govemment',
  'govenment',
  'lndla',
  'lndia',
  'secrotary',
  'deparment',
  'ministy',
  'minisrty',
];

/// PDF extraction artifacts: page markers, letterheads, department boilerplate,
/// URLs, pincodes, file names.
final RegExp _pdfNoisePattern = RegExp(
  r'page\s*no\.?\s*\d+|pages?\s*\d+|f\.?\s*no\b|file\s*no\b|'
  r'government of india|ministry of|department of|operational guidelines|'
  r'krishi bhawan|shastri bhawan|newdelhi|new delhi|pin\s*code|'
  r'@gov\.in|@nic\.in|www\.|\.pdf\b',
  caseSensitive: false,
);

/// Control characters other than tab/newline/carriage-return.
final RegExp _controlChars = RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F]');

const int _maxDotsPerToken = 2;
const int _defaultMaxLength = 400;

/// True when [text] is unusable as citizen-facing presentation content.
///
/// Anything much longer than [maxLength] is almost certainly a raw PDF dump
/// rather than curated prose.
bool isPresentationNoise(String? text, {int maxLength = 400}) {
  final raw = text;
  if (raw == null || raw.trim().isEmpty) return true;
  if (raw.trim().length > maxLength) return true;
  if (_controlChars.hasMatch(raw)) return true;
  if (raw.contains('\uFFFD')) return true;
  if (_unusualSymbols.hasMatch(raw)) return true;
  if (_asciiSymbolRun.hasMatch(raw)) return true;

  final lower = raw.toLowerCase();
  for (final misspelling in _ocrMisspellings) {
    if (lower.contains(misspelling)) return true;
  }
  if (_pdfNoisePattern.hasMatch(raw)) return true;

  // A leftover "None" / "N/A" placeholder is not content.
  final compact = lower.replaceAll(RegExp(r'[\s,.]'), '');
  if (compact.isEmpty) return true;
  if (const {'none', 'na', 'n/a', 'nil', 'tbd', 'n', '-', '--'}.contains(compact)) {
    return true;
  }

  final tokens = raw.split(RegExp(r'\s+'));
  var garbled = 0;
  for (final token in tokens) {
    if ('.'.allMatches(token).length > _maxDotsPerToken) return true;
    if (_isGarbledToken(token)) garbled++;
  }
  if (garbled > 0 && garbled / tokens.length > 0.3) return true;
  return false;
}

/// A token with no letter/digit at all ("^,,-", "---") is extraction junk.
/// Non-ASCII characters count as letters so Indian scripts are never flagged.
bool _isGarbledToken(String token) {
  if (token.length <= 2) return false;
  for (final rune in token.runes) {
    final isAsciiAlnum = (rune >= 0x30 && rune <= 0x39) ||
        (rune >= 0x41 && rune <= 0x5A) ||
        (rune >= 0x61 && rune <= 0x7A);
    if (isAsciiAlnum || rune > 0x7F) return false;
  }
  return true;
}

/// Returns a citizen-safe version of [raw], or null when it is corrupted /
/// extraction noise / longer than [max] (a raw PDF dump).
String? cleanPresentationText(String? raw, {int max = _defaultMaxLength}) {
  final value = raw;
  if (value == null) return null;
  final collapsed = value.replaceAll(RegExp(r'\s+'), ' ').trim();
  if (collapsed.isEmpty) return null;
  if (isPresentationNoise(collapsed)) return null;
  if (collapsed.length > max) return null;
  return collapsed;
}

/// Validate every item in a citizen-facing list. Invalid items are discarded —
/// they are never passed through or replaced by raw content.
List<String> cleanPresentationList(
  Iterable<String>? items, {
  int max = 300,
}) {
  final out = <String>[];
  final seen = <String>{};
  for (final item in items ?? const <String>[]) {
    final clean = cleanPresentationText(item, max: max);
    if (clean == null || seen.contains(clean)) continue;
    seen.add(clean);
    out.add(clean);
  }
  return out;
}