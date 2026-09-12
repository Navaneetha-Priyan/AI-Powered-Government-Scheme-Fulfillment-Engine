"""Structured eligibility models for government schemes (Phase 2).

These models represent eligibility criteria extracted from scheme PDFs.
All fields are optional because not every scheme document provides every criterion.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EligibilityStatus(str):
    """Eligibility determination status."""

    ELIGIBLE = "eligible"
    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NOT_ELIGIBLE = "not_eligible"
    INSUFFICIENT_INFORMATION = "insufficient_information"


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

    def has_mandatory_failures(self) -> bool:
        return any(not c.passed and c.mandatory for c in self.failed_conditions)

    def has_missing_mandatory(self) -> bool:
        return any(c.mandatory for c in self.missing_information)


def determine_status(result: EligibilityResult) -> str:
    """Determine overall eligibility status from condition results.

    Logic:
    - If any mandatory condition failed -> not_eligible
    - If all mandatory passed and no missing mandatory -> eligible
    - If all mandatory passed but some mandatory missing -> potentially_eligible
    - If mandatory conditions missing information -> insufficient_information
    """
    if result.has_mandatory_failures():
        return EligibilityStatus.NOT_ELIGIBLE

    if result.mandatory_rules_total == 0:
        return EligibilityStatus.POTENTIALLY_ELIGIBLE

    if result.has_missing_mandatory():
        return EligibilityStatus.INSUFFICIENT_INFORMATION

    if result.mandatory_rules_passed == result.mandatory_rules_total:
        return EligibilityStatus.ELIGIBLE

    return EligibilityStatus.POTENTIALLY_ELIGIBLE
