"""DocumentProfileExtractor - Step 2: Document → ExtractedDocumentData.

Reads the structured ``doc_metadata`` JSON attached to a ``GovernmentDocument``
(created in Step 1) and normalizes it into a standards-based
``ExtractedDocumentData`` representation.

Pipeline (kept strictly separated so later steps stay decoupled)::

    GovernmentDocument
        -> DocumentProfileExtractor      # THIS STEP
        -> ExtractedDocumentData
        -> [future Step 3] DocumentProfileMapper
        -> [future Step 4] ProfileEnrichmentService

The extractor is intentionally READ-ONLY:
- It never writes to the database.
- It does not know how ``citizen_profiles`` or ``land_records`` are updated.
- It performs NO OCR / PDF / image parsing — it only interprets already
  structured JSON metadata.
- It performs NO document → profile mapping (e.g. it never turns
  ``land_area > 0`` into ``is_farmer = true``). That belongs to Step 3.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.exceptions.exceptions import (
    DocumentExtractionError,
    DocumentMetadataInvalidError,
    UnsupportedDocumentTypeError,
)
from app.schemas.citizen_profile import DocumentTypeEnum
from app.schemas.document_profile import ExtractedDocumentData

logger = get_logger(__name__)

# Canonical list of document types the extractor understands for Step 2.
# The Mock DigiLocker data (Step 1) emits a few metadata-level type labels that
# map onto the shared DocumentTypeEnum vocabulary. We reuse the existing enum
# instead of inventing a second taxonomy.
_SUPPORTED_TYPES = {
    DocumentTypeEnum.AADHAAR,
    DocumentTypeEnum.SMART_RATION_CARD,
    DocumentTypeEnum.INCOME_CERTIFICATE,
    DocumentTypeEnum.COMMUNITY_CERTIFICATE,
    DocumentTypeEnum.CASTE_CERTIFICATE,
    DocumentTypeEnum.RESIDENCE_CERTIFICATE,
    DocumentTypeEnum.LAND_RECORD,
    DocumentTypeEnum.DISABILITY_CERTIFICATE,
    DocumentTypeEnum.FARMER_ID,
}

# Metadata type-label → canonical DocumentTypeEnum. Step 1 documents use a
# couple of shorthand labels ("ration_card", "caste_certificate") that need to
# be resolved to the canonical enum value.
_TYPE_ALIASES: Dict[str, DocumentTypeEnum] = {
    "aadhaar": DocumentTypeEnum.AADHAAR,
    "ration_card": DocumentTypeEnum.SMART_RATION_CARD,
    "smart_ration_card": DocumentTypeEnum.SMART_RATION_CARD,
    "income_certificate": DocumentTypeEnum.INCOME_CERTIFICATE,
    "community_certificate": DocumentTypeEnum.COMMUNITY_CERTIFICATE,
    "caste_certificate": DocumentTypeEnum.CASTE_CERTIFICATE,
    "residence_certificate": DocumentTypeEnum.RESIDENCE_CERTIFICATE,
    "land_record": DocumentTypeEnum.LAND_RECORD,
    "disability_certificate": DocumentTypeEnum.DISABILITY_CERTIFICATE,
    "farmer_id": DocumentTypeEnum.FARMER_ID,
    "birth_certificate": DocumentTypeEnum.BIRTH_CERTIFICATE,
}

# The normalized fields a given document type is expected to expose. Absent
# optional fields are preserved with a None value (never fabricated).
_FIELD_SPECS: Dict[DocumentTypeEnum, List[str]] = {
    DocumentTypeEnum.AADHAAR: [
        "full_name",
        "date_of_birth",
        "gender",
        "address_line1",
        "village",
        "taluk",
        "district",
        "state",
        "pincode",
    ],
    DocumentTypeEnum.SMART_RATION_CARD: [
        "card_number",
        "holder_name",
        "card_type",
        "family_size",
        "district",
    ],
    DocumentTypeEnum.INCOME_CERTIFICATE: [
        "holder_name",
        "annual_income",
        "income_category",
        "financial_year",
    ],
    DocumentTypeEnum.COMMUNITY_CERTIFICATE: [
        "holder_name",
        "caste",
        "community",
        "sub_caste",
        "religion",
        "issuing_authority",
    ],
    DocumentTypeEnum.CASTE_CERTIFICATE: [
        "holder_name",
        "caste",
        "community",
        "sub_caste",
        "religion",
        "issuing_authority",
    ],
    DocumentTypeEnum.RESIDENCE_CERTIFICATE: [
        "holder_name",
        "village",
        "taluk",
        "district",
        "state",
    ],
    DocumentTypeEnum.LAND_RECORD: [
        "owner_name",
        "survey_number",
        "land_area",
        "unit",
        "land_type",
        "village",
        "taluk",
        "district",
        "state",
        "ownership_type",
        "patta_number",
    ],
    DocumentTypeEnum.DISABILITY_CERTIFICATE: [
        "holder_name",
        "is_disabled",
        "disability_percentage",
    ],
    DocumentTypeEnum.FARMER_ID: [
        "farmer_id",
        "holder_name",
        "is_farmer",
        "occupation",
    ],
}


class DocumentProfileExtractor:
    """Extracts normalized structured data from a GovernmentDocument's metadata.

    Two entry points are provided:

    - ``extract(document)``        — accepts a ``GovernmentDocument`` (or any
      object exposing ``doc_metadata`` and ``id``) and preserves the document id.
    - ``extract_from_metadata(metadata)`` — accepts the raw metadata directly
      (``str`` JSON, ``dict``, or ``None``) and remains fully
      database/object-agnostic (document_id = None).
    """

    def __init__(self) -> None:
        self.supported_types = set(_SUPPORTED_TYPES)

    # ── Public API ────────────────────────────────────────────────────────

    def extract(self, document: Any) -> ExtractedDocumentData:
        """Extract structured data from a GovernmentDocument object."""
        document_id: Optional[str] = None
        try:
            document_id = getattr(document, "id", None)
        except Exception:  # defensive: id access must never break extraction
            document_id = None

        if document is None:
            raise DocumentExtractionError(
                "No document provided to extract", document_id=document_id or ""
            )

        metadata = getattr(document, "doc_metadata", None)

        result = self.extract_from_metadata(metadata)
        if document_id:
            # Preserve provenance when we have it (document-aware path only).
            return result.model_copy(update={"document_id": document_id})
        return result

    def extract_from_metadata(self, metadata: Any) -> ExtractedDocumentData:
        """Extract structured data from raw document metadata.

        ``metadata`` may be:
        - a JSON string (as stored in ``GovernmentDocument.doc_metadata``)
        - an already-parsed ``dict`` (e.g. for callers that pre-parsed it)
        - ``None`` (missing metadata)

        Raises controlled exceptions on malformed/unknown input.
        """
        parsed = self._parse_metadata(metadata)
        doc_type = self._resolve_document_type(parsed)
        fields = self._normalize_fields(doc_type, parsed)
        return ExtractedDocumentData(document_type=doc_type, fields=fields)

    # ── Parsing ───────────────────────────────────────────────────────────

    def _parse_metadata(self, metadata: Any) -> Dict[str, Any]:
        """Safely coerce metadata into a dict.

        Returns an empty dict when metadata is missing so callers get a clear,
        controlled missing-data error rather than an internal crash.
        """
        if metadata is None:
            raise DocumentMetadataInvalidError("Document metadata is missing")

        if isinstance(metadata, dict):
            return metadata

        if isinstance(metadata, str):
            stripped = metadata.strip()
            if not stripped:
                raise DocumentMetadataInvalidError("Document metadata is empty")
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                logger.warning("Document metadata is not valid JSON: %s", exc)
                raise DocumentMetadataInvalidError(
                    "Document metadata is not valid JSON"
                ) from exc
            if not isinstance(parsed, dict):
                raise DocumentMetadataInvalidError(
                    "Document metadata must be a JSON object"
                )
            return parsed

        # Non-str/dict metadata (unexpected type).
        raise DocumentMetadataInvalidError(
            f"Unsupported metadata type: {type(metadata).__name__}"
        )

    def _resolve_document_type(self, parsed: Dict[str, Any]) -> DocumentTypeEnum:
        """Resolve and validate the canonical document type from metadata."""
        raw_type = parsed.get("document_type")
        if raw_type is None:
            raise DocumentMetadataInvalidError("Document metadata is missing 'document_type'")

        if not isinstance(raw_type, str):
            raise DocumentMetadataInvalidError("Document metadata 'document_type' must be a string")

        raw_type = raw_type.strip().lower()
        if not raw_type:
            raise DocumentMetadataInvalidError("Document metadata 'document_type' is empty")

        canonical = _TYPE_ALIASES.get(raw_type)
        if canonical is None:
            raise UnsupportedDocumentTypeError(document_type=raw_type)

        if canonical not in self.supported_types:
            raise UnsupportedDocumentTypeError(document_type=raw_type)

        logger.debug("Resolved document_type '%s' -> %s", raw_type, canonical.value)
        return canonical

    def _normalize_fields(
        self, doc_type: DocumentTypeEnum, parsed: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract the normalized fields for a document type.

        Only fields declared in ``_FIELD_SPECS`` for the type are included.
        Applying the field spec also drops any unexpected/extra keys from the
        raw data (a lightweight, predictable normalization). Missing optional
        fields become None rather than being fabricated.
        """
        data = parsed.get("data")
        if data is None:
            raise DocumentMetadataInvalidError("Document metadata is missing 'data'")
        if not isinstance(data, dict):
            raise DocumentMetadataInvalidError("Document metadata 'data' must be an object")

        field_spec = _FIELD_SPECS[doc_type]
        return {field: data.get(field) for field in field_spec}

