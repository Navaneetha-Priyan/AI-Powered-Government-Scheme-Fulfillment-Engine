"""Loader for the canonical structured eligibility catalogue.

The catalogue is a foundation artifact: it records PDF-derived eligibility
rules, evidence requirements, and profile-field coverage without replacing the
existing recommendation engine.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from app.models.scheme_eligibility import SchemeEligibilityCatalogueEntry


CATALOGUE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "eligibility_rules"
    / "catalog.json"
)


@lru_cache(maxsize=1)
def load_eligibility_catalogue() -> List[SchemeEligibilityCatalogueEntry]:
    """Load and validate the structured eligibility catalogue."""
    with CATALOGUE_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [
        SchemeEligibilityCatalogueEntry.model_validate(item)
        for item in payload.get("schemes", [])
    ]


def get_catalogue_entry(scheme_id: str) -> Optional[SchemeEligibilityCatalogueEntry]:
    """Return one catalogue entry by scheme id, case-insensitively."""
    normalized = (scheme_id or "").strip().lower()
    for entry in load_eligibility_catalogue():
        if entry.scheme_id.lower() == normalized:
            return entry
    return None


def get_catalogue_entry_for_scheme(scheme: Any) -> Optional[SchemeEligibilityCatalogueEntry]:
    """Return a catalogue entry for a database GovernmentScheme-like object."""
    if not scheme:
        return None

    scheme_id = getattr(scheme, "scheme_id", None) or getattr(scheme, "id", None)
    by_id = get_catalogue_entry(str(scheme_id or ""))
    if by_id:
        return by_id

    normalized_name = _normalize_scheme_name(getattr(scheme, "scheme_name", "") or "")
    if not normalized_name:
        return None

    for entry in load_eligibility_catalogue():
        candidates = {
            _normalize_scheme_name(entry.scheme_id),
            _normalize_scheme_name(entry.scheme_name),
            _normalize_scheme_name(entry.pdf_filename.replace(".pdf", "")),
        }
        candidates.update(
            _normalize_scheme_name(name.replace(".pdf", ""))
            for name in entry.alternate_pdf_filenames
        )
        stripped_name = _strip_catalogue_suffixes(normalized_name)
        stripped_candidates = {_strip_catalogue_suffixes(candidate) for candidate in candidates}
        if normalized_name in candidates or stripped_name in stripped_candidates:
            return entry

    return None


def _normalize_scheme_name(value: str) -> str:
    """Normalize scheme names and PDF filenames for deterministic lookup."""
    normalized = re.sub(r"[_\-]+", " ", value.lower())
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _strip_catalogue_suffixes(value: str) -> str:
    """Drop generic document-title words from a normalized scheme name."""
    tokens = [
        token
        for token in value.split()
        if token not in {"operational", "guidelines", "guideline", "scheme", "document", "documents", "pdf"}
    ]
    return " ".join(tokens).strip()
