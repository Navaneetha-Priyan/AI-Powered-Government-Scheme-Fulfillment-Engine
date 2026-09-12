"""Tests for catalogue-driven structured eligibility evaluation."""
from __future__ import annotations

from types import SimpleNamespace

from app.models.scheme_eligibility import (
    EligibilityRuleSource,
    SchemeEligibilityCatalogueEntry,
    StructuredEligibilityRule,
)
from app.services.eligibility_catalog_service import get_catalogue_entry
from app.services.eligibility_evaluator import EligibilityEvaluator
from app.services.recommendation_service import CitizenContext


def _source():
    return EligibilityRuleSource(
        document="test.pdf",
        section_name="Eligibility",
        text="Synthetic test source.",
    )


def _rule(**kwargs):
    base = {
        "rule_id": "rule-1",
        "field": "age",
        "operator": ">=",
        "value": 18,
        "rule_type": "THRESHOLD",
        "severity": "mandatory",
        "profile_field": "context.age",
        "source": _source(),
        "beneficiary_scope": "INDIVIDUAL",
    }
    base.update(kwargs)
    return StructuredEligibilityRule(**base)


def _entry(**kwargs):
    base = {
        "scheme_id": "test-scheme",
        "scheme_name": "Test Scheme",
        "pdf_filename": "test.pdf",
        "beneficiary_scope": "INDIVIDUAL",
        "eligibility_available": True,
        "structured_rules_exist": True,
        "extraction_status": "structured",
        "rules": [_rule()],
        "evidence_requirements": [],
        "missing_profile_fields": [],
    }
    base.update(kwargs)
    return SchemeEligibilityCatalogueEntry(**base)


def _land(**kwargs):
    base = {"land_type": "agricultural", "ownership_type": "owned", "land_area": 2.5}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _context(
    *,
    age=35,
    occupation="farmer",
    is_farmer=True,
    gender="male",
    land_records=None,
    document_types=None,
    extra_profile=None,
):
    profile_values = {
        "occupation": occupation,
        "annual_income": 150000,
        "income_category": "bpl",
        "is_farmer": is_farmer,
        "caste": "",
        "community": "",
        "profile_completion_percentage": 80,
    }
    profile_values.update(extra_profile or {})
    profile = SimpleNamespace(**profile_values)
    citizen = SimpleNamespace(state="Tamil Nadu", district="Villupuram", gender=gender)
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
        document_types=set(document_types or []),
        document_names=set(),
    )


def test_required_rule_passes():
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        _entry(),
        _context(age=35),
    )
    assert result.status == "eligible"
    assert result.matched_conditions[0].result == "PASS"


def test_required_rule_fails():
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        _entry(),
        _context(age=16),
    )
    assert result.status == "not_eligible"
    assert result.failed_conditions[0].result == "FAIL"


def test_required_rule_unknown_is_insufficient_information():
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        _entry(),
        _context(age=None),
    )
    assert result.status == "insufficient_information"
    assert result.missing_information[0].result == "UNKNOWN"


def test_exclusion_passes_when_condition_does_not_apply():
    entry = _entry(
        rules=[
            _rule(
                rule_id="not-government-employee",
                field="government_employee_status",
                operator="!=",
                value=True,
                rule_type="EXCLUSION",
                profile_field="profile.government_employee",
            )
        ]
    )
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        entry,
        _context(extra_profile={"government_employee": False}),
    )
    assert result.status == "eligible"
    assert result.matched_conditions[0].rule_type == "EXCLUSION"


def test_exclusion_triggers_not_eligible_when_condition_applies():
    entry = _entry(
        rules=[
            _rule(
                rule_id="not-income-tax-payer",
                field="income_tax_payer",
                operator="!=",
                value=True,
                rule_type="EXCLUSION",
                profile_field="profile.income_tax_payer",
            )
        ]
    )
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        entry,
        _context(extra_profile={"income_tax_payer": True}),
    )
    assert result.status == "not_eligible"
    assert result.failed_conditions[0].result == "FAIL"


def test_exclusion_unknown_is_not_treated_as_fail():
    entry = _entry(
        rules=[
            _rule(
                rule_id="not-income-tax-payer",
                field="income_tax_payer",
                operator="!=",
                value=True,
                rule_type="EXCLUSION",
                profile_field="profile.income_tax_payer",
            )
        ]
    )
    result = EligibilityEvaluator().evaluate_catalogue_entry(entry, _context())
    assert result.status == "insufficient_information"
    assert not result.failed_conditions


def test_in_not_in_one_of_any_of_all_of_operators():
    evaluator = EligibilityEvaluator()
    assert evaluator.evaluate_catalogue_entry(
        _entry(rules=[_rule(field="occupation", operator="in", value=["farmer"], rule_type="ONE_OF", profile_field="profile.occupation")]),
        _context(occupation="cultivator farmer"),
    ).status == "eligible"
    assert evaluator.evaluate_catalogue_entry(
        _entry(rules=[_rule(field="occupation", operator="not_in", value=["teacher"], rule_type="EXCLUSION", profile_field="profile.occupation")]),
        _context(occupation="farmer"),
    ).status == "eligible"
    assert evaluator.evaluate_catalogue_entry(
        _entry(rules=[_rule(field="documents", operator="all_of", value=["aadhaar", "bank_account"], rule_type="ALL_OF", profile_field="document_types")]),
        _context(document_types={"aadhaar", "bank_account"}),
    ).status == "eligible"


def test_conditional_rule_unknown_when_trigger_field_missing():
    entry = get_catalogue_entry("pm-rkvy-pkvy")
    result = EligibilityEvaluator().evaluate_catalogue_entry(entry, _context())
    assert result.status == "insufficient_information"
    assert any(rule.rule_id == "pm-rkvy-pkvy-organic-component" for rule in result.missing_information)


def test_missing_profile_field_becomes_unknown():
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        _entry(rules=[_rule(field="pregnancy_status", operator="==", value=True, rule_type="REQUIRED", profile_field=None)]),
        _context(gender="female"),
    )
    assert result.status == "insufficient_information"
    assert result.missing_information[0].field == "pregnancy_status"


def test_non_individual_scope_requires_manual_review():
    entry = _entry(beneficiary_scope="COMMUNITY")
    result = EligibilityEvaluator().evaluate_catalogue_entry(entry, _context())
    assert result.status == "insufficient_information"
    assert result.evaluation_status == "manual_review_required"


def test_review_required_entry_is_not_evaluated():
    entry = _entry(extraction_status="review_required", rules=[])
    result = EligibilityEvaluator().evaluate_catalogue_entry(entry, _context())
    assert result.status == "insufficient_information"
    assert result.missing_information[0].operator == "manual_review"


def test_missing_evidence_does_not_make_not_eligible():
    entry = _entry(evidence_requirements=["aadhaar", "bank_account"])
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        entry,
        _context(age=35, document_types={"aadhaar"}),
    )
    assert result.status == "potentially_eligible"
    assert result.missing_evidence == ["bank_account"]


def test_explainable_output_contains_rule_metadata_and_evidence():
    result = EligibilityEvaluator().evaluate_catalogue_entry(
        _entry(),
        _context(age=35),
    )
    condition = result.matched_conditions[0]
    assert condition.rule_id == "rule-1"
    assert condition.operator == ">="
    assert condition.result == "PASS"
    assert condition.evidence[0].document_id == "test.pdf"
