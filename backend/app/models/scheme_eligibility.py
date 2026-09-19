"""Structured eligibility models for government schemes (Phase 2).

These models represent eligibility criteria extracted from scheme PDFs.
All fields are optional because not every scheme document provides every criterion.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EligibilityStatus(str):
    """The ONE canonical overall-eligibility vocabulary.

    Single authoritative owner of the status representation used by the
    evaluator, the recommendation service, the API layer, and the persisted
    ``CitizenSchemeMatch.eligibility_status`` column. Other modules reference
    these constants instead of hard-coding strings; no module may introduce a
    second vocabulary.

    Legacy aliases (``possibly_eligible``, ``ineligible``) are still accepted on
    read for rows persisted before this consolidation; use
    :func:`normalize_eligibility_status` to translate them.
    """

    ELIGIBLE = "eligible"
    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NOT_ELIGIBLE = "not_eligible"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


# Legacy -> canonical aliases. Read-only compatibility; never written.
_LEGACY_STATUS_ALIASES = {
    "possibly_eligible": EligibilityStatus.POTENTIALLY_ELIGIBLE,
    "ineligible": EligibilityStatus.NOT_ELIGIBLE,
    "more_information_needed": EligibilityStatus.INSUFFICIENT_INFORMATION,
    "manual_review_required": EligibilityStatus.MANUAL_REVIEW,
}

VALID_ELIGIBILITY_STATUSES = frozenset(
    {
        EligibilityStatus.ELIGIBLE,
        EligibilityStatus.POTENTIALLY_ELIGIBLE,
        EligibilityStatus.NOT_ELIGIBLE,
        EligibilityStatus.INSUFFICIENT_INFORMATION,
        EligibilityStatus.NOT_APPLICABLE,
        EligibilityStatus.MANUAL_REVIEW,
    }
)


class CriterionState(str):
    """The ONE canonical per-criterion evaluation vocabulary.

    ``NOT_APPLICABLE`` means the rule was in scope for the scheme but its
    precondition (a ``when`` / ``requirement`` guard) did not hold, so it
    neither passes nor fails and must never count as a failure.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


VALID_CRITERION_STATES = frozenset(
    {
        CriterionState.PASS,
        CriterionState.FAIL,
        CriterionState.UNKNOWN,
        CriterionState.NOT_APPLICABLE,
    }
)


def normalize_eligibility_status(value: object) -> str:
    """Return the canonical status string for any stored/legacy value.

    Unknown values are returned unchanged so callers can decide how to treat
    them; they are never silently coerced into a decisive status.
    """
    text = str(value or "").strip().lower().replace(" ", "_")
    if not text:
        return ""
    if text in VALID_ELIGIBILITY_STATUSES:
        return text
    return _LEGACY_STATUS_ALIASES.get(text, text)


def is_recommendable_status(value: object) -> bool:
    """True when a status may still be surfaced to the citizen as a match."""
    return normalize_eligibility_status(value) in {
        EligibilityStatus.ELIGIBLE,
        EligibilityStatus.POTENTIALLY_ELIGIBLE,
        EligibilityStatus.INSUFFICIENT_INFORMATION,
    }


VALID_BENEFICIARY_SCOPES = {
    "INDIVIDUAL",
    "FAMILY",
    "FARMER",
    "ARTISAN",
    "ENTERPRISE",
    "MICRO_ENTERPRISE",
    "SHG",
    "FPO",
    "COMMUNITY",
    "STATE_UT",
    "LOCAL_BODY",
    "INSTITUTION",
    "MULTI_LEVEL",
    "OTHER",
}


VALID_RULE_TYPES = {
    "REQUIRED",
    "EXCLUSION",
    "CONDITIONAL",
    "ONE_OF",
    "ANY_OF",
    "ALL_OF",
    "THRESHOLD",
    "DOCUMENT_REQUIRED",
    "EVIDENCE_REQUIRED",
    "PROGRAM_LEVEL",
    "SCHEME_SPECIFIC",
}


VALID_OPERATORS = {
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "not_in",
    "exists",
    "not_exists",
    "any_of",
    "all_of",
    "conditional",
    "manual_review",
}


