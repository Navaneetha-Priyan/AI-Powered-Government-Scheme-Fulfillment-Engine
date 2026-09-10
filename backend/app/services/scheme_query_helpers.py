"""Shared canonical-scheme resolution and query-expansion helpers.

Used by:
  * text_normalization_service  – recover scheme names the LLM dropped/hallucinated
  * voice_query_service         – expand generic queries with relevant scheme aliases
  * evaluate_voice_offline      – keep the retrieval metric consistent with the pipeline

The aliases here are evaluation/retrieval aids only; they do NOT change eligibility
rules or the production recommendation ranking beyond improving recall for generic
queries.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

# ── Romanized / Tanglish aliases → canonical catalog name ────────────────────
ROMANIZED_SCHEME_ALIASES: Dict[str, str] = {
    "pm kisan": "PM Kisan",
    "pmkisan": "PM Kisan",
    "pm-kisan": "PM Kisan",
    "pradhan mantri kisan": "PM Kisan",
    "pradhan mantri kisan samman nidhi": "PM Kisan",
    "kisan samman nidhi": "PM Kisan",
    "kisan samman": "PM Kisan",
    "samman nidhi": "PM Kisan",
    "pm fasal bima": "PM Fasal Bima",
    "pm fasal bima yojana": "PM Fasal Bima",
    "fasal bima": "PM Fasal Bima",
    "fasal bima yojana": "PM Fasal Bima",
    "pmfby": "PM Fasal Bima",
    "pradhan mantri fasal bima yojana": "PM Fasal Bima",
    "crop insurance": "PM Fasal Bima",
    "pm kusum": "PM Kusum",
    "pm-kusum": "PM Kusum",
    "pmkusum": "PM Kusum",
    "pradhan mantri kisan urja suraksha": "PM Kusum",
    "pm rkvy": "PM RKVY",
    "pm pkvy": "PM RKVY",
    "pm rkvy pkvy": "PM RKVY",
    "rkvy": "PM RKVY",
    "pkvy": "PM RKVY",
    "rashtriya krishi vikas yojana": "PM RKVY",
    "paramparagat krishi vikas yojana": "PM RKVY",
    "pmfme": "PMFME",
    "pm fme": "PMFME",
    "pm formalisation of micro food processing": "PMFME",
    "smam": "SMAM",
    "sub mission on agricultural mechanization": "SMAM",
    "midh": "MIDH",
    "mission for integrated development of horticulture": "MIDH",
}

# ── Tamil substrings (distinctive prefixes) → canonical catalog name ─────────
TAMIL_SCHEME_MARKERS: Dict[str, str] = {
    "கிசா": "PM Kisan",
    "பசல்": "PM Fasal Bima",
}

FARMER_SCHEME_ALIASES: List[str] = [
    "PM Kisan",
    "PM Fasal Bima",
    "PM RKVY",
    "PM Kusum",
    "PMFME",
    "SMAM",
]

KNOWN_SCHEME_OCCUPATIONS: Set[str] = {
    "farmer", "cultivator", "agricultural labourer", "farm worker",
    "landowner", "tenant", "student", "laborer", "labourer",
}


def _normalize_alias_key(text: str) -> str:
    """Lowercase, strip punctuation/extra-space for alias lookup."""
    if not text:
        return ""
    cleaned = ""
    for ch in text.lower():
        if ch.isalnum() or ch == " ":
            cleaned += ch
        else:
            cleaned += " "
    return " ".join(cleaned.split())


def detect_scheme_names_in_text(text: str) -> List[str]:
    """Return canonical scheme names detectable in *text* (any script)."""
    found: List[str] = []
    seen: Set[str] = set()

    def add(name: str) -> None:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            found.append(name)

    if not text:
        return found

    for marker, canonical in TAMIL_SCHEME_MARKERS.items():
        if marker in text:
            add(canonical)

    key = _normalize_alias_key(text)
    for alias, canonical in ROMANIZED_SCHEME_ALIASES.items():
        if alias in key:
            add(canonical)

    return found


def expand_query_for_occupation(
    query: str,
    occupation: Optional[str],
    entities: Optional[Dict[str, object]] = None,
) -> str:
    """Append canonical scheme aliases to a GENERIC query to improve recall.

    Only expands when the query does not already name a specific scheme and the
    occupation is explicitly farmer/agricultural.
    """
    if not query:
        query = ""

    entities = entities or {}
    existing_scheme = entities.get("scheme_name")
    if isinstance(existing_scheme, str) and existing_scheme.strip():
        return query

    already_present = detect_scheme_names_in_text(query)
    if already_present:
        return query

    occupation_norm = _normalize_alias_key(occupation or "")
    is_farmer_domain = (
        occupation_norm in KNOWN_SCHEME_OCCUPATIONS
        or any(tok in occupation_norm for tok in ("farm", "cultiv", "agri"))
    )

    if not is_farmer_domain:
        return query

    extras: List[str] = []
    query_key = _normalize_alias_key(query)
    for alias in FARMER_SCHEME_ALIASES:
        if _normalize_alias_key(alias) not in query_key:
            extras.append(alias)

    if extras:
        return f"{query} {' '.join(extras)}".strip()
    return query
