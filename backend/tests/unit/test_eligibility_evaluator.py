"""Unit tests for the structured eligibility evaluator.

These tests verify the EligibilityEvaluator against the structured
SchemeEligibility rules and a CitizenContext built from simple fake objects.
No database, RAG, or LLM is involved.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models.scheme_eligibility import SchemeEligibility
from app.models.scheme_rules import PM_KISAN_ELIGIBILITY, PMFME_ELIGIBILITY
from app.services.eligibility_evaluator import EligibilityEvaluator
from app.services.recommendation_service import CitizenContext


def _land(**kwargs):
    base = {
        "land_type": "agricultural",
        "ownership_type": "owned",
        "land_area": 2.0,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _profile(**kwargs):
    base = {
        "occupation": "farmer",
        "annual_income": 50000.0,
        "income_category": "bpl",
        "is_farmer": True,
        "caste": "",
        "community": "",
        "sub_caste": None,
        "education_level": "10th",
        "family_member_count": 4,
        "profile_completion_percentage": 80,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _citizen(**kwargs):
    base = {
        "state": "Tamil Nadu",
        "district": "Villupuram",
        "gender": "male",
        "date_of_birth": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _context(
    profile=None,
    citizen=None,
    land_records=None,
    age=None,
    total_land_area=None,
):
    profile = profile or _profile()
    citizen = citizen or _citizen()
    land_records = land_records or []
    if total_land_area is None:
        total_land_area = sum(
            float(getattr(r, "land_area", 0.0) or 0.0) for r in land_records
        )
    return CitizenContext(
        citizen=citizen,
        profile=profile,
        land_records=land_records,
        documents=[],
        total_land_area=total_land_area,
        profile_completion_percentage=getattr(profile, "profile_completion_percentage", 0),
        age=age,
        senior_citizen=bool(age is not None and age >= 60),
        family_size=getattr(profile, "family_member_count", None),
        document_types=set(),
        document_names=set(),
    )


@pytest.fixture
def evaluator():
    return EligibilityEvaluator()


# ── 1. ELIGIBLE FARMER ────────────────────────────────────────────────────

class TestEligibleFarmer:
    def test_eligible_farmer_with_land_and_age(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Test Farmer Scheme",
            scheme_id="test-farmer",
            occupations=["farmer"],
            land_required=True,
            land_type=["agricultural"],
            land_ownership_types=["owned"],
            age_min=18,
        )
        context = _context(
            land_records=[_land(land_type="agricultural", ownership_type="owned", land_area=2.0)],
            age=35,
        )
        result = evaluator.evaluate(scheme, context)
        assert result.status == "eligible"
        assert result.eligibility_percentage == 100.0
        assert result.mandatory_rules_passed == result.mandatory_rules_total


# ── 2. LAND REQUIREMENT FAILED ──────────────────────────────────────────

class TestLandRequirementFailed:
    def test_land_requirement_failed_when_no_qualifying_land(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Land Scheme",
            scheme_id="land-scheme",
            occupations=["farmer"],
            land_required=True,
            land_type=["agricultural"],
        )
        # Citizen has a residential land record only — no qualifying land.
        context = _context(
            land_records=[_land(land_type="residential", land_area=1.0)],
            age=30,
        )
        result = evaluator.evaluate(scheme, context)
        assert result.status == "not_eligible"
        assert any(c.condition == "land" and not c.passed for c in result.failed_conditions)


# ── 3. LAND INFORMATION MISSING ─────────────────────────────────────────

class TestLandInformationMissing:
    def test_land_required_but_no_land_records_loaded(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Land Scheme",
            scheme_id="land-scheme",
            occupations=["farmer"],
            land_required=True,
            land_type=["agricultural"],
        )
        # No land records loaded at all.
        context = _context(land_records=[], age=30)
        result = evaluator.evaluate(scheme, context)
        assert result.status == "insufficient_information"
        assert any(c.condition == "land" for c in result.missing_information)


# ── 4. AGE FAILURE ──────────────────────────────────────────────────────

class TestAgeFailure:
    def test_age_below_minimum(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Age Scheme",
            scheme_id="age-scheme",
            occupations=["farmer"],
            age_min=18,
        )
        context = _context(age=16)
        result = evaluator.evaluate(scheme, context)
        assert result.status == "not_eligible"
        assert any(c.condition == "age" and not c.passed for c in result.failed_conditions)


# ── 5. AGE MISSING ──────────────────────────────────────────────────────

class TestAgeMissing:
    def test_age_unavailable(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Age Scheme",
            scheme_id="age-scheme",
            occupations=["farmer"],
            age_min=18,
        )
        context = _context(age=None)
        result = evaluator.evaluate(scheme, context)
        assert result.status == "insufficient_information"
        assert any(c.condition == "age" for c in result.missing_information)


# ── 6. MULTIPLE LAND RECORDS ────────────────────────────────────────────

class TestMultipleLandRecords:
    def test_any_agricultural_record_satisfies(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Agri Land Scheme",
            scheme_id="agri-land",
            occupations=["farmer"],
            land_required=True,
            land_type=["agricultural"],
        )
        context = _context(
            land_records=[
                _land(land_type="residential", land_area=1.0),
                _land(land_type="agricultural", land_area=3.0),
            ],
            age=40,
        )
        result = evaluator.evaluate(scheme, context)
        assert result.status == "eligible"
        assert any(c.condition == "land" and c.passed for c in result.matched_conditions)


# ── 7. OCCUPATION MISMATCH ──────────────────────────────────────────────

class TestOccupationMismatch:
    def test_non_farmer_occupation(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Farmer Scheme",
            scheme_id="farmer-scheme",
            occupations=["farmer"],
        )
        context = _context(profile=_profile(occupation="teacher", is_farmer=False))
        result = evaluator.evaluate(scheme, context)
        assert result.status == "not_eligible"
        assert any(c.condition == "occupation" and not c.passed for c in result.failed_conditions)


# ── 8. OCCUPATION UNKNOWN ───────────────────────────────────────────────

class TestOccupationUnknown:
    def test_occupation_missing(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Farmer Scheme",
            scheme_id="farmer-scheme",
            occupations=["farmer"],
        )
        context = _context(profile=_profile(occupation="", is_farmer=False))
        result = evaluator.evaluate(scheme, context)
        assert result.status == "insufficient_information"
        assert any(c.condition == "occupation" for c in result.missing_information)


# ── 9. OPTIONAL / PREFERENCE CRITERIA ───────────────────────────────────

class TestOptionalPreferenceCriteria:
    def test_not_in_priority_group_not_ineligible(self, evaluator):
        scheme = SchemeEligibility(
            scheme_name="Preference Scheme",
            scheme_id="preference-scheme",
            occupations=["farmer"],
            social_categories=["SC", "ST", "women"],
        )
        # Citizen is a farmer but not SC/ST/women.
        context = _context(
            profile=_profile(occupation="farmer", is_farmer=True, caste="Vanniyar", community="MBC"),
            age=30,
        )
        result = evaluator.evaluate(scheme, context)
        # Social category is a preference, not mandatory — citizen stays eligible.
        assert result.status == "eligible"
        all_conditions = (
            result.matched_conditions
            + result.failed_conditions
            + result.missing_information
        )
        assert not any(
            c.condition == "social_category" and c.mandatory for c in all_conditions
        )


# ── 10. REAL SCHEME RULE ────────────────────────────────────────────────

class TestRealSchemeRule:
    def test_pm_kisan_eligible_farmer(self, evaluator):
        context = _context(
            profile=_profile(occupation="farmer", is_farmer=True, annual_income=50000.0),
            land_records=[_land(land_type="agricultural", ownership_type="owned", land_area=2.0)],
            age=40,
        )
        result = evaluator.evaluate(PM_KISAN_ELIGIBILITY, context)
        assert result.scheme_id == "pm-kisan"
        assert result.status in {"eligible", "potentially_eligible"}

    def test_pmfme_eligible_entrepreneur(self, evaluator):
        context = _context(
            profile=_profile(occupation="food processing", is_farmer=False, annual_income=300000.0),
            age=30,
        )
        result = evaluator.evaluate(PMFME_ELIGIBILITY, context)
        assert result.scheme_id == "pmfme"
        assert result.status in {"eligible", "potentially_eligible"}