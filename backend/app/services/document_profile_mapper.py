"""DocumentProfileMapper - Step 3: ExtractedDocumentData → MappedDocumentData.

Reads the normalized ``ExtractedDocumentData`` produced by Step 2 and determines
*which* canonical citizen/profile/land fields each document's data should
update. It translates document-specific field names onto the existing domain
vocabulary (``citizens``, ``citizen_profiles``, ``land_records``).

Pipeline (kept strictly separated so later steps stay decoupled)::

    GovernmentDocument
        -> DocumentProfileExtractor      # Step 2
        -> ExtractedDocumentData
        -> DocumentProfileMapper         # THIS STEP
        -> MappedDocumentData
        -> [future Step 4] ProfileEnrichmentService
        -> Database

The mapper is intentionally READ-ONLY and BUSINESS-RULE-FREE:
- It never writes to the database.
- It never modifies ``citizens``, ``citizen_profiles``, or ``land_records``.
- It performs NO business inference (e.g. ``land_area > 0`` is NEVER turned into
  ``is_farmer = true``). Those rules belong to Step 4 / the domain layer.
- It performs NO conflict resolution, document precedence, or merging. Each
  document is mapped independently and deterministically.
- It ignores unknown/un-related fields and never fabricates data.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.exceptions.exceptions import UnsupportedDocumentTypeError
from app.schemas.citizen_profile import DocumentTypeEnum
from app.schemas.document_profile import (
    ExtractedDocumentData,
    LandRecordUpdateData,
    MappedDocumentData,
)

logger = get_logger(__name__)


class DocumentProfileMapper:
    """Maps a document's extracted fields onto canonical domain update instructions.

    The mapper is a pure, deterministic transformation: given the same
    ``ExtractedDocumentData`` it always produces the same ``MappedDocumentData``.
    It holds no session and performs no persistence.
    """

    def __init__(self) -> None:
        # No DB session, no repositories. The mapper cannot write by design.
        pass

    # ── Public API ────────────────────────────────────────────────────────

    def map(self, document_data: ExtractedDocumentData) -> MappedDocumentData:
        """Map a single extracted document to normalized update instructions.

        Raises ``UnsupportedDocumentTypeError`` if the document type has no
        defined domain mapping.
        """
        if document_data is None:
            raise UnsupportedDocumentTypeError(
                document_type="unknown",
                reason="No extracted document data provided to map",
            )

        doc_type = document_data.document_type
        fields = document_data.fields or {}

        if doc_type == DocumentTypeEnum.AADHAAR:
            return self._map_aadhaar(document_data, fields)
        if doc_type == DocumentTypeEnum.INCOME_CERTIFICATE:
            return self._map_income_certificate(document_data, fields)
        if doc_type in (
            DocumentTypeEnum.CASTE_CERTIFICATE,
            DocumentTypeEnum.COMMUNITY_CERTIFICATE,
        ):
            return self._map_caste_certificate(document_data, fields)
        if doc_type == DocumentTypeEnum.FARMER_ID:
            return self._map_farmer_id(document_data, fields)
        if doc_type == DocumentTypeEnum.SMART_RATION_CARD:
            return self._map_ration_card(document_data, fields)
        if doc_type == DocumentTypeEnum.RESIDENCE_CERTIFICATE:
            return self._map_residence_certificate(document_data, fields)
        if doc_type == DocumentTypeEnum.DISABILITY_CERTIFICATE:
            return self._map_disability_certificate(document_data, fields)
        if doc_type == DocumentTypeEnum.LAND_RECORD:
            return self._map_land_record(document_data, fields)

        # No defined mapping for this document type (e.g. birth_certificate).
        raise UnsupportedDocumentTypeError(document_type=doc_type.value)

    def map_many(
        self, documents: List[ExtractedDocumentData]
    ) -> List[MappedDocumentData]:
        """Map each extracted document independently.

        Each document is mapped on its own. No merging, conflict resolution, or
        precedence logic is performed here — that belongs to Step 4.
        """
        if not documents:
            return []
        return [self.map(doc) for doc in documents]

    # ── Individual document mappers ───────────────────────────────────────

    def _map_aadhaar(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Aadhaar → citizens (identity + address). Nothing goes to the profile."""
        citizen_updates = {}
        for src, dst in (
            ("full_name", "full_name"),
            ("date_of_birth", "date_of_birth"),
            ("gender", "gender"),
            ("address_line1", "address_line1"),
            ("village", "village"),
            ("taluk", "taluk"),
            ("district", "district"),
            ("state", "state"),
            ("pincode", "pincode"),
        ):
            value = fields.get(src)
            if value is not None:
                citizen_updates[dst] = value
        return self._build(data, citizen_updates=citizen_updates)

    def _map_income_certificate(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Income Certificate → citizen_profiles (economic)."""
        profile_updates = {}
        for src, dst in (
            ("annual_income", "annual_income"),
            ("income_category", "income_category"),
        ):
            value = fields.get(src)
            if value is not None:
                profile_updates[dst] = value
        return self._build(data, profile_updates=profile_updates)

    def _map_caste_certificate(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Caste / Community Certificate → citizen_profiles (social)."""
        profile_updates = {}
        for src, dst in (
            ("caste", "caste"),
            ("community", "community"),
            ("sub_caste", "sub_caste"),
            ("religion", "religion"),
        ):
            value = fields.get(src)
            if value is not None:
                profile_updates[dst] = value
        return self._build(data, profile_updates=profile_updates)

    def _map_farmer_id(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Farmer ID → citizen_profiles (farmer status)."""
        profile_updates = {}
        for src, dst in (
            ("farmer_id", "farmer_id"),
            ("is_farmer", "is_farmer"),
            ("occupation", "occupation"),
        ):
            value = fields.get(src)
            if value is not None:
                profile_updates[dst] = value
        return self._build(data, profile_updates=profile_updates)

    def _map_ration_card(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Ration Card → citizens.smart_ration_card + citizen_profiles.family_member_count.

        ``card_number`` is the canonical ``citizens.smart_ration_card``.
        ``family_size`` is the canonical ``citizen_profiles.family_member_count``.
        ``card_type`` intentionally has NO canonical destination (it would imply
        business inference to map it onto income/BPL) and is therefore dropped.
        """
        citizen_updates = {}
        profile_updates = {}

        card_number = fields.get("card_number")
        if card_number is not None:
            citizen_updates["smart_ration_card"] = card_number

        family_size = fields.get("family_size")
        if family_size is not None:
            profile_updates["family_member_count"] = family_size

        return self._build(
            data,
            citizen_updates=citizen_updates,
            profile_updates=profile_updates,
        )

    def _map_residence_certificate(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Residence Certificate → citizens (address only)."""
        citizen_updates = {}
        for src, dst in (
            ("village", "village"),
            ("taluk", "taluk"),
            ("district", "district"),
            ("state", "state"),
        ):
            value = fields.get(src)
            if value is not None:
                citizen_updates[dst] = value
        return self._build(data, citizen_updates=citizen_updates)

    def _map_disability_certificate(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Disability Certificate → citizen_profiles (disability status)."""
        profile_updates = {}
        for src, dst in (
            ("is_disabled", "is_disabled"),
            ("disability_percentage", "disability_percentage"),
        ):
            value = fields.get(src)
            if value is not None:
                profile_updates[dst] = value
        return self._build(data, profile_updates=profile_updates)

    def _map_land_record(
        self, data: ExtractedDocumentData, fields: Dict[str, Any]
    ) -> MappedDocumentData:
        """Land Record → land_records (single record update instruction).

        ``owner_name`` is an informational label and is intentionally dropped.
        ``unit`` maps to the canonical ``land_area_unit`` field.
        No profile/citizen inference (e.g. is_farmer) is performed here.
        """
        land = LandRecordUpdateData()
        for src, dst in (
            ("survey_number", "survey_number"),
            ("land_area", "land_area"),
            ("unit", "land_area_unit"),
            ("land_type", "land_type"),
            ("village", "village"),
            ("taluk", "taluk"),
            ("district", "district"),
            ("state", "state"),
            ("ownership_type", "ownership_type"),
            ("patta_number", "patta_number"),
        ):
            value = fields.get(src)
            if value is not None:
                setattr(land, dst, value)

        return self._build(data, land_record_updates=[land])

    # ── Result builder ────────────────────────────────────────────────────

    def _build(
        self,
        data: ExtractedDocumentData,
        citizen_updates: Optional[Dict[str, Any]] = None,
        profile_updates: Optional[Dict[str, Any]] = None,
        land_record_updates: Optional[List[LandRecordUpdateData]] = None,
    ) -> MappedDocumentData:
        """Assemble a MappedDocumentData, preserving the document_id."""
        return MappedDocumentData(
            document_type=data.document_type,
            document_id=data.document_id,
            citizen_updates=citizen_updates or {},
            profile_updates=profile_updates or {},
            land_record_updates=land_record_updates or [],
        )

