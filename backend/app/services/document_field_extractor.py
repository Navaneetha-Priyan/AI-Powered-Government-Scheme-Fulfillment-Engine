"""DocumentFieldExtractor — Phase 5/6/7/8: Raw Text → ExtractedDocumentData.

Converts the raw text produced by PDF text extraction or OCR into the same
normalized ``ExtractedDocumentData`` schema consumed by the existing Step 3
``DocumentProfileMapper``. This is intentionally deterministic (label-based +
regex parsing) — no LLM is used.

Pipeline::

    REAL PDF/OCR TEXT
        -> DocumentFieldExtractor      # THIS STEP
        -> ExtractedDocumentData
        -> DocumentProfileMapper       # existing Step 3
        -> ProfileEnrichmentService    # existing Step 4
        -> Database

Design rules:
- The document type is supplied explicitly by the upload request (Phase 4).
- Parsing is robust: labels are matched case-insensitively with flexible
  spacing/colon handling, not brittle ``text.split("Name:")[1]``.
- Values are normalized (Phase 7): currency → float, "2.5 Acres" → 2.5 + unit,
  "Male" → "male", "YES" → True, dates → ISO strings.
- Missing optional fields remain ``None``; nothing is ever fabricated (Phase 8).
- No business-rule inference: e.g. land area > 0 never becomes ``is_farmer``.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.exceptions.exceptions import (
    DocumentProcessingError,
    UnsupportedDocumentTypeError,
)
from app.schemas.citizen_profile import DocumentTypeEnum
from app.schemas.document_profile import ExtractedDocumentData

logger = get_logger(__name__)

# ─── Normalization helpers ────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(r"[₹Rs.\s,]+", re.IGNORECASE)
_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+")
_DATE_RE = re.compile(
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
)
_YES_WORDS = {"yes", "y", "true", "owned", "own", "agricultural", "farmer"}
_NO_WORDS = {"no", "n", "false", "not", "none", "rented", "lease", "leased"}


def _normalize_text(value: str) -> str:
    """Collapse whitespace and strip punctuation noise."""
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_lower(value: str) -> str:
    return _normalize_text(value).lower()


def _parse_money(value: str) -> Optional[float]:
    """Parse 'Rs. 72,000' / '₹85,000' / '72000' → 72000.0."""
    if not value:
        return None
    cleaned = _CURRENCY_RE.sub("", value)
    match = _NUMBER_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _parse_area(value: str) -> tuple[Optional[float], Optional[str]]:
    """Parse '2.5 acres' / '1.0 Acre' → (2.5, 'acres')."""
    if not value:
        return None, None
    match = _NUMBER_RE.search(value)
    if not match:
        return None, None
    try:
        number = float(match.group())
    except ValueError:
        return None, None
    lower = _normalize_lower(value)
    unit = "acres" if "acre" in lower else None
    return number, unit


def _parse_bool(value: str) -> Optional[bool]:
    """Parse 'YES'/'No'/'True'/'False' → bool. Returns None when ambiguous."""
    if not value:
        return None
    lower = _normalize_lower(value)
    if lower in _YES_WORDS:
        return True
    if lower in _NO_WORDS:
        return False
    return None


def _parse_date(value: str) -> Optional[str]:
    """Parse '12/04/1985' / '01-01-1985' → '1985-04-12' (ISO)."""
    if not value:
        return None
    match = _DATE_RE.search(value)
    if not match:
        return None
    day, month, year = match.groups()
    year_int = int(year)
    if year_int < 100:
        year_int += 2000
    try:
        return f"{year_int:04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        return None


def _parse_int(value: str) -> Optional[int]:
    if not value:
        return None
    match = _NUMBER_RE.search(value)
    if not match:
        return None
    try:
        return int(float(match.group()))
    except ValueError:
        return None


# ─── Label-based extraction ───────────────────────────────────────────────────

# Values that should never be treated as a real label value (document titles,
# parentheticals, separators).
_UNWANTED_VALUE_PREFIXES = ("(", ")", "-", "—", "·", ":", ";", ",")


def _extract_label(
    text: str,
    label: str,
    *,
    multiline: bool = False,
    max_chars: int = 200,
) -> Optional[str]:
    """Extract the value following ``label:`` in ``text``.

    Matching is line-anchored: a label only counts when it appears at the start
    of a line (after trimming leading whitespace). A colon is preferred; a
    space-separated value is accepted only when the value does not look like a
    document header (e.g. a parenthetical). This prevents "Farmer ID" inside a
    document title like "Government ... — Farmer ID (Test Document)" from being
    mistaken for a real field.
    """
    escaped = re.escape(label)
    colon_pattern = re.compile(
        rf"^\s*{escaped}\s*:\s*(.+)$",
        re.IGNORECASE,
    )
    colon_only_pattern = re.compile(
        rf"^\s*{escaped}\s*:\s*$",
        re.IGNORECASE,
    )
    space_pattern = re.compile(
        rf"^\s*{escaped}\s+(.+)$",
        re.IGNORECASE,
    )

    lines = text.splitlines()
    for i, line in enumerate(lines):
        match = colon_pattern.match(line)
        if not match:
            match = space_pattern.match(line)
        if match:
            raw = match.group(1).strip()
            if not raw:
                continue
            if raw.startswith(_UNWANTED_VALUE_PREFIXES):
                continue
            value = raw
            if not multiline:
                value = raw.split("\n", 1)[0].strip()
            else:
                value = raw[:max_chars]
            if value:
                return _normalize_text(value)
            continue

        # Label-only line: "Label:" with nothing after the colon.
        # The value is on the next non-empty line.
        if colon_only_pattern.match(line):
            value = _take_next_value(lines, i + 1, multiline, max_chars)
            if value:
                return value
    return None


def _take_next_value(
    lines: list[str], start: int, multiline: bool, max_chars: int
) -> Optional[str]:
    """Take the next non-empty line as a value, skipping lines that look like labels."""
    for j in range(start, len(lines)):
        next_line = lines[j].strip()
        if not next_line:
            continue
        # Skip if the next line looks like another label (ends with colon).
        if next_line.endswith(":"):
            break
        if next_line.startswith(_UNWANTED_VALUE_PREFIXES):
            continue
        if not multiline:
            value = next_line
        else:
            collected = [next_line]
            for k in range(j + 1, len(lines)):
                subsequent = lines[k].strip()
                if not subsequent:
                    break
                if subsequent.endswith(":"):
                    break
                collected.append(subsequent)
            value = " ".join(collected)[:max_chars]
        if value:
            return _normalize_text(value)
        break
    return None


def _extract_any_label(text: str, labels: list[str], **kwargs) -> Optional[str]:
    """Try multiple labels in order; return the first match."""
    for label in labels:
        value = _extract_label(text, label, **kwargs)
        if value:
            return value
    return None


# ─── Field extractors per document type ───────────────────────────────────────

def _extract_aadhaar(text: str) -> Dict[str, Any]:
    full_name = _extract_any_label(text, ["Name", "Full Name", "Applicant Name"])
    dob_raw = _extract_any_label(text, ["DOB", "Date of Birth", "Date Of Birth"])
    gender = _extract_any_label(text, ["Gender", "Sex"])
    address = _extract_any_label(text, ["Address"], multiline=True)
    village = _extract_any_label(text, ["Village"])
    taluk = _extract_any_label(text, ["Taluk", "Taluka"])
    district = _extract_any_label(text, ["District"])
    state = _extract_any_label(text, ["State"])
    pincode = _extract_any_label(text, ["Pincode", "PIN Code", "Pin Code"])

    fields: Dict[str, Any] = {
        "full_name": _normalize_text(full_name) if full_name else None,
        "date_of_birth": _parse_date(dob_raw) if dob_raw else None,
        "gender": _normalize_lower(gender) if gender else None,
        "address_line1": _normalize_text(address) if address else None,
        "village": _normalize_text(village) if village else None,
        "taluk": _normalize_text(taluk) if taluk else None,
        "district": _normalize_text(district) if district else None,
        "state": _normalize_text(state) if state else None,
        "pincode": _normalize_text(pincode) if pincode else None,
    }
    return fields


def _extract_income_certificate(text: str) -> Dict[str, Any]:
    holder = _extract_any_label(text, ["Name", "Holder Name", "Applicant Name"])
    income_raw = _extract_any_label(
        text, ["Annual Income", "Income", "Total Income", "Yearly Income"]
    )
    category = _extract_any_label(text, ["Income Category", "Category", "Economic Category"])
    fy = _extract_any_label(text, ["Financial Year", "Year"])

    return {
        "holder_name": _normalize_text(holder) if holder else None,
        "annual_income": _parse_money(income_raw) if income_raw else None,
        "income_category": _normalize_lower(category) if category else None,
        "financial_year": _normalize_text(fy) if fy else None,
    }


def _extract_land_record(text: str) -> Dict[str, Any]:
    owner = _extract_any_label(text, ["Owner", "Owner Name", "Name"])
    survey = _extract_any_label(text, ["Survey Number", "Survey No", "Survey No.", "Survey"])
    area_raw = _extract_any_label(text, ["Land Area", "Area", "Extent"])
    land_type = _extract_any_label(text, ["Land Type", "Type", "Classification"])
    village = _extract_any_label(text, ["Village"])
    taluk = _extract_any_label(text, ["Taluk", "Taluka"])
    district = _extract_any_label(text, ["District"])
    state = _extract_any_label(text, ["State"])
    ownership = _extract_any_label(text, ["Ownership", "Ownership Type", "Nature of Holding"])
    patta = _extract_any_label(text, ["Patta Number", "Patta No", "Patta No.", "Patta"])

    area, unit = _parse_area(area_raw) if area_raw else (None, None)

    return {
        "owner_name": _normalize_text(owner) if owner else None,
        "survey_number": _normalize_text(survey) if survey else None,
        "land_area": area,
        "unit": unit,
        "land_type": _normalize_lower(land_type) if land_type else None,
        "village": _normalize_text(village) if village else None,
        "taluk": _normalize_text(taluk) if taluk else None,
        "district": _normalize_text(district) if district else None,
        "state": _normalize_text(state) if state else None,
        "ownership_type": _normalize_lower(ownership) if ownership else None,
        "patta_number": _normalize_text(patta) if patta else None,
    }


def _extract_farmer_id(text: str) -> Dict[str, Any]:
    farmer_id = _extract_any_label(text, ["Farmer ID", "Farmer Id", "Farmer No", "Farmer Number"])
    holder = _extract_any_label(text, ["Farmer Name", "Holder Name", "Name"])
    occupation = _extract_any_label(text, ["Occupation", "Profession"])
    is_farmer_raw = _extract_any_label(text, ["Is Farmer", "Farmer Status", "Status"])

    return {
        "farmer_id": _normalize_text(farmer_id) if farmer_id else None,
        "holder_name": _normalize_text(holder) if holder else None,
        "is_farmer": _parse_bool(is_farmer_raw) if is_farmer_raw else None,
        "occupation": _normalize_text(occupation) if occupation else None,
    }


def _extract_ration_card(text: str) -> Dict[str, Any]:
    card_number = _extract_any_label(text, ["Card Number", "Ration Card No", "Ration Card Number", "Card No"])
    holder = _extract_any_label(text, ["Name", "Holder Name", "Head of Family"])
    card_type = _extract_any_label(text, ["Card Type", "Type", "Category"])
    family_size = _extract_any_label(text, ["Family Size", "Members", "No of Members", "Family Members"])
    district = _extract_any_label(text, ["District"])

    return {
        "card_number": _normalize_text(card_number) if card_number else None,
        "holder_name": _normalize_text(holder) if holder else None,
        "card_type": _normalize_lower(card_type) if card_type else None,
        "family_size": _parse_int(family_size) if family_size else None,
        "district": _normalize_text(district) if district else None,
    }


def _extract_caste_certificate(text: str) -> Dict[str, Any]:
    holder = _extract_any_label(text, ["Name", "Holder Name", "Applicant Name"])
    caste = _extract_any_label(text, ["Caste"])
    community = _extract_any_label(text, ["Community", "Category"])
    sub_caste = _extract_any_label(text, ["Sub Caste", "Sub-Caste"])
    religion = _extract_any_label(text, ["Religion"])
    authority = _extract_any_label(text, ["Issuing Authority", "Authority", "Issued By"])

    return {
        "holder_name": _normalize_text(holder) if holder else None,
        "caste": _normalize_text(caste) if caste else None,
        "community": _normalize_text(community) if community else None,
        "sub_caste": _normalize_text(sub_caste) if sub_caste else None,
        "religion": _normalize_text(religion) if religion else None,
        "issuing_authority": _normalize_text(authority) if authority else None,
    }


def _extract_residence_certificate(text: str) -> Dict[str, Any]:
    holder = _extract_any_label(text, ["Name", "Holder Name", "Applicant Name"])
    village = _extract_any_label(text, ["Village"])
    taluk = _extract_any_label(text, ["Taluk", "Taluka"])
    district = _extract_any_label(text, ["District"])
    state = _extract_any_label(text, ["State"])

    return {
        "holder_name": _normalize_text(holder) if holder else None,
        "village": _normalize_text(village) if village else None,
        "taluk": _normalize_text(taluk) if taluk else None,
        "district": _normalize_text(district) if district else None,
        "state": _normalize_text(state) if state else None,
    }


def _extract_disability_certificate(text: str) -> Dict[str, Any]:
    holder = _extract_any_label(text, ["Name", "Holder Name", "Applicant Name"])
    disabled_raw = _extract_any_label(text, ["Disabled", "Disability", "Status"])
    percentage = _extract_any_label(text, ["Disability Percentage", "Percentage", "Disability %"])

    return {
        "holder_name": _normalize_text(holder) if holder else None,
        "is_disabled": _parse_bool(disabled_raw) if disabled_raw else None,
        "disability_percentage": _parse_int(percentage) if percentage else None,
    }


# ─── Document type dispatch ───────────────────────────────────────────────────

_EXTRACTORS: Dict[DocumentTypeEnum, Any] = {
    DocumentTypeEnum.AADHAAR: _extract_aadhaar,
    DocumentTypeEnum.INCOME_CERTIFICATE: _extract_income_certificate,
    DocumentTypeEnum.LAND_RECORD: _extract_land_record,
    DocumentTypeEnum.FARMER_ID: _extract_farmer_id,
    DocumentTypeEnum.SMART_RATION_CARD: _extract_ration_card,
    DocumentTypeEnum.CASTE_CERTIFICATE: _extract_caste_certificate,
    DocumentTypeEnum.COMMUNITY_CERTIFICATE: _extract_caste_certificate,
    DocumentTypeEnum.RESIDENCE_CERTIFICATE: _extract_residence_certificate,
    DocumentTypeEnum.DISABILITY_CERTIFICATE: _extract_disability_certificate,
}


class DocumentFieldExtractor:
    """Converts raw document text into normalized ``ExtractedDocumentData``."""

    def extract(
        self,
        document_type: str,
        raw_text: str,
        document_id: Optional[str] = None,
    ) -> ExtractedDocumentData:
        """Extract normalized fields from ``raw_text`` for ``document_type``.

        ``document_type`` is the explicit type supplied by the upload request
        (e.g. ``"aadhaar"``, ``"land_record"``). Raises
        ``UnsupportedDocumentTypeError`` for unknown types and
        ``DocumentProcessingError`` when the text is empty.
        """
        if not raw_text or not raw_text.strip():
            raise DocumentProcessingError(
                reason="No text was extracted from the document",
                document_type=document_type,
                document_id=document_id or "",
            )

        canonical = self._resolve_type(document_type)
        extractor = _EXTRACTORS.get(canonical)
        if extractor is None:
            raise UnsupportedDocumentTypeError(document_type=document_type)

        fields = extractor(raw_text)
        return ExtractedDocumentData(
            document_type=canonical,
            fields=fields,
            document_id=document_id,
        )

    @staticmethod
    def _resolve_type(document_type: str) -> DocumentTypeEnum:
        """Resolve an explicit type string to the canonical enum."""
        if not document_type:
            raise UnsupportedDocumentTypeError(document_type="unknown")
        normalized = document_type.strip().lower()
        try:
            return DocumentTypeEnum(normalized)
        except ValueError:
            raise UnsupportedDocumentTypeError(document_type=document_type)