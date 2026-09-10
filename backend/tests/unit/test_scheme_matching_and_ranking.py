"""Regression tests for scheme-name matching and the recommendation pipeline.

Covers:
  1. PM Kisan alias matching
  2. PM Fasal Bima / PMFBY alias matching
  3. A rank-1 eligible PM KISAN retrieval remains recommended
  4. A rank-1 eligible PMFBY retrieval remains recommended
  5. An actually ineligible scheme is still filtered out
  6. An unrelated adjacent scheme does not outrank an eligible exact-match
     merely because of a generic similarity score.
"""
import os
import sys
from types import SimpleNamespace

import pytest

# Make the evaluation harness importable for alias-matching tests.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from app.models.government_scheme import GovernmentScheme  # noqa: E402
from app.services.eligibility_evaluator import EligibilityEvaluator  # noqa: E402
from app.services.recommendation_service import (  # noqa: E402
    CitizenContext,
    RecommendationService,
)

# Also import the harness matcher for alias tests.
from evaluate_voice_offline import canonical_scheme_key, schemes_equivalent  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────────

def _scheme(name, description="Benefits for farmers.", category="agriculture",
            department="Agriculture", level="central", language="en",
            required_documents="Aadhaar, land record",
            eligibility_summary="Small and marginal farmers",
            benefits="Financial assistance"):
    return GovernmentScheme(
        scheme_name=name,
        description=description,
        category=category,
        department=department,
        government_level=level,
        language=language,
        status="active",
        is_deleted=False,
        required_documents=required_documents,
        eligibility_summary=eligibility_summary,
        benefits=benefits,
        application_process="Apply online",
    )


def _context(is_farmer=True, income=85000, occupation="Farmer", state="Tamil Nadu",
             land_records=None):
    citizen = SimpleNamespace(
        id="citizen-1",
        full_name="Selvam Murugan",
        state=state,
        district="Villupuram",
        village="Periyakulam",
    )
    profile = SimpleNamespace(
        annual_income=income,
        occupation=occupation,
        is_farmer=is_farmer,
        is_disabled=False,
        income_category="bpl",
        caste="Vanniyar",
        community="MBC",
        family_member_count=4,
        profile_completion_percentage=82,
        education_level="10th",
        marital_status="married",
    )
    return CitizenContext(
        citizen=citizen,
        profile=profile,
        land_records=land_records or [],
        documents=[],
        total_land_area=1.5,
        profile_completion_percentage=82,
        age=41,
        senior_citizen=False,
        family_size=4,
        document_types={"aadhaar", "smart_ration_card"},
        document_names={"aadhaar card", "ration card"},
    )


# ── 1 & 2. Alias matching ──────────────────────────────────────────────────

@pytest.mark.parametrize("expected_name, catalog_name", [
    ("PM Kisan", "PM KISAN Operational Guidelines"),
    ("PM Fasal Bima", "PMFBY Scheme Document"),
    ("PMFBY", "Pradhan Mantri Fasal Bima Yojana"),
    ("PM Kusum", "PM KUSUM Guidelines"),
    ("PM RKVY", "PM RKVY and PKVY Guidelines"),
    ("SMAM", "SMAM Operational Guidelines 2025"),
    ("MIDH", "MIDH Operational Guidelines 2025"),
])
def test_scheme_alias_matching(expected_name, catalog_name):
    """Ground-truth names must resolve to the catalog scheme."""
    assert schemes_equivalent(expected_name, catalog_name) is True


@pytest.mark.parametrize("name_a, name_b", [
    ("PM Kisan", "PM KUSUM Guidelines"),
    ("PM Fasal Bima", "Unified Package Insurance Scheme Guidelines"),
    ("Crop Insurance", "PMFBY Scheme Document"),
    ("SMAM", "MIDH Operational Guidelines 2025"),
])
def test_aliases_do_not_equate_unrelated_schemes(name_a, name_b):
    """Distinct schemes must never collapse into one another."""
    assert schemes_equivalent(name_a, name_b) is False


def test_canonical_id_preferred_when_available():
    """When both sides carry a scheme_id, identity takes precedence."""
    assert schemes_equivalent("X", "Y", expected_scheme_id="abc", actual_scheme_id="abc") is True
    assert schemes_equivalent("PM Kisan", "PM KISAN Operational Guidelines",
                             expected_scheme_id="a", actual_scheme_id="b") is False


# ── 3-6. Pipeline tests (ranking + eligibility filter) ──────────────────────

@pytest.fixture
def setup_db(test_db):
    """Seed three schemes into the in-memory test database."""
    kisan = _scheme("PM KISAN Operational Guidelines")
    pmfby = _scheme("PMFBY Scheme Document")
    unified = _scheme(
        "Unified Package Insurance Scheme Guidelines",
        description="Package insurance scheme for farmers and rural households.",
        required_documents="Aadhaar",
        eligibility_summary="Farmers and rural households",
        benefits="Insurance coverage",
    )
    for s in (kisan, pmfby, unified):
        test_db.add(s)
    test_db.commit()
    test_db.refresh(kisan)
    test_db.refresh(pmfby)
    test_db.refresh(unified)
    return {"pm-kisan": kisan, "pmfby": pmfby, "unified": unified}


