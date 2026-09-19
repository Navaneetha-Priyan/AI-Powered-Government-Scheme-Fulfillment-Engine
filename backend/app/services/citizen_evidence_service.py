"""Canonical citizen evidence layer (single source of truth for "what does the
citizen actually hold?").

Problem this module solves
--------------------------
Uploaded documents and DigiLocker/government documents were stored as two
unrelated representations:

* ``uploaded_documents.document_type``   -> ``aadhaar_card``, ``land_document``
* ``government_documents.document_type`` -> ``aadhaar``, ``land_record``

Eligibility requirements (``aadhaar``, ``land_record``) only ever matched the
second vocabulary, so an Aadhaar the citizen had uploaded and verified was
reported as "missing" while the very same document arriving through DigiLocker
was seen. This module removes that divergence.

Pipeline
--------
::

    UploadedDocument   (Build My Profile upload + verification)
    GovernmentDocument (DigiLocker sync + citizen uploads)
                |
                v
        canonical_evidence_type()   # explicit alias map, never a default
                |
                v
        CitizenEvidence             # canonical citizen evidence
                |
                v
        EligibilityEvaluator        # criterion + evidence evaluation

Design rules
------------
* **One canonical vocabulary.** Canonical evidence keys are the requirement keys
  already used by ``data/eligibility_rules/catalog.json`` and by the DigiLocker
  ``DocumentType`` enum, so no third naming scheme is introduced.
* **Explicit aliasing only.** ``canonical_evidence_type`` returns ``None`` for
  anything it does not positively recognise. Unknown document types are
  reported through ``CitizenEvidence.unmapped_types`` and are NEVER silently
  mapped onto an unrelated type such as ``land_record``.
* **Verification is state, not a boolean.** Each canonical type carries an
  :class:`EvidenceState` so the UI can distinguish verified evidence, evidence
  that is present but not yet verified, and genuinely missing evidence.
* **No inference.** This layer never derives a profile fact (age, income,
  farmer status...) from a document. It only reports which canonical evidence
  items exist and how trustworthy they are. Profile facts stay owned by
  ``citizens`` / ``citizen_profiles`` / ``land_records``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.citizen_document import (
    DocumentProcessStatus,
    UploadedDocument,
    VerificationStatus as UploadVerificationStatus,
)
from app.models.digilocker import DocumentVerificationStatus, GovernmentDocument
from app.repositories.digilocker_repository import GovernmentDocumentRepository
from app.services.evidence_mapping_service import get_mapping

logger = get_logger(__name__)

__all__ = [
    "CANONICAL_EVIDENCE_TYPES",
    "CanonicalEvidenceItem",
    "CitizenEvidence",
    "CitizenEvidenceService",
    "EvidenceState",
    "canonical_evidence_type",
    "evidence_from_raw_types",
    "requirement_evidence_types",
]


# ── Canonical evidence vocabulary ────────────────────────────────────────────
# These strings are simultaneously:
#   * the DigiLocker ``DocumentType`` values, and
#   * the evidence-requirement keys used by catalog.json.
# Reusing them keeps one vocabulary end to end.

EVIDENCE_AADHAAR = "aadhaar"
EVIDENCE_SMART_RATION_CARD = "smart_ration_card"
EVIDENCE_INCOME_CERTIFICATE = "income_certificate"
EVIDENCE_COMMUNITY_CERTIFICATE = "community_certificate"
EVIDENCE_CASTE_CERTIFICATE = "caste_certificate"
EVIDENCE_RESIDENCE_CERTIFICATE = "residence_certificate"
EVIDENCE_LAND_RECORD = "land_record"
EVIDENCE_DISABILITY_CERTIFICATE = "disability_certificate"
EVIDENCE_FARMER_ID = "farmer_id"
EVIDENCE_BIRTH_CERTIFICATE = "birth_certificate"
EVIDENCE_BANK_PASSBOOK = "bank_passbook"
EVIDENCE_EDUCATION_CERTIFICATE = "education_certificate"

CANONICAL_EVIDENCE_TYPES = frozenset(
    {
        EVIDENCE_AADHAAR,
        EVIDENCE_SMART_RATION_CARD,
        EVIDENCE_INCOME_CERTIFICATE,
        EVIDENCE_COMMUNITY_CERTIFICATE,
        EVIDENCE_CASTE_CERTIFICATE,
        EVIDENCE_RESIDENCE_CERTIFICATE,
        EVIDENCE_LAND_RECORD,
        EVIDENCE_DISABILITY_CERTIFICATE,
        EVIDENCE_FARMER_ID,
        EVIDENCE_BIRTH_CERTIFICATE,
        EVIDENCE_BANK_PASSBOOK,
        EVIDENCE_EDUCATION_CERTIFICATE,
    }
)


# Explicit raw-document-type -> canonical-evidence-type aliases.
#
# Only equivalences that are true in the domain belong here. Anything absent
# stays unknown and is surfaced through ``CitizenEvidence.unmapped_types``.
DOCUMENT_TYPE_ALIASES: dict[str, str] = {
    # -- Upload vocabulary (``CitizenDocumentType``) ------------------------
    "aadhaar_card": EVIDENCE_AADHAAR,
    "smart_ration_card": EVIDENCE_SMART_RATION_CARD,
    "income_certificate": EVIDENCE_INCOME_CERTIFICATE,
    "community_certificate": EVIDENCE_COMMUNITY_CERTIFICATE,
    "land_document": EVIDENCE_LAND_RECORD,
    "farmer_document": EVIDENCE_FARMER_ID,
    "disability_certificate": EVIDENCE_DISABILITY_CERTIFICATE,
    "bank_passbook": EVIDENCE_BANK_PASSBOOK,
    "education_certificate": EVIDENCE_EDUCATION_CERTIFICATE,
    # -- DigiLocker vocabulary (``DocumentType``) ---------------------------
    "aadhaar": EVIDENCE_AADHAAR,
    "land_record": EVIDENCE_LAND_RECORD,
    "farmer_id": EVIDENCE_FARMER_ID,
    "residence_certificate": EVIDENCE_RESIDENCE_CERTIFICATE,
    "caste_certificate": EVIDENCE_CASTE_CERTIFICATE,
    "birth_certificate": EVIDENCE_BIRTH_CERTIFICATE,
    # -- Documented synonyms already present in repository data -------------
    "aadhar": EVIDENCE_AADHAAR,
    "ration_card": EVIDENCE_SMART_RATION_CARD,
    "farmer_card": EVIDENCE_FARMER_ID,
    "farmer_certificate": EVIDENCE_FARMER_ID,
    "land_patta": EVIDENCE_LAND_RECORD,
    "income_proof": EVIDENCE_INCOME_CERTIFICATE,
    "bank_account": EVIDENCE_BANK_PASSBOOK,
}

# Requirement-side equivalences: a requirement may accept more than one
# canonical type when the underlying evidence is the same thing under different
# government names. ``caste_certificate`` and ``community_certificate`` are the
# same certificate; the existing ``evidence_mapping_service`` already maps the
# ``caste_certificate`` requirement onto a Community certificate upload, so this
# only makes that existing decision explicit in one place.
REQUIREMENT_EQUIVALENTS: dict[str, frozenset[str]] = {
    EVIDENCE_CASTE_CERTIFICATE: frozenset(
        {EVIDENCE_CASTE_CERTIFICATE, EVIDENCE_COMMUNITY_CERTIFICATE}
    ),
    EVIDENCE_COMMUNITY_CERTIFICATE: frozenset(
        {EVIDENCE_COMMUNITY_CERTIFICATE, EVIDENCE_CASTE_CERTIFICATE}
    ),
}

# ``unknown`` is an explicit upload slot, not a real evidence type.
_IGNORED_RAW_TYPES = {"unknown", "none", "", "null"}


class EvidenceState(str, Enum):
    """How trustworthy one canonical evidence item is right now."""

    VERIFIED = "verified"   # held and confirmed
    PRESENT = "present"     # held but not yet confirmed
    EXPIRED = "expired"     # held but no longer valid
    REJECTED = "rejected"   # held but refused
    MISSING = "missing"     # not held at all
    UNKNOWN = "unknown"     # cannot be determined

    @property
    def is_available(self) -> bool:
        """True when the item counts as evidence actually held by the citizen."""
        return self in {EvidenceState.VERIFIED, EvidenceState.PRESENT}


# Lower rank wins when several stored documents resolve to the same type.
_STATE_PRECEDENCE: dict[EvidenceState, int] = {
    EvidenceState.VERIFIED: 0,
    EvidenceState.PRESENT: 1,
    EvidenceState.EXPIRED: 2,
    EvidenceState.REJECTED: 3,
    EvidenceState.MISSING: 4,
    EvidenceState.UNKNOWN: 5,
}


def _raw_type_value(raw: Any) -> str:
    """Return the lower-case string value of a document-type field/enum."""
    if raw is None:
        return ""
    value = getattr(raw, "value", raw)
    return str(value).strip().lower()


def canonical_evidence_type(raw: Any) -> Optional[str]:
    """Map any raw document-type value onto a canonical evidence type.

    Returns ``None`` when the value cannot be positively identified. Callers
    MUST handle ``None`` explicitly and must never substitute a default type.
    """
    key = _raw_type_value(raw)
    if key in _IGNORED_RAW_TYPES:
        return None
    if key in CANONICAL_EVIDENCE_TYPES:
        return key
    return DOCUMENT_TYPE_ALIASES.get(key)


def _candidate_requirement_keys(requirement: Any) -> list[str]:
    key = _raw_type_value(requirement)
    if not key:
        return []
    # Catalogue keys are snake_case; tolerate the space-separated form too.
    return [key, key.replace(" ", "_")]


def requirement_evidence_types(requirement: Any) -> tuple[frozenset[str], str]:
    """Return ``(canonical_types, kind)`` that satisfy one requirement.

    ``kind`` is one of ``document`` (resolvable from held evidence),
    ``profile_info`` (must come from the citizen profile) or ``manual``
    (scheme-specific evidence with no automatic mapping).

    There is exactly ONE requirement->evidence mapping table in the codebase
    (``evidence_mapping_service``); this function reuses it and never invents a
    mapping for an unrecognised key.
    """
    for key in _candidate_requirement_keys(requirement):
        mapping = get_mapping(key)
        if mapping is None:
            continue
        if mapping.kind != "document":
            return frozenset(), mapping.kind
        resolved: set[str] = set()
        for raw_type in mapping.document_types:
            canonical = canonical_evidence_type(raw_type)
            if canonical:
                resolved.add(canonical)
        for canonical in list(resolved):
            resolved.update(REQUIREMENT_EQUIVALENTS.get(canonical, ()))
        return frozenset(resolved), "document"

    # No upload slot is mapped for this key. The key itself may already BE a
    # canonical evidence type (``aadhaar``, ``land_record``,
    # ``caste_certificate``, ...) which is the case for most catalogue
    # requirements.
    for key in _candidate_requirement_keys(requirement):
        canonical = canonical_evidence_type(key)
        if canonical:
            equivalents = REQUIREMENT_EQUIVALENTS.get(
                canonical, frozenset({canonical})
            )
            return frozenset(equivalents), "document"

    return frozenset(), "manual"


@dataclass(frozen=True)
class CanonicalEvidenceItem:
    """One canonical evidence item derived from a concrete stored document."""

    canonical_type: str
    state: EvidenceState
    raw_type: str
    source: str                 # "uploaded_document" | "government_document"
    document_id: Optional[str] = None
    label: Optional[str] = None
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_type": self.canonical_type,
            "state": self.state.value,
            "raw_type": self.raw_type,
            "source": self.source,
            "document_id": self.document_id,
            "label": self.label,
            "verified": self.verified,
        }


@dataclass
class CitizenEvidence:
    """Canonical citizen evidence: canonical type -> best known state."""

    items: list[CanonicalEvidenceItem] = field(default_factory=list)
    unmapped_types: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        best: dict[str, CanonicalEvidenceItem] = {}
        for item in self.items:
            current = best.get(item.canonical_type)
            if current is None or (
                _STATE_PRECEDENCE[item.state] < _STATE_PRECEDENCE[current.state]
            ):
                best[item.canonical_type] = item
        self._best = best

    # ── Canonical type level ────────────────────────────────────────────
    @property
    def by_type(self) -> dict[str, CanonicalEvidenceItem]:
        return dict(self._best)

    @property
    def verified_types(self) -> set[str]:
        return {
            key
            for key, item in self._best.items()
            if item.state == EvidenceState.VERIFIED
        }

    @property
    def pending_types(self) -> set[str]:
        return {
            key
            for key, item in self._best.items()
            if item.state == EvidenceState.PRESENT
        }

    @property
    def unavailable_types(self) -> set[str]:
        return {
            key
            for key, item in self._best.items()
            if item.state in {EvidenceState.EXPIRED, EvidenceState.REJECTED}
        }

    @property
    def available_types(self) -> set[str]:
        """Canonical types the citizen actually holds (verified or present)."""
        return self.verified_types | self.pending_types

    @property
    def states(self) -> dict[str, str]:
        return {key: item.state.value for key, item in self._best.items()}

    @property
    def names(self) -> set[str]:
        return {
            str(item.label).strip().lower()
            for item in self._best.values()
            if item.label
        }

    def state_for(self, canonical_type: Any) -> EvidenceState:
        """Best known state for one canonical type (``MISSING`` if absent)."""
        canonical = canonical_evidence_type(canonical_type) or _raw_type_value(
            canonical_type
        )
        item = self._best.get(canonical)
        return item.state if item else EvidenceState.MISSING

    # ── Requirement level ───────────────────────────────────────────────
    def state_for_requirement(self, requirement: Any) -> EvidenceState:
        """Best evidence state for one scheme evidence requirement.

        Returns ``MISSING`` when the requirement is a document requirement the
        citizen does not hold, so callers never have to guess. Profile-only and
        manual requirements report ``UNKNOWN`` because this layer only knows
        about documents.
        """
        types, kind = requirement_evidence_types(requirement)
        if kind != "document" or not types:
            return EvidenceState.UNKNOWN
        states = [self.state_for(canonical) for canonical in sorted(types)]
        if not states:
            return EvidenceState.MISSING
        return min(states, key=lambda state: _STATE_PRECEDENCE[state])

    def satisfies(self, requirement: Any) -> bool:
        """True only when real, usable evidence exists for the requirement."""
        return self.state_for_requirement(requirement).is_available

    def missing_requirements(self, requirements: Iterable[Any]) -> list[str]:
        """Return the requirement keys that are genuinely not satisfied.

        Order is preserved and duplicates are collapsed, so the result is
        directly usable as the evaluator's ``missing_evidence`` list.
        """
        missing: list[str] = []
        for requirement in requirements or []:
            key = str(requirement or "").strip()
            if not key or key in missing:
                continue
            if not self.satisfies(key):
                missing.append(key)
        return missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "states": self.states,
            "verified": sorted(self.verified_types),
            "pending": sorted(self.pending_types),
            "unavailable": sorted(self.unavailable_types),
            "unmapped_document_types": list(self.unmapped_types),
        }


def citizen_evidence_for(context: Any) -> CitizenEvidence:
    """Return the canonical evidence view for a citizen context.

    Prefers the canonical evidence layer built by ``CitizenContextService``.
    When a context was constructed directly (tests, persisted snapshots) the
    raw ``document_types`` / ``document_names`` collections are adapted into
    the same canonical representation, so evaluation semantics never depend on
    how the context was produced.
    """
    evidence = getattr(context, "citizen_evidence", None)
    if isinstance(evidence, CitizenEvidence):
        return evidence
    return evidence_from_raw_types(
        getattr(context, "document_types", None) or [],
        getattr(context, "document_names", None) or [],
        verified_types=getattr(context, "verified_document_types", None),
    )


def evidence_from_raw_types(
    document_types: Iterable[Any] | Mapping[str, Any] | None,
    document_names: Iterable[Any] | None = None,
    *,
    verified_types: Iterable[Any] | None = None,
) -> CitizenEvidence:
    """Build a canonical evidence view from raw type/name collections.

    Compatibility adapter for callers that already hold document-type strings
    (the persisted recommendation context snapshot) and for ``CitizenContext``
    instances constructed directly in tests. Types listed in ``verified_types``
    are reported as ``VERIFIED``; all others as ``PRESENT``. Unknown types are
    reported as unmapped instead of being defaulted.
    """
    verified = {
        canonical_evidence_type(value) for value in (verified_types or [])
    } - {None}

    if isinstance(document_types, Mapping):
        candidates: Iterable[Any] = list(document_types.keys())
    else:
        candidates = list(document_types or [])
    name_list = [str(name).strip().lower() for name in (document_names or [])]

    items: list[CanonicalEvidenceItem] = []
    unmapped: list[str] = []
    for raw in candidates:
        key = _raw_type_value(raw)
        if not key or key in _IGNORED_RAW_TYPES:
            continue
        canonical = canonical_evidence_type(raw)
        if canonical is None:
            if key not in unmapped:
                unmapped.append(key)
            continue
        state = (
            EvidenceState.VERIFIED if canonical in verified else EvidenceState.PRESENT
        )
        label = next(
            (
                name
                for name in name_list
                if key in name or key.replace("_", " ") in name
            ),
            None,
        )
        items.append(
            CanonicalEvidenceItem(
                canonical_type=canonical,
                state=state,
                raw_type=key,
                source="declared",
                label=label,
                verified=state == EvidenceState.VERIFIED,
            )
        )
    return CitizenEvidence(items=items, unmapped_types=unmapped)


class CitizenEvidenceService:
    """Aggregate every citizen document source into :class:`CitizenEvidence`.

    Sources are unified read-only; this service never writes and never changes
    document state:

    * ``government_documents`` — DigiLocker sync results AND citizen uploads
      made through the government-document endpoint (that endpoint stores both
      in this table).
    * ``uploaded_documents`` — the "Build My Profile" document-intelligence
      uploads, whose ``verification_status`` becomes ``verified`` once the
      citizen confirms the extracted profile.
    """

    def __init__(self, db: Session):
        self.db = db
        self.government_document_repo = GovernmentDocumentRepository(db)

    # ── Public API ──────────────────────────────────────────────────────
    def build(self, citizen_id: str) -> CitizenEvidence:
        """Return the canonical evidence view for one citizen."""
        items: list[CanonicalEvidenceItem] = []
        unmapped: list[str] = []

        for item, raw_key, mapped in self._iter_government_documents(citizen_id):
            items.append(item)
            if not mapped:
                unmapped.append(raw_key)

        for item, raw_key, mapped in self._iter_uploaded_documents(citizen_id):
            items.append(item)
            if not mapped:
                unmapped.append(raw_key)

        return CitizenEvidence(items=items, unmapped_types=_dedupe(unmapped))

    # ── Source adapters ─────────────────────────────────────────────────
    def _iter_government_documents(self, citizen_id: str):
        documents: Sequence[GovernmentDocument] = (
            self.government_document_repo.get_by_citizen_id(citizen_id)
        )
        for document in documents or []:
            raw_key = _raw_type_value(getattr(document, "document_type", None))
            canonical = canonical_evidence_type(raw_key)
            state = (
                self._government_document_state(document)
                if canonical is not None
                else EvidenceState.UNKNOWN
            )
            yield (
                CanonicalEvidenceItem(
                    canonical_type=canonical or raw_key,
                    state=state,
                    raw_type=raw_key,
                    source="government_document",
                    document_id=document.id,
                    label=getattr(document, "document_name", None),
                    verified=state == EvidenceState.VERIFIED,
                ),
                raw_key,
                canonical is not None,
            )

    def _iter_uploaded_documents(self, citizen_id: str):
        documents = (
            self.db.query(UploadedDocument)
            .filter(UploadedDocument.citizen_id == citizen_id)
            .all()
        )
        for document in documents or []:
            raw_key = _raw_type_value(getattr(document, "document_type", None))
            canonical = canonical_evidence_type(raw_key)
            state = (
                self._uploaded_document_state(document)
                if canonical is not None
                else EvidenceState.UNKNOWN
            )
            yield (
                CanonicalEvidenceItem(
                    canonical_type=canonical or raw_key,
                    state=state,
                    raw_type=raw_key,
                    source="uploaded_document",
                    document_id=document.id,
                    label=getattr(document, "original_file_name", None),
                    verified=state == EvidenceState.VERIFIED,
                ),
                raw_key,
                canonical is not None,
            )

    # ── State derivation ────────────────────────────────────────────────
    @staticmethod
    def _government_document_state(document: GovernmentDocument) -> EvidenceState:
        status = getattr(document, "verification_status", None)
        if status == DocumentVerificationStatus.REJECTED:
            return EvidenceState.REJECTED
        if status == DocumentVerificationStatus.EXPIRED:
            return EvidenceState.EXPIRED
        try:
            if document.is_expired():
                return EvidenceState.EXPIRED
        except Exception:  # pragma: no cover - defensive for detached instances
            pass
        if status == DocumentVerificationStatus.VERIFIED:
            return EvidenceState.VERIFIED
        return EvidenceState.PRESENT

    @staticmethod
    def _uploaded_document_state(document: UploadedDocument) -> EvidenceState:
        if (
            getattr(document, "verification_status", None)
            == UploadVerificationStatus.REJECTED
        ):
            return EvidenceState.REJECTED
        if getattr(document, "upload_status", None) == DocumentProcessStatus.FAILED:
            return EvidenceState.REJECTED
        if (
            getattr(document, "verification_status", None)
            == UploadVerificationStatus.VERIFIED
        ):
            return EvidenceState.VERIFIED
        if getattr(document, "upload_status", None) == DocumentProcessStatus.VERIFIED:
            return EvidenceState.VERIFIED
        return EvidenceState.PRESENT


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
