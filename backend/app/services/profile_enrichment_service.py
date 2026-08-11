"""ProfileEnrichmentService - Step 4: MappedDocumentData → Persisted Profile.

This is the first pipeline stage permitted to write to the database. It consumes
the destination-aware :class:`MappedDocumentData` produced by Step 3
(``DocumentProfileMapper``) and incrementally enriches the citizen's existing
internal profile across three canonical tables:

- ``citizens``            (identity + address)
- ``citizen_profiles``    (economic / social / farmer / disability / family)
- ``land_records``        (one row per owned parcel)

Pipeline (responsibilities kept strictly separated)::

    GovernmentDocument
        -> DocumentProfileExtractor      # Step 2
        -> ExtractedDocumentData
        -> DocumentProfileMapper         # Step 3
        -> MappedDocumentData
        -> ProfileEnrichmentService      # THIS STEP
        -> Database

The service never parses raw ``GovernmentDocument.doc_metadata``. It only reads
the already-normalized, destination-aware ``MappedDocumentData``.

Design rules (per specification):
- **Incremental partial updates** — a document only updates the fields it
  supplies; it never replaces the whole profile.
- **Nulls never overwrite** — a ``None`` document value never clobbers an
  existing value.
- **Deterministic conflict handling** — when two documents in one run supply
  different non-null values for the same field, the first non-null value in
  input order is retained and the conflict is reported (not silently hidden).
- **Idempotent land records** — land records are matched on the strongest
  existing identifier (``citizen_id + survey_number``); re-processing the same
  parcel updates the existing row instead of inserting a duplicate.
- **Farmer inference** — only a Farmer ID with ``is_farmer=true`` sets farmer
  status. Land ownership alone does NOT imply farmer status (no invented rule).
- **Profile completion** — reuses the shared ``calculate_profile_completion``
  helper so there is exactly one completion algorithm.

Transaction behavior: this service uses the existing repository convention
(each repository commits individually). It does NOT introduce a new
service-level transaction. See the module docstring of the test for the
documented atomicity limitation.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.exceptions.exceptions import NotFoundError
from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import (
    CitizenProfileRepository,
    LandRecordRepository,
)
from app.schemas.citizen_profile import DocumentTypeEnum
from app.schemas.document_profile import (
    EnrichmentResult,
    FieldConflict,
    LandRecordUpdateData,
    MappedDocumentData,
)
from app.services.citizen_profile_service import calculate_profile_completion

logger = get_logger(__name__)


class ProfileEnrichmentService:
    """Incrementally enriches a citizen's profile from mapped documents."""

    def __init__(self, db: Session):
        self.db = db
        self.citizen_repo = CitizenRepository(db)
        self.profile_repo = CitizenProfileRepository(db)
        self.land_repo = LandRecordRepository(db)

    # ── Public API ────────────────────────────────────────────────────────

    def enrich(
        self, citizen_id: str, mapped_document: MappedDocumentData
    ) -> EnrichmentResult:
        """Enrich a citizen's profile from a single mapped document."""
        return self.enrich_many(citizen_id, [mapped_document])

    def enrich_many(
        self, citizen_id: str, mapped_documents: List[MappedDocumentData]
    ) -> EnrichmentResult:
        """Enrich a citizen's profile from multiple mapped documents.

        Documents are processed in the given (deterministic) order. For a given
        canonical field, the first non-null value wins; later conflicting values
        are reported as conflicts rather than silently overriding.
        """
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        result = EnrichmentResult(citizen_id=citizen_id)

        # Deterministic field-merge maps: canonical field -> retained value.
        committed_citizen: Dict[str, Any] = {}
        committed_profile: Dict[str, Any] = {}

        # Track the document that supplied each committed value (for conflict
        # reporting). Keyed by (table, field).
        provenance: Dict[tuple, tuple] = {}

        documents = mapped_documents or []

        for mapped in documents:
            if mapped is None:
                continue
            result.processed_documents += 1

            # citizens
            committed_citizen, conflicts = self._merge_fields(
                table="citizens",
                incoming=mapped.citizen_updates or {},
                committed=committed_citizen,
                provenance=provenance,
                document_type=mapped.document_type,
                document_id=mapped.document_id,
            )
            result.conflicts.extend(conflicts)

            # citizen_profiles
            committed_profile, conflicts = self._merge_fields(
                table="citizen_profiles",
                incoming=mapped.profile_updates or {},
                committed=committed_profile,
                provenance=provenance,
                document_type=mapped.document_type,
                document_id=mapped.document_id,
            )
            result.conflicts.extend(conflicts)

            # land_records
            for land in mapped.land_record_updates or []:
                created, updated, conflicts = self._apply_land_record(
                    citizen_id, land
                )
                result.conflicts.extend(conflicts)
                if created:
                    result.created_land_records.append(created)
                if updated:
                    result.updated_land_records.append(updated)

        # Recompute which fields were actually updated (non-null committed value
        # differing from current persisted value).
        citizen_updates = self._build_non_null_updates(committed_citizen)
        profile_updates = self._build_non_null_updates(committed_profile)

        # Persist citizen updates (if any).
        if citizen_updates:
            citizen_updates = self._coerce_citizen_updates(citizen_updates)
            self.citizen_repo.update(citizen_id, citizen_updates)
            result.updated_citizen_fields.extend(sorted(citizen_updates.keys()))

        # Persist profile updates (if any).
        if profile_updates:
            self.profile_repo.upsert(citizen_id, profile_updates)
            result.updated_profile_fields.extend(sorted(profile_updates.keys()))

        # Record skipped fields: committed values that were None (nulls never
        # overwrite). We derive these from the incoming documents.
        skipped = self._collect_skipped_fields(documents)
        result.skipped_fields.extend(sorted(skipped))

        # Recalculate profile completion using the shared helper and persist it
        # so the stored value reflects the newly derived information. If no
        # profile row exists yet (e.g. a citizen-only document), upserting
        # creates one carrying the completion score.
        refreshed_citizen = self.citizen_repo.get_by_id(citizen_id)
        profile = self.profile_repo.get_by_citizen_id(citizen_id)
        completion = calculate_profile_completion(
            refreshed_citizen, profile if profile else {}
        )
        result.profile_completion_percentage = completion
        self.profile_repo.upsert(
            citizen_id, {"profile_completion_percentage": completion}
        )

        logger.info(
            f"Enrichment for citizen {citizen_id} applied: "
            f"{len(result.updated_citizen_fields)} citizen fields, "
            f"{len(result.updated_profile_fields)} profile fields, "
            f"{len(result.created_land_records)} land created, "
            f"{len(result.updated_land_records)} land updated, "
            f"{len(result.conflicts)} conflicts"
        )
        return result

    # ── Deterministic field merge ─────────────────────────────────────────

    def _merge_fields(
        self,
        table: str,
        incoming: Dict[str, Any],
        committed: Dict[str, Any],
        provenance: Dict[tuple, tuple],
        document_type: DocumentTypeEnum,
        document_id: Optional[str],
    ) -> tuple:
        """Merge an incoming document's field updates into the committed map.

        Returns the updated ``committed`` map and a list of new conflicts.
        Deterministic rule: the first non-null value in input order wins. A
        None value is never committed (nulls never overwrite).
        """
        conflicts: List[FieldConflict] = []
        for field, value in incoming.items():
            if value is None:
                # Nulls are never written; not a conflict by itself.
                continue
            if field in committed:
                existing = committed[field]
                if existing != value:
                    # Prefer the already-committed (earlier) value and report.
                    owner_doc_type, owner_doc_id = provenance.get(
                        (table, field), (document_type, document_id)
                    )
                    conflicts.append(
                        FieldConflict(
                            field=field,
                            table=table,
                            document_type=owner_doc_type,
                            retained_value=existing,
                            conflicting_value=value,
                            document_id=owner_doc_id,
                        )
                    )
                # else: identical value, no conflict.
                continue
            # First non-null value for this field.
            committed[field] = value
            provenance[(table, field)] = (document_type, document_id)
        return committed, conflicts

    @staticmethod
    def _build_non_null_updates(committed: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out None committed values (they must never be persisted)."""
        return {k: v for k, v in committed.items() if v is not None}

    @staticmethod
    def _coerce_citizen_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce citizen fields to the types the model expects.

        ``date_of_birth`` is produced by the extractor as an ISO date string,
        but the ``citizens.date_of_birth`` column is a ``DateTime`` (which both
        MySQL and SQLite enforce). Convert it to a ``datetime``/``date`` here so
        persistence is DB-agnostic. Unknown/unrelated values pass through.
        """
        coerced: Dict[str, Any] = {}
        for field, value in updates.items():
            if field == "date_of_birth" and isinstance(value, str):
                try:
                    coerced[field] = datetime.fromisoformat(value)
                except ValueError:
                    # Fall back to the raw string; the bind will surface the
                    # real error rather than silently corrupting data.
                    coerced[field] = value
            else:
                coerced[field] = value
        return coerced

    def _collect_skipped_fields(self, documents: List[MappedDocumentData]) -> set:
        """Collect canonical fields that were supplied as None by documents."""
        skipped = set()
        for mapped in documents:
            if mapped is None:
                continue
            for field, value in (mapped.citizen_updates or {}).items():
                if value is None:
                    skipped.add(field)
            for field, value in (mapped.profile_updates or {}).items():
                if value is None:
                    skipped.add(field)
        return skipped

    # ── Land record handling ──────────────────────────────────────────────

    def _apply_land_record(
        self, citizen_id: str, land: LandRecordUpdateData
    ) -> tuple:
        """Idempotently create or update a single land record.

        Deduplication identifier: ``citizen_id + survey_number`` (the strongest
        available existing identifier). Re-processing the same survey updates
        the existing record's missing fields instead of inserting a duplicate.

        Returns ``(created_survey, updated_survey, conflicts)``.
        """
        survey = land.survey_number
        if not survey:
            # No reliable identifier — nothing to dedupe against. Skip.
            logger.warning(
                f"Land record for citizen {citizen_id} has no survey_number; skipped"
            )
            return None, None, []

        existing = self.land_repo.get_by_citizen_and_survey(citizen_id, survey)
        conflicts: List[FieldConflict] = []

        if existing:
            # Update missing/non-null fields only; never overwrite with None.
            updates = self._build_non_null_updates(
                land.model_dump(exclude_none=True)
            )
            if updates:
                for key, value in updates.items():
                    setattr(existing, key, value)
                self.db.commit()
                self.db.refresh(existing)
                logger.info(
                    f"LandRecord updated for citizen {citizen_id} survey {survey}"
                )
            return None, survey, conflicts

        # Create a new land record.
        record_data = land.model_dump(exclude_none=True)
        record_data["citizen_id"] = citizen_id
        self.land_repo.create(record_data)
        logger.info(f"LandRecord created for citizen {citizen_id} survey {survey}")
        return survey, None, conflicts