def _search_result(scheme, similarity):
    return {
        "scheme_id": scheme.id,
        "scheme_name": scheme.scheme_name,
        "similarity_score": similarity,
        "matched_content": f"{scheme.scheme_name} {scheme.eligibility_summary}",
        "relevant_content": scheme.eligibility_summary,
        "score": similarity,
    }


def _run(svc, context, query, search_results, limit=5, request_type="generate"):
    svc.context_service.build = lambda _cid: context
    svc.scheme_service.semantic_search = lambda _q, **_kw: search_results
    _, recommendations, *_ = svc.generate(
        "citizen-1", query_override=query, limit=limit, request_type=request_type,
    )
    return [r.scheme.scheme_name for r in recommendations]


def test_voice_farmer_discovery_keeps_relevant_schemes_when_profile_is_incomplete(test_db, setup_db):
    """Broad voice discovery shows retrieved farmer schemes before eligibility is complete."""
    ctx = _context(is_farmer=False, occupation="", land_records=[])
    svc = RecommendationService(test_db)
    results = _run(
        svc,
        ctx,
        "I need government schemes for farmer",
        [_search_result(setup_db["pm-kisan"], 0.68), _search_result(setup_db["pmfby"], 0.65)],
        request_type="voice",
    )
    assert results


def test_rank1_eligible_pm_kisan_remains_recommended(test_db, setup_db):
    """Eligible PM KISAN must be recommended even when a non-matching
    scheme has a higher generic similarity score (req 3 + 6)."""
    ctx = _context(land_records=[SimpleNamespace(land_type="cultivable",
                                                ownership_type="owned",
                                                land_area=1.5)])
    svc = RecommendationService(test_db)
    results = _run(
        svc, ctx,
        "I am eligible for PM Kisan scheme",
        [
            _search_result(setup_db["pm-kisan"], 0.68),
            _search_result(setup_db["unified"], 0.95),  # higher generic similarity
        ],
    )
    assert "PM KISAN Operational Guidelines" in results
    # Eligible exact-match must outrank the higher-similarity adjacent scheme.
    assert results[0] == "PM KISAN Operational Guidelines"


def test_rank1_eligible_pmfby_remains_recommended(test_db, setup_db):
    """Eligible PMFBY must be recommended (req 4)."""
    ctx = _context(land_records=[SimpleNamespace(land_type="agricultural",
                                                ownership_type="owned",
                                                land_area=1.5)])
    svc = RecommendationService(test_db)
    results = _run(
        svc, ctx,
        "Am I eligible for PMFBY?",
        [_search_result(setup_db["pmfby"], 0.68)],
    )
    assert results[0] == "PMFBY Scheme Document"


def test_ineligible_scheme_still_filtered_out(test_db, setup_db):
    """A scheme with KNOWN non-qualifying land ownership must be filtered (req 5).

    PM KISAN requires owned/inherited land; a leased record is a definitive
    failure, not missing information.
    """
    ctx = _context(land_records=[SimpleNamespace(land_type="cultivable",
                                                ownership_type="leased",  # known fail
                                                land_area=1.5)])
    svc = RecommendationService(test_db)
    results = _run(
        svc, ctx,
        "I am eligible for PM Kisan scheme",
        [
            _search_result(setup_db["pm-kisan"], 0.68),
            _search_result(setup_db["unified"], 0.70),
        ],
    )
    assert "PM KISAN Operational Guidelines" not in results
    assert "Unified Package Insurance Scheme Guidelines" in results


def test_unknown_land_type_is_missing_not_failed(test_db, setup_db):
    """Unknown land type must keep the scheme visible (pending info) without
    collapsing into a hard failure — the behavior recordings 24/28 depend on."""
    ctx = _context(land_records=[SimpleNamespace(land_type=None,
                                                ownership_type="owned",
                                                land_area=1.5)])
    evaluator = EligibilityEvaluator()
    from app.models.scheme_rules import get_scheme_eligibility_for_scheme
    result = evaluator.evaluate(
        get_scheme_eligibility_for_scheme(setup_db["pm-kisan"]), ctx,
    )
    assert result.status in {"insufficient_information", "potentially_eligible"}
    assert "land" in [c.condition for c in result.missing_information]


@pytest.mark.parametrize("name_a, name_b", [
    ("PM Kisan", "PM KUSUM Guidelines"),
    ("PM Fasal Bima", "Unified Package Insurance Scheme Guidelines"),
    ("Crop Insurance", "PMFBY Scheme Document"),
    ("SMAM", "MIDH Operational Guidelines 2025"),
])
def test_aliases_do_not_equate_unrelated_schemes(name_a, name_b):
    """Distinct schemes must never collapse into one another."""
    assert schemes_equivalent(name_a, name_b) is False


def test_canonical_id_preferred_when_available():
    """When both sides carry a scheme_id, identity takes precedence."""
    assert schemes_equivalent("X", "Y", expected_scheme_id="abc", actual_scheme_id="abc") is True
    assert schemes_equivalent("PM Kisan", "PM KISAN Operational Guidelines",
                             expected_scheme_id="a", actual_scheme_id="b") is False
