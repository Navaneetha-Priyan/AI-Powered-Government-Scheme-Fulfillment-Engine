"""Validation tests for the structured eligibility catalogue."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from app.models.scheme_eligibility import (
    VALID_BENEFICIARY_SCOPES,
    VALID_OPERATORS,
    VALID_RULE_TYPES,
)
from app.models.scheme_rules import PMFME_ELIGIBILITY, PM_KISAN_ELIGIBILITY
from app.services.eligibility_catalog_service import load_eligibility_catalogue
from app.services.eligibility_evaluator import EligibilityEvaluator
from app.services.recommendation_service import CitizenContext


DATA_DIR = Path(__file__).resolve().parents[2] / "data"

ALLOWED_PROFILE_FIELDS = {
    None,
    "context.age",
    "citizen.gender",
    "citizen.state",
    "citizen.district",
    "citizen.village",
    "citizen.aadhaar_number",
    "citizen.smart_ration_card",
    "profile.annual_income",
    "profile.income_category",
    "profile.occupation",
    "profile.nationality",
    "profile.caste",
    "profile.community",
    "profile.is_disabled",
    "profile.is_farmer",
    "profile.farmer_id",
    "profile.education_level",
    "profile.family_member_count",
    "land_records.land_area",
    "land_records.land_type",
    "land_records.ownership_type",
    "land_records.survey_number",
    "land_records.village",
    "land_records.district",
    "land_records.state",
    "land_records.patta_number",
}


def _land(**kwargs):
    base = {
        "land_type": "agricultural",
        "ownership_type": "owned",
        "land_area": 2.0,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _context(
    *,
    age=None,
    occupation="farmer",
    is_farmer=True,
    income_category="bpl",
    gender="male",
    land_records=None,
):
    citizen = SimpleNamespace(
        state="Tamil Nadu",
        district="Villupuram",
        village="Sample",
        gender=gender,
    )
    profile = SimpleNamespace(
        occupation=occupation,
        annual_income=150000,
        income_category=income_category,
        is_farmer=is_farmer,
        caste="",
        community="",
        education_level="10th",
        family_member_count=4,
        profile_completion_percentage=80,
    )
    records = land_records or []
    return CitizenContext(
        citizen=citizen,
        profile=profile,
        land_records=records,
        documents=[],
        total_land_area=sum(float(getattr(item, "land_area", 0) or 0) for item in records),
        profile_completion_percentage=80,
        age=age,
        senior_citizen=bool(age is not None and age >= 60),
        family_size=4,
        document_types=set(),
        document_names=set(),
    )


def test_catalogue_has_unique_non_empty_scheme_entries():
    entries = load_eligibility_catalogue()
    assert entries

    scheme_ids = [entry.scheme_id for entry in entries]
    assert len(scheme_ids) == len(set(scheme_ids))
    assert all(entry.scheme_name for entry in entries)
    assert all(entry.pdf_filename for entry in entries)


def test_catalogue_references_existing_pdf_documents():
    entries = load_eligibility_catalogue()
    known_documents = {path.name for path in DATA_DIR.glob("*.pdf")}

    covered_documents = set()
    for entry in entries:
        assert entry.pdf_filename in known_documents
        covered_documents.add(entry.pdf_filename)
        for alternate in entry.alternate_pdf_filenames:
            assert alternate in known_documents
            covered_documents.add(alternate)

    assert known_documents == covered_documents


def test_rule_ids_types_operators_sources_and_scopes_are_valid():
    for entry in load_eligibility_catalogue():
        assert entry.beneficiary_scope in VALID_BENEFICIARY_SCOPES

        rule_ids = [rule.rule_id for rule in entry.rules]
        assert len(rule_ids) == len(set(rule_ids))

        for rule in entry.rules:
            assert rule.rule_type in VALID_RULE_TYPES
            assert rule.operator in VALID_OPERATORS
            assert rule.source.document == entry.pdf_filename
            assert rule.source.section_name or rule.source.page_number is not None
            assert rule.profile_field in ALLOWED_PROFILE_FIELDS
            if rule.beneficiary_scope:
                assert rule.beneficiary_scope in VALID_BENEFICIARY_SCOPES
            if rule.rule_type == "CONDITIONAL":
                assert rule.when
                assert rule.requirement
            if rule.rule_type == "EXCLUSION":
                assert rule.operator in {"!=", "not_in", "not_exists"}


def test_no_duplicate_rule_meanings_within_a_scheme():
    for entry in load_eligibility_catalogue():
        meanings = [
            (rule.field, rule.operator, str(rule.value), rule.rule_type)
            for rule in entry.rules
        ]
        duplicates = [item for item, count in Counter(meanings).items() if count > 1]
        assert not duplicates


def test_review_required_entries_explain_missing_machine_rules():
    for entry in load_eligibility_catalogue():
        if not entry.rules:
            assert entry.extraction_status in {"review_required", "manual_review_required"}
            assert entry.notes


def test_exclusion_rules_are_separate_from_required_rules():
    exclusion_rules = [
        rule
        for entry in load_eligibility_catalogue()
        for rule in entry.rules
        if rule.rule_type == "EXCLUSION"
    ]
    assert exclusion_rules
    assert all(rule.rule_type != "REQUIRED" for rule in exclusion_rules)


def test_sample_evaluation_demonstrates_core_statuses():
    evaluator = EligibilityEvaluator()

    eligible_farmer = evaluator.evaluate(
        PM_KISAN_ELIGIBILITY,
        _context(age=35, land_records=[_land()]),
    )
    ineligible_artisan_for_farmer_scheme = evaluator.evaluate(
        PM_KISAN_ELIGIBILITY,
        _context(
            age=25,
            occupation="artisan",
            is_farmer=False,
            land_records=[_land(land_type="residential")],
        ),
    )
    missing_farmer = evaluator.evaluate(
        PM_KISAN_ELIGIBILITY,
        _context(age=None, land_records=[]),
    )
    enterprise_ready = evaluator.evaluate(
        PMFME_ELIGIBILITY,
        _context(age=30, occupation="food processing entrepreneur", is_farmer=False),
    )

    assert eligible_farmer.status == "eligible"
    assert ineligible_artisan_for_farmer_scheme.status == "not_eligible"
    assert missing_farmer.status == "insufficient_information"
    assert enterprise_ready.status == "eligible"