class EvidenceSource(BaseModel):
    """Reference to source document evidence for an eligibility criterion."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: Optional[str] = None
    scheme_id: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    text: Optional[str] = None


class EligibilityRuleSource(BaseModel):
    """Traceability metadata for one catalogue rule."""

    model_config = ConfigDict(from_attributes=True)

    document: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    text: Optional[str] = None


class StructuredEligibilityRule(BaseModel):
    """Machine-readable catalogue rule derived from a scheme document.

    ``profile_field`` is optional because some valid scheme requirements are
    not currently represented by the citizen profile schema. Those are still
    retained so the catalogue can report missing profile coverage explicitly.
    """

    model_config = ConfigDict(from_attributes=True)

    rule_id: str
    field: str
    operator: str
    value: Optional[Any] = None
    rule_type: str
    severity: str = "mandatory"
    profile_field: Optional[str] = None
    source: EligibilityRuleSource
    notes: Optional[str] = None
    beneficiary_scope: Optional[str] = None
    when: Optional[dict[str, Any]] = None
    requirement: Optional[dict[str, Any]] = None


class SchemeEligibilityCatalogueEntry(BaseModel):
    """Canonical catalogue entry for one scheme PDF."""

    model_config = ConfigDict(from_attributes=True)

    scheme_id: str
    scheme_name: str
    pdf_filename: str
    alternate_pdf_filenames: List[str] = Field(default_factory=list)
    beneficiary_scope: str
    eligibility_available: bool
    structured_rules_exist: bool = False
    extraction_status: str = "review_required"
    rules: List[StructuredEligibilityRule] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    missing_profile_fields: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class SchemeEligibility(BaseModel):
    """Structured eligibility criteria for a single government scheme.

    Fields are Optional because the source PDF may not contain the information.
    Missing fields mean the scheme document does not specify that criterion.
    """

    model_config = ConfigDict(from_attributes=True)

    scheme_name: str
    scheme_id: str
    beneficiary_scope: str = "INDIVIDUAL"

    # Target beneficiary groups explicitly mentioned
    target_groups: List[str] = Field(default_factory=list)
    occupations: List[str] = Field(default_factory=list)

    # Geographic scope
    states: List[str] = Field(default_factory=list)
    government_level: Optional[str] = None

    # Land-related criteria
    land_required: Optional[bool] = None
    land_type: List[str] = Field(default_factory=list)
    land_min_acres: Optional[float] = None
    land_max_acres: Optional[float] = None
    land_ownership_types: List[str] = Field(default_factory=list)

    # Economic criteria
    income_max: Optional[float] = None
    income_category_exclusions: List[str] = Field(default_factory=list)

    # Demographic criteria
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender: Optional[str] = None
    social_categories: List[str] = Field(default_factory=list)

    # Activity/crop criteria
    activity_types: List[str] = Field(default_factory=list)
    crop_types: List[str] = Field(default_factory=list)

    # Documents and process
    required_documents: List[str] = Field(default_factory=list)
    application_conditions: List[str] = Field(default_factory=list)

    # Evidence traceability
    evidence_sources: List[EvidenceSource] = Field(default_factory=list)


class EligibilityConditionResult(BaseModel):
    """Result of evaluating a single eligibility condition."""

    condition: str
    passed: bool
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    evidence: List[EvidenceSource] = Field(default_factory=list)
    mandatory: bool = True
    rule_id: Optional[str] = None
    field: Optional[str] = None
    operator: Optional[str] = None
    rule_type: Optional[str] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    source_document: Optional[str] = None


class EligibilityResult(BaseModel):
    """Complete eligibility evaluation result for a citizen against a scheme."""

    scheme_name: str
    scheme_id: str
    status: str
    matched_conditions: List[EligibilityConditionResult] = Field(default_factory=list)
    failed_conditions: List[EligibilityConditionResult] = Field(default_factory=list)
    missing_information: List[EligibilityConditionResult] = Field(default_factory=list)
    evidence: List[EvidenceSource] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    evaluation_status: str = "evaluated"
    eligibility_percentage: float = 0.0
    mandatory_rules_total: int = 0
    mandatory_rules_passed: int = 0

    # Canonical citizen-evidence snapshot used for this evaluation, keyed by
    # canonical evidence type (``aadhaar``, ``land_record``, ``farmer_id`` ...)
    # with an ``EvidenceState`` value. This is what lets the UI distinguish
    # verified / pending / missing evidence instead of guessing from raw
    # requirement keys. Empty when evaluated without a canonical evidence layer.
    evidence_states: dict[str, str] = Field(default_factory=dict)
    # Raw document-type strings that could NOT be canonicalized. They are
    # reported explicitly and are never silently matched to a requirement.
    unmapped_document_types: List[str] = Field(default_factory=list)

    def has_mandatory_failures(self) -> bool:
        return any(not c.passed and c.mandatory for c in self.failed_conditions)

    def has_missing_mandatory(self) -> bool:
        return any(c.mandatory for c in self.missing_information)


def determine_status(result: EligibilityResult) -> str:
    """Determine the canonical overall status from criterion results.

    Logic (order matters):

    1. ``evaluation_status == "manual_review_required"`` -> ``MANUAL_REVIEW``.
       This is the explicit, citizen-visible representation of a scheme whose
       rules cannot be machine-verified (programme-level scope, extraction not
       safe, or a document that must be assessed by an officer).
    2. Any mandatory criterion FAILED -> ``NOT_ELIGIBLE``.
    3. No mandatory criteria at all -> ``POTENTIALLY_ELIGIBLE`` (nothing to
       disprove eligibility; a zero-rule scheme is never claimed as eligible).
    4. Every mandatory criterion is ``NOT_APPLICABLE`` -> ``NOT_APPLICABLE``.
    5. Any mandatory criterion UNKNOWN -> ``INSUFFICIENT_INFORMATION``
       (never converted to FAIL just to look decisive).
    6. All mandatory criteria PASS -> ``ELIGIBLE``.
    7. Otherwise -> ``POTENTIALLY_ELIGIBLE``.
    """
    if str(getattr(result, "evaluation_status", "") or "") == "manual_review_required":
        return EligibilityStatus.MANUAL_REVIEW

    if result.has_mandatory_failures():
        return EligibilityStatus.NOT_ELIGIBLE

    if result.mandatory_rules_total == 0:
        # A scheme with no mandatory criteria at all has nothing to disprove
        # eligibility, so it is never claimed as eligible. If the only
        # criteria present were all non-applicable, say so explicitly.
        if any(
            str(getattr(c, "result", "") or "") == CriterionState.NOT_APPLICABLE
            for c in result.matched_conditions
        ):
            return EligibilityStatus.NOT_APPLICABLE
        return EligibilityStatus.POTENTIALLY_ELIGIBLE

    if result.has_missing_mandatory():
        return EligibilityStatus.INSUFFICIENT_INFORMATION

    if result.mandatory_rules_passed == result.mandatory_rules_total:
        return EligibilityStatus.ELIGIBLE

    return EligibilityStatus.POTENTIALLY_ELIGIBLE
