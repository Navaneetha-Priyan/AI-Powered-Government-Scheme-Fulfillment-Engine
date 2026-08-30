"""Structured eligibility rules for the 7 MVP farmer-focused government schemes.

These rules are based on explicit scheme PDF analysis. All fields are optional
because not every scheme document provides every criterion.
Missing fields mean the scheme document does not specify that criterion.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.models.government_scheme import GovernmentScheme
from app.models.scheme_eligibility import (
    EligibilityStatus,
    EvidenceSource,
    SchemeEligibility,
)


def _evidence(chunk_id: str, scheme_id: str, page: int, section: str, text: str) -> EvidenceSource:
    return EvidenceSource(
        chunk_id=chunk_id,
        scheme_id=scheme_id,
        page_number=page,
        section_name=section,
        text=text,
    )


# ── PM-KISAN ────────────────────────────────────────────────────────────────
PM_KISAN_ELIGIBILITY = SchemeEligibility(
    scheme_name="PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
    scheme_id="pm-kisan",
    target_groups=["landholding farmer families"],
    occupations=["farmer", "cultivator"],
    states=[],  # Central scheme - all states
    government_level="central",
    land_required=True,
    land_type=["cultivable"],
    land_ownership_types=["owned", "inherited"],
    income_category_exclusions=[
        "income_tax_payer",
        "constitutional_post_holder",
        "government_employee",
        "pensioner_above_threshold",
        "professional_category",
    ],
    age_min=18,
    social_categories=[],  # No specific social category restriction
    activity_types=["farming", "cultivation"],
    crop_types=[],  # No specific crop restriction
    required_documents=[
        "aadhaar",
        "land_record",
        "bank_account",
    ],
    application_conditions=[
        "landholder name must match land records",
        "institutional landholders excluded",
        "constitutional post holders excluded",
        "certain government employees excluded",
        "pensioners above documented threshold excluded",
        "income tax payers excluded",
        "specified professional categories excluded",
        "applicable cut-off date conditions apply",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="pmkisan-p1-eligibility",
            scheme_id="pm-kisan",
            page=1,
            section="Eligibility Criteria",
            text="All landholding farmer families having cultivable land are eligible. Institutional landholders excluded. Constitutional post holders excluded. Serving/retired government employees excluded. Pensioners above Rs 10,000/month excluded. Income tax payers excluded. Professionals like doctors, engineers, lawyers, architects excluded.",
        ),
    ],
)


# ── PM-KUSUM ────────────────────────────────────────────────────────────────
PM_KUSUM_ELIGIBILITY = SchemeEligibility(
    scheme_name="PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan)",
    scheme_id="pm-kusum",
    target_groups=["farmers", "farmer groups", "FPOs", "panchayats", "water_user_associations"],
    occupations=["farmer"],
    states=[],  # Central scheme
    government_level="central",
    land_required=True,
    land_type=["barren", "uncultivable", "agricultural"],
    land_ownership_types=["owned", "leased"],
    age_min=18,
    activity_types=["solar_power_generation", "solar_pump_installation"],
    crop_types=[],
    required_documents=[
        "aadhaar",
        "land_record",
        "land_lease_agreement",  # if leased
        "bank_account",
    ],
    application_conditions=[
        "barren/uncultivable land preferred for solar plants",
        "agricultural land allowed for solar pumps in specified configurations",
        "land lease agreement required if land is leased",
        "distance from substation criteria apply for feeder level solarization",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="pmkusum-p1-eligibility",
            scheme_id="pm-kusum",
            page=1,
            section="Eligibility",
            text="Farmers, group of farmers, cooperatives, panchayats, FPOs, Water User Associations eligible. Barren/uncultivable land preferred for Component A. Agricultural land allowed for Components B and C. Land lease agreement required for leased land. Distance from substation criteria for feeder solarization.",
        ),
    ],
)


# ── PMFBY ───────────────────────────────────────────────────────────────────
PMFBY_ELIGIBILITY = SchemeEligibility(
    scheme_name="PMFBY (Pradhan Mantri Fasal Bima Yojana)",
    scheme_id="pmfby",
    target_groups=["farmers", "loanee_farmers", "non_loanee_farmers", "sharecroppers", "tenant_farmers"],
    occupations=["farmer", "cultivator"],
    states=[],  # Central scheme with state notification
    government_level="central",
    land_required=True,
    land_type=["agricultural"],
    land_ownership_types=["owned", "leased", "sharecropped", "tenant"],
    activity_types=["crop_cultivation"],
    crop_types=["notified_crops"],  # Only notified crops for the season/area
    required_documents=[
        "aadhaar",
        "land_record",
        "bank_account",
        "sowing_certificate",
    ],
    application_conditions=[
        "insurable interest in the crop",
        "crop must be notified for the area/season",
        "sharecroppers/tenant farmers need supported land records",
        "loanee farmers automatically covered through banks",
        "non-loanee farmers must register voluntarily",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="pmfby-p1-eligibility",
            scheme_id="pmfby",
            page=1,
            section="Eligibility",
            text="All farmers including loanee, non-loanee, sharecroppers, tenant farmers growing notified crops. Insurable interest required. Notified crop requirement for the specific area and season. Land records required for tenant/sharecropper farmers.",
        ),
    ],
)


# ── PM-RKVY / PKVY ──────────────────────────────────────────────────────────
PM_RKVY_PKVY_ELIGIBILITY = SchemeEligibility(
    scheme_name="PM-RKVY / PKVY (Paramparagat Krishi Vikas Yojana / Rashtriya Krishi Vikas Yojana)",
    scheme_id="pm-rkvy-pkvy",
    target_groups=["small_marginal_farmers", "FPOs", "SHGs", "cooperatives"],
    occupations=["farmer"],
    states=[],  # Central scheme
    government_level="central",
    land_required=True,
    land_type=["agricultural"],
    land_ownership_types=["owned", "leased"],
    activity_types=["organic_farming", "cluster_farming", "sustainable_agriculture"],
    crop_types=[],  # Various crops
    required_documents=[
        "aadhaar",
        "land_record",
        "bank_account",
        "pgs_certificate",  # PGS certification where explicitly required
    ],
    application_conditions=[
        "cluster-based approach for organic farming",
        "PGS certification where explicitly required",
        "small/marginal farmers prioritized",
        "FPOs/SHGs/cooperatives for collective farming",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="pmrkvy-p1-eligibility",
            scheme_id="pm-rkvy-pkvy",
            page=1,
            section="Eligibility",
            text="Small and marginal farmers, FPOs, SHGs, cooperatives. Cluster-based organic farming approach. PGS certification required for organic components. Not all farmers eligible for every component.",
        ),
    ],
)


# ── PMFME ───────────────────────────────────────────────────────────────────
PMFME_ELIGIBILITY = SchemeEligibility(
    scheme_name="PMFME (PM Formalisation of Micro food processing Enterprises)",
    scheme_id="pmfme",
    target_groups=["existing_micro_food_processing_unit_owners"],
    occupations=["food_processing_entrepreneur"],
    states=[],  # Central scheme
    government_level="central",
    land_required=False,
    age_min=18,
    activity_types=["food_processing"],
    crop_types=["odop_products"],  # One District One Product preference
    required_documents=[
        "aadhaar",
        "bank_account",
        "education_certificate",  # minimum 8th standard
        "unit_registration",
    ],
    application_conditions=[
        "existing unincorporated micro food processing unit",
        "fewer than 10 workers",
        "age above 18 years",
        "minimum 8th standard education",
        "one beneficiary per family",
        "ODOP (One District One Product) preference where applicable",
        "beneficiary contribution / loan conditions apply",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="pmfme-p1-eligibility",
            scheme_id="pmfme",
            page=1,
            section="Eligibility",
            text="Existing unincorporated micro food processing unit with less than 10 workers. Age above 18 years. Minimum 8th standard education. One beneficiary per family. ODOP preference. Beneficiary contribution required.",
        ),
    ],
)


# ── SMAM ────────────────────────────────────────────────────────────────────
SMAM_ELIGIBILITY = SchemeEligibility(
    scheme_name="SMAM (Sub-Mission on Agricultural Mechanization)",
    scheme_id="smam",
    target_groups=["small_marginal_farmers", "sc_st_farmers", "women_farmers", "ne_farmers", "fra_patta_holders"],
    occupations=["farmer"],
    states=[],  # Central scheme
    government_level="central",
    land_required=True,
    land_type=["agricultural"],
    land_ownership_types=["owned", "leased"],
    social_categories=["SC", "ST", "women", "NE", "FRA_patta_holders"],
    activity_types=["mechanization", "farm_machinery", "custom_hiring_centres"],
    crop_types=[],
    required_documents=[
        "aadhaar",
        "land_record",
        "bank_account",
        "caste_certificate",  # for SC/ST
    ],
    application_conditions=[
        "small/marginal farmer categories",
        "SC/ST/women/NE categories get higher subsidy",
        "FRA patta holders eligible where applicable",
        "mechanization/activity-specific conditions",
        "subsidy categories vary by equipment type",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="smam-p1-eligibility",
            scheme_id="smam",
            page=1,
            section="Eligibility",
            text="Small and marginal farmers, SC/ST, women, NE region farmers, FRA patta holders. Different subsidy rates for different categories. Activity-specific conditions for machinery types. Not all farmers eligible for every subsidy category.",
        ),
    ],
)


# ── MIDH ────────────────────────────────────────────────────────────────────
MIDH_ELIGIBILITY = SchemeEligibility(
    scheme_name="MIDH (Mission for Integrated Development of Horticulture)",
    scheme_id="midh",
    target_groups=["horticulture_farmers", "FPOs", "SHGs", "PRIs"],
    occupations=["farmer", "horticulture_farmer"],
    states=[],  # Central scheme with state-specific implementation
    government_level="central",
    land_required=True,
    land_type=["horticulture", "agricultural"],
    land_ownership_types=["owned", "leased"],
    activity_types=["horticulture_cultivation", "nursery", "post_harvest_management", "cold_chain"],
    crop_types=["horticulture_crops"],  # Fruits, vegetables, spices, flowers, etc.
    required_documents=[
        "aadhaar",
        "land_record",
        "bank_account",
    ],
    application_conditions=[
        "horticulture-related activities mandatory",
        "applicable geographic conditions (state-specific)",
        "FPOs/SHGs/PRIs for collective activities",
        "horticulture activity requirement",
    ],
    evidence_sources=[
        _evidence(
            chunk_id="midh-p1-eligibility",
            scheme_id="midh",
            page=1,
            section="Eligibility",
            text="Farmers engaged in horticulture activities. FPOs, SHGs, PRIs for collective activities. Geographic conditions apply per state. Horticulture activity is mandatory - not all farmers automatically eligible.",
        ),
    ],
)


# ── Registry of all 7 schemes ───────────────────────────────────────────────
SCHEME_ELIGIBILITY_REGISTRY: Dict[str, SchemeEligibility] = {
    "pm-kisan": PM_KISAN_ELIGIBILITY,
    "pm-kusum": PM_KUSUM_ELIGIBILITY,
    "pmfby": PMFBY_ELIGIBILITY,
    "pm-rkvy-pkvy": PM_RKVY_PKVY_ELIGIBILITY,
    "pmfme": PMFME_ELIGIBILITY,
    "smam": SMAM_ELIGIBILITY,
    "midh": MIDH_ELIGIBILITY,
}


def get_scheme_eligibility(scheme_id: str) -> Optional[SchemeEligibility]:
    """Get structured eligibility criteria for a scheme by ID."""
    return SCHEME_ELIGIBILITY_REGISTRY.get(scheme_id.lower())


def list_scheme_eligibilities() -> List[SchemeEligibility]:
    """List all registered scheme eligibility criteria."""
    return list(SCHEME_ELIGIBILITY_REGISTRY.values())


def get_eligible_schemes_for_farmer() -> List[str]:
    """Return scheme IDs that target farmers (for MVP filtering)."""
    return list(SCHEME_ELIGIBILITY_REGISTRY.keys())


# ── Scheme-to-Structured-Rule Mapping ────────────────────────────────────────
# Deterministic normalization and alias mapping to connect GovernmentScheme
# database records to structured eligibility rules in SCHEME_ELIGIBILITY_REGISTRY.

_SCHEME_ALIASES: Dict[str, str] = {
    # Explicit aliases for known naming variations
    "pm kisan": "pm-kisan",
    "pm-kisan": "pm-kisan",
    "pradhan mantri kisan samman nidhi": "pm-kisan",
    "pm kusum": "pm-kusum",
    "pm-kusum": "pm-kusum",
    "pradhan mantri kisan urja suraksha": "pm-kusum",
    "pmfby": "pmfby",
    "pradhan mantri fasal bima yojana": "pmfby",
    "pm rkvy": "pm-rkvy-pkvy",
    "pm-rkvy": "pm-rkvy-pkvy",
    "pm pkvy": "pm-rkvy-pkvy",
    "pm-pkvy": "pm-rkvy-pkvy",
    "pm rkvy pkvy": "pm-rkvy-pkvy",
    "pm-rkvy-pkvy": "pm-rkvy-pkvy",
    "paramparagat krishi vikas yojana": "pm-rkvy-pkvy",
    "rashtriya krishi vikas yojana": "pm-rkvy-pkvy",
    "pmfme": "pmfme",
    "pm formalisation of micro food processing": "pmfme",
    "smam": "smam",
    "sub mission on agricultural mechanization": "smam",
    "midh": "midh",
    "mission for integrated development of horticulture": "midh",
}


def _normalize_scheme_name(name: str) -> str:
    """Normalize a scheme name for deterministic matching.

    - Lowercase
    - Remove punctuation (except hyphens which are meaningful in IDs)
    - Collapse whitespace
    """
    if not name:
        return ""
    # Replace punctuation with spaces, keep hyphens
    normalized = re.sub(r"[^\w\s-]", " ", name.lower())
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_scheme_id(name: str) -> str:
    """Normalize a scheme name to an ID-like form for matching against registry keys."""
    normalized = _normalize_scheme_name(name)
    # Replace spaces with hyphens for ID comparison
    normalized = normalized.replace(" ", "-")
    # Collapse multiple hyphens
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


def get_scheme_eligibility_for_scheme(scheme: GovernmentScheme) -> Optional[SchemeEligibility]:
    """Look up structured eligibility rules for a GovernmentScheme.

    Uses deterministic normalization and explicit aliases to map the
    database scheme name to a structured rule ID.

    Returns None if no structured rule exists for the scheme.
    """
    if not scheme or not scheme.scheme_name:
        return None

    # Try explicit alias match first (most reliable)
    normalized_name = _normalize_scheme_name(scheme.scheme_name)
    if normalized_name in _SCHEME_ALIASES:
        rule_id = _SCHEME_ALIASES[normalized_name]
        return SCHEME_ELIGIBILITY_REGISTRY.get(rule_id)

    # Try normalized ID match
    normalized_id = _normalize_scheme_id(scheme.scheme_name)
    if normalized_id in SCHEME_ELIGIBILITY_REGISTRY:
        return SCHEME_ELIGIBILITY_REGISTRY[normalized_id]

    # Try partial match against known scheme IDs (for cases like
    # "PM KISAN Operational Guidelines" -> "pm-kisan")
    for rule_id in SCHEME_ELIGIBILITY_REGISTRY:
        # Check if the rule_id is contained in the normalized scheme name
        if rule_id in normalized_id or rule_id.replace("-", " ") in normalized_name:
            return SCHEME_ELIGIBILITY_REGISTRY[rule_id]

    return None