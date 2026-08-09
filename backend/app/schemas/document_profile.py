"""Pydantic Schemas for Document Profile Extraction & Mapping (Steps 2 & 3).

Step 2 (:class:`ExtractedDocumentData`) is the normalized, machine-readable
representation produced by ``DocumentProfileExtractor`` when it reads structured
metadata from a ``GovernmentDocument.doc_metadata``.

Step 3 (:class:`MappedDocumentData` / :class:`LandRecordUpdateData`) is the
destination-aware representation produced by ``DocumentProfileMapper``. It
declares *which* canonical domain fields a document's data should update and on
*which* table, but it performs no persistence and makes no business-rule
inferences.

Both transformations are intentionally *read-only*: they never write to nor
know about ``citizen_profiles``, ``land_records``, the eligibility engine, or
the recommendation engine. Persistence/conflict resolution belongs to the
future Step 4 ``ProfileEnrichmentService``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Reuse the existing document-type vocabulary. We deliberately do NOT invent a
# second, conflicting document-type system.
from app.schemas.citizen_profile import DocumentTypeEnum


class FieldConflict(BaseModel):
    """A non-destructive conflict discovered while enriching one canonical field.

    When two documents in a single enrichment operation supply different
    non-null values for the same canonical field, the service preserves the
    first non-null value (deterministic input order) and records the conflict
    here rather than silently choosing an arbitrary value.
    """

    field: str = Field(
        ...,
        description="Canonical domain field name involved in the conflict.",
    )
    table: str = Field(
        default="citizen_profiles",
        description="Which domain table the conflicting field belongs to "
        "(citizens, citizen_profiles, or land_records).",
    )
    document_type: Optional[DocumentTypeEnum] = Field(
        default=None,
        description="Document type whose value was retained.",
    )
    retained_value: Any = Field(
        default=None,
        description="The value that was kept (first non-null in input order).",
    )
    conflicting_value: Any = Field(
        default=None,
        description="The value that was ignored because a value was already set.",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Provenance id of the document that supplied the retained value.",
    )


class EnrichmentResult(BaseModel):
    """Structured outcome of a :class:`ProfileEnrichmentService` enrichment run.

    Describes exactly what was persisted so callers and tests can assert on the
    result. It does NOT replace the underlying rows — it only reports on them.
    """

    citizen_id: str = Field(..., description="The citizen whose profile was enriched.")
    processed_documents: int = Field(
        default=0,
        description="Number of mapped documents processed in this run.",
    )
    updated_citizen_fields: List[str] = Field(
        default_factory=list,
        description="Canonical citizen fields that were actually updated.",
    )
    updated_profile_fields: List[str] = Field(
        default_factory=list,
        description="Canonical citizen_profile fields that were actually updated.",
    )
    created_land_records: List[str] = Field(
        default_factory=list,
        description="survey_numbers of newly created land records.",
    )
    updated_land_records: List[str] = Field(
        default_factory=list,
        description="survey_numbers of existing land records that were updated.",
    )
    skipped_fields: List[str] = Field(
        default_factory=list,
        description="Canonical fields skipped because the document supplied a "
        "None value (nulls never overwrite existing data).",
    )
    conflicts: List[FieldConflict] = Field(
        default_factory=list,
        description="Non-destructive conflicts detected during this run.",
    )
    profile_completion_percentage: int = Field(
        default=0,
        description="Recalculated completion percentage after enrichment.",
    )


class LandRecordUpdateData(BaseModel):
    """Normalized update instructions for a single ``LandRecord``.

    This is the mapper's *intent* for one land record — it is NOT a database
    write. The Step 4 ``ProfileEnrichmentService`` decides how/where to persist
    it. Only fields with a canonical ``land_records`` destination are included;
    informational labels such as ``owner_name`` are intentionally dropped.
    """

    survey_number: Optional[str] = Field(default=None)
    land_area: Optional[float] = Field(default=None)
    land_area_unit: Optional[str] = Field(default=None)
    land_type: Optional[str] = Field(default=None)
    village: Optional[str] = Field(default=None)
    taluk: Optional[str] = Field(default=None)
    district: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    ownership_type: Optional[str] = Field(default=None)
    patta_number: Optional[str] = Field(default=None)


class MappedDocumentData(BaseModel):
    """Normalized, destination-aware update instructions produced by the mapper.

    This is a pure, read-only mapping result. It describes *what* should be
    updated (and on *which* existing domain table) for a single document, but it
    performs no persistence and makes no business-rule inferences.

    - ``citizen_updates``      — fields destined for the ``citizens`` table.
    - ``profile_updates``      — fields destined for the ``citizen_profiles`` table.
    - ``land_record_updates``  — list of ``LandRecordUpdateData`` destined for the
      ``land_records`` table.

    ``document_id`` is preserved from ``ExtractedDocumentData`` for traceability.
    """

    document_type: DocumentTypeEnum = Field(
        ...,
        description="Canonical document type that produced these updates.",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Provenance id of the source GovernmentDocument.",
    )
    citizen_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Canonical updates targeted at the citizens table.",
    )
    profile_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Canonical updates targeted at the citizen_profiles table.",
    )
    land_record_updates: List[LandRecordUpdateData] = Field(
        default_factory=list,
        description="Canonical updates targeted at the land_records table.",
    )


class ExtractedDocumentData(BaseModel):
    """Normalized structured data extracted from a single document.

    ``document_type`` uses the same vocabulary as the existing
    ``DocumentTypeEnum`` so downstream mappers can rely on one canonical set of
    document types.

    ``fields`` holds the document-specific normalized fields (e.g. Aadhaar's
    ``full_name``/``date_of_birth``, a land record's ``survey_number``/
    ``land_area``). Only fields actually present in the source metadata are
    emitted; absent optional fields are set to ``None`` rather than fabricated.

    ``document_id`` is optional provenance: when ``extract(document)`` is called
    with a ``GovernmentDocument`` the row's ``id`` is preserved here for
    traceability. ``extract_from_metadata()`` stays database-agnostic and leaves
    it ``None``.
    """

    document_type: DocumentTypeEnum = Field(
        ...,
        description="Canonical government document type (from DocumentTypeEnum).",
    )
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Normalized document fields. Missing optional fields are present "
            "with a None value; no values are ever fabricated."
        ),
    )
    document_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional provenance id of the source GovernmentDocument. Populated "
            "only by the document-aware extract() entry point."
        ),
    )

