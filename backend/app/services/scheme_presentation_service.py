"""User-facing scheme presentation metadata.

Architectural separation:

1. SOURCE / RAG CONTENT — the original scheme PDF text, extracted chunks and
   ChromaDB/RAG data. This stays untouched and remains the only source for
   source-grounded retrieval answers.

2. USER-FACING SCHEME INFORMATION — this module. Curated presentation metadata
   (``backend/data/scheme_presentation.json``) keyed by the *existing* canonical
   catalogue scheme_ids (``backend/data/eligibility_rules/catalog.json``).
   It carries a clean display name, a short citizen-friendly description and
   short bullet benefits, all grounded in the referenced scheme PDFs.

This module never feeds RAG and never feeds the eligibility evaluator. It is
purely for presentation surfaces (recommendation cards, scheme detail pages,
and later concise voice responses).

Noise policy: obvious PDF-extraction artifacts (page markers, letterhead
fragments, OCR garbage, raw document section labels) must never surface here.
When no clean, source-backed content exists the caller receives the safe
fallback text instead of raw extraction.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.services.eligibility_catalog_service import get_catalogue_entry_for_scheme

logger = logging.getLogger(__name__)

PRESENTATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "scheme_presentation.json"
)

# Safe citizen-facing fallback. Raw PDF extraction is NEVER used as fallback.
FALLBACK_DESCRIPTION = "Information about this scheme is being prepared."

# Maximum length of a citizen-facing summary. Anything much longer is almost
# certainly a raw PDF dump rather than a curated summary.
_MAX_SUMMARY_LENGTH = 400
_MAX_BULLET_LENGTH = 300

# Text-extraction noise that must never be shown to citizens.
_NOISE_PATTERNS = [
    re.compile(r"\bpages?\s*\d+", re.IGNORECASE),
    re.compile(r"^page\s*no\.?\s*\d+", re.IGNORECASE),
    re.compile(r"\bf\.?\s*no\.?\s*", re.IGNORECASE),
    re.compile(r"\bfile\s*no\.?\s*", re.IGNORECASE),
    re.compile(r"&to&p|govemment|govemment of india", re.IGNORECASE),
    re.compile(r"\bgovernment of india\b", re.IGNORECASE),
    re.compile(r"\bministry of\b|\bdepartment of\b", re.IGNORECASE),
    re.compile(r"\boperational guidelines\b", re.IGNORECASE),
    re.compile(
        r"\bkrishi bhawan|shastri bhawan|new delhi\s*-?\s*1100\d\d", re.IGNORECASE
    ),
    re.compile(r"@gov\.in|@nic\.in|www\.|http", re.IGNORECASE),
    re.compile(r"\b(pin\s*code|pincode)\b", re.IGNORECASE),
    re.compile(r"\.(pdf|docx?|xlsx?)\b", re.IGNORECASE),
]

# Control characters (except common whitespace) that indicate corrupted text.
# This catches mojibake/OCR garbage that slips past pattern matching.
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Mojibake/garbled-Unicode indicators: sequences of control chars or
# replacement chars that suggest broken encoding.
_MOJIBAKE_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\uFFFD]+")

# Heuristic: a single word that is almost entirely non-letter, non-digit,
# non-space characters — typical of OCR control-character garbage.
def _is_garbled_word(word: str) -> bool:
    if not word:
        return False
    alnum = sum(1 for c in word if c.isalnum())
    return alnum == 0 and len(word) > 2


# ── Corrupted / mojibake detection ──────────────────────────────────────────
# Symbols that essentially never occur in curated citizen-facing prose but are
# extremely common in broken PDF/OCR extraction ("{r*yr", spreadsheet leftovers,
# "&TO&P)" style fragments).  Everything else — including ()[] and ``&`` / ``%``
# / ``/`` / ``-`` / em dashes — is treated as legitimate punctuation because it
# appears in real scheme text ("Agriculture & Farmers Welfare", "SC/ST",
# "(Housing for All — Urban)").
_UNUSUAL_SYMBOLS = frozenset("{}|\\^`")

# Four or more consecutive non-word, non-space characters ("^,,-", "| *')").
# Legitimate prose peaks far below this ("Rs. 6,000/-", "i.e.,", "...", "(a)").
_SYMBOL_RUN_PATTERN = re.compile(r"[^\w\s]{4,}")

# Classic OCR letter substitutions that are never valid English words.  These
# appear verbatim in the corrupted extraction that prompted this hardening.
_OCR_MISSPELLINGS = (
    "govemment",
    "govenment",
    "lndla",
    "lndia",
    "secrotary",
    "deparment",
    "ministy",
    "minisrty",
)

# Tokens with more than two dots are extraction garbage ("er6.q.qq.").
_MAX_DOTS_PER_TOKEN = 2


def _looks_corrupted(text: str) -> bool:
    """True when text shows signs of broken extraction/encoding.

    Conservative on purpose: legitimate Indian-language Unicode (Tamil,
    Devanagari, ...) and legitimate punctuation are never rejected simply for
    being non-ASCII.
    """
    if not text:
        return False
    # Braces, pipes, backslashes, backticks, carets: never curated prose.
    if any(char in _UNUSUAL_SYMBOLS for char in text):
        return True
    if _SYMBOL_RUN_PATTERN.search(text):
        return True
    lowered = text.lower()
    if any(misspelling in lowered for misspelling in _OCR_MISSPELLINGS):
        return True
    tokens = text.split()
    if not tokens:
        return False
    for token in tokens:
        if token.count(".") > _MAX_DOTS_PER_TOKEN:
            return True
    garbled = sum(1 for token in tokens if _is_garbled_word(token))
    if garbled > 0 and garbled / len(tokens) > 0.3:
        return True
    return False


def is_extraction_noise(text: Any) -> bool:
    """Return True when the text is an obvious PDF/OCR extraction artifact.

    Also rejects giant paragraphs copied straight from PDF extraction —
    curated user-facing summaries are short by design.
    """
    if text is None:
        return True
    normalized = re.sub(r"\s+", " ", str(text)).strip()
    if not normalized:
        return True
    if len(normalized) > _MAX_SUMMARY_LENGTH:
        return True
    compact = normalized.replace(" ", "").replace(".", "").lower()
    if compact in {"none", "na", "n/a", "nil", "tbd", "null", "n", "-", "--"}:
        return True
    for pattern in _NOISE_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def is_valid_presentation_text(text: Any) -> bool:
    """Validate that text is safe for citizen-facing presentation.

    Rejects:
    - None / empty / whitespace-only text
    - Control characters (mojibake/OCR garbage indicators)
    - Unicode replacement characters (U+FFFD)
    - Corrupted/mojibake extraction (unusual symbol runs, OCR misspellings,
      token-level garbage)
    - PDF extraction noise (page markers, letterheads, OCR fragments)
    - Giant paragraphs (raw PDF dumps)

    Does NOT reject legitimate non-ASCII Indian-language Unicode —
    Devanagari, Tamil, Telugu, etc. are permitted.
    """
    if text is None:
        return False
    raw = str(text)
    # Control characters (except tab/newline/carriage-return) → corrupted.
    if _CONTROL_CHAR_PATTERN.search(raw):
        return False
    # Unicode replacement character → broken encoding.
    if "\ufffd" in raw:
        return False
    # Braces/symbol runs/OCR misspellings/garbled tokens → corrupted.
    if _looks_corrupted(raw):
        return False
    # Delegate to the established noise patterns (page markers, etc.).
    if is_extraction_noise(raw):
        return False
    return True


@lru_cache(maxsize=1)
def load_scheme_presentation() -> dict[str, dict[str, Any]]:
    """Load and validate the structured presentation metadata.

    Entries are validated against the canonical eligibility catalogue: only
    scheme_ids that exist there are returned (no second identity system).
    """
    with PRESENTATION_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
        out: dict[str, dict[str, Any]] = {}
    for item in payload.get("schemes", []):
        scheme_id = str(item.get("scheme_id", "")).strip()
        if not scheme_id:
            continue
        benefits = [
            str(benefit).strip()
            for benefit in (item.get("benefits") or [])
            if str(benefit).strip()
        ]
        who_it_is_for = (item.get("who_it_is_for") or "").strip()
        eligibility_summary = (item.get("eligibility_summary") or "").strip()
        documents = [
            str(doc).strip()
            for doc in (item.get("documents") or [])
            if str(doc).strip()
        ]
        application = [
            str(step).strip()
            for step in (item.get("application") or [])
            if str(step).strip()
        ]
        out[scheme_id] = {
            "display_name": str(item.get("display_name") or "").strip(),
            "short_description": str(item.get("short_description") or "").strip(),
            "benefits": benefits,
            "needs_review": bool(item.get("needs_review", False)),
            "benefits_needs_review": bool(item.get("benefits_needs_review", False)),
            "short_description_needs_review": bool(
                item.get("short_description_needs_review", False)
            ),
            "who_it_is_for_needs_review": bool(
                item.get("who_it_is_for_needs_review", False)
            ),
            "eligibility_summary_needs_review": bool(
                item.get("eligibility_summary_needs_review", False)
            ),
            "source_document": str(item.get("source_document") or "").strip(),
            "who_it_is_for": who_it_is_for,
            "eligibility_summary": eligibility_summary,
            "documents": documents,
            "application": application,
        }
    # Guard against drift between presentation ids and the canonical catalogue.
    try:
        from app.services.eligibility_catalog_service import (
            load_eligibility_catalogue,
        )

        catalogue_ids = {entry.scheme_id for entry in load_eligibility_catalogue()}
        unknown = set(out) - catalogue_ids
        if unknown:
            logger.warning(
                "Presentation metadata has scheme_ids not in the canonical "
                "catalogue (ignored): %s",
                sorted(unknown),
            )
            for scheme_id in unknown:
                out.pop(scheme_id, None)
    except Exception:  # pragma: no cover - catalogue load failure is non-fatal here
        logger.warning("Could not cross-check presentation ids against catalogue")
    return out


def get_presentation_by_scheme_id(scheme_id: str) -> Optional[dict[str, Any]]:
    """Return the raw presentation entry for a canonical scheme_id."""
    normalized = (scheme_id or "").strip()
    if not normalized:
        return None
    entries = load_scheme_presentation()
    if normalized in entries:
        return entries[normalized]
    lowered = normalized.lower()
    for entry_id, entry in entries.items():
        if entry_id.lower() == lowered:
            return entry
    return None



def resolve_presentation_for_scheme(scheme: Any) -> Optional[dict[str, Any]]:
    """Resolve a presentation entry for a DB scheme-like object.

    Uses the existing canonical eligibility catalogue identity mapping —
    no second scheme identity system is created.
    """
    entry = get_catalogue_entry_for_scheme(scheme)
    if entry is not None:
        presentation = get_presentation_by_scheme_id(entry.scheme_id)
        if presentation is not None:
            return presentation
    # Direct fallback: presentation keys mirror catalogue scheme_ids, which are
    # also stored on the DB scheme for catalogue-backed records.
    return get_presentation_by_scheme_id(str(getattr(scheme, "scheme_id", "") or ""))


def clean_benefit_bullets(benefits: list[str]) -> list[str]:
    """Return only citizen-safe benefit bullets (noise rejected, capped)."""
    out: list[str] = []
    for benefit in benefits:
        if not is_valid_presentation_text(benefit) or len(benefit) > _MAX_BULLET_LENGTH:
            continue
        out.append(benefit.strip())
    return out


def _validate_text_list(items: list[str], max_len: int = _MAX_BULLET_LENGTH) -> list[str]:
    """Validate every item in a citizen-facing text list. Invalid items are
    discarded (never passed through)."""
    out: list[str] = []
    for item in items:
        if not is_valid_presentation_text(item) or len(item) > max_len:
            continue
        out.append(item.strip())
    return out


def presentation_for_scheme(scheme: Any) -> dict[str, Any]:
    """Citizen-facing presentation fields for one scheme, always safe.

    Returns a dict with:
      display_name, short_description, benefits (list[str]), needs_review,
      who_it_is_for, eligibility_summary, documents, application
    Missing/noisy/unreviewed content is replaced by the safe fallback —
    raw PDF extraction is never returned.
    """
    entry = resolve_presentation_for_scheme(scheme) if scheme is not None else None
    if entry is None:
        return {
            "display_name": None,
            "short_description": FALLBACK_DESCRIPTION,
            "benefits": [],
            "needs_review": True,
            "who_it_is_for": None,
            "eligibility_summary": None,
            "eligibility_summary_needs_review": True,
            "documents": [],
            "application": [],
        }
    needs_review = bool(entry["needs_review"])
    # short_description: validate before returning; fall back to safe text.
    short_description: Optional[str] = None
    raw_short = entry["short_description"]
    if (
        not needs_review
        and not entry.get("short_description_needs_review")
        and raw_short
        and is_valid_presentation_text(raw_short)
    ):
        short_description = raw_short.strip()
    if short_description is None:
        short_description = FALLBACK_DESCRIPTION
        needs_review = True
    # benefits: validate each bullet individually; never fall back to raw.
    if needs_review or entry["benefits_needs_review"]:
        benefits = []
    else:
        benefits = clean_benefit_bullets(entry["benefits"])
    # who_it_is_for: validate before returning; a field explicitly marked for
    # review is withheld rather than shown half-verified.
    who_it_is_for = entry.get("who_it_is_for") or None
    if who_it_is_for is not None and (
        entry.get("who_it_is_for_needs_review")
        or not is_valid_presentation_text(who_it_is_for)
    ):
        who_it_is_for = None
    eligibility_summary = entry.get("eligibility_summary") or None
    if eligibility_summary is not None and not is_valid_presentation_text(
        eligibility_summary
    ):
        eligibility_summary = None
    # documents, application: validate each item individually.
    documents = _validate_text_list(entry.get("documents") or [])
    application = _validate_text_list(entry.get("application") or [])
    # display_name: a corrupted display name must never reach a heading.
    display_name = entry.get("display_name") or None
    if display_name is not None and not is_valid_presentation_text(display_name):
        display_name = None
    return {
        "display_name": display_name,
        "short_description": short_description,
        "benefits": benefits,
        "needs_review": needs_review
        or bool(entry["benefits_needs_review"] and not benefits),
        "who_it_is_for": who_it_is_for,
        "eligibility_summary": eligibility_summary,
        "eligibility_summary_needs_review": bool(
            entry.get("eligibility_summary_needs_review")
        ),
        "documents": documents,
        "application": application,
    }
