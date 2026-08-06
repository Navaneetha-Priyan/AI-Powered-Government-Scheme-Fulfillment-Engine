"""Unit tests for Module 4 eligibility and recommendation services."""
from types import SimpleNamespace

from app.models.government_scheme import GovernmentScheme
from app.services.recommendation_service import CitizenContext, EligibilityEngineService, RuleDefinition, RuleEvaluationService, RankingService


def build_context():
    citizen = SimpleNamespace(
        id="citizen-1",
        full_name="Selvam Murugan",
        state="Tamil Nadu",
        district="Villupuram",
        village="Periyakulam",
        date_of_birth=None,
    )
    profile = SimpleNamespace(
        annual_income=85000,
        occupation="Farmer",
        is_farmer=True,
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
        land_records=[],
        documents=[],
        total_land_area=3.2,
        profile_completion_percentage=82,
        age=34,
        senior_citizen=False,
        family_size=4,
        document_types={"aadhaar", "smart_ration_card"},
        document_names={"aadhaar card", "ration card"},
    )


def test_rule_evaluation_supports_numeric_and_boolean_rules():
    context = build_context()
    service = RuleEvaluationService()

    income_rule = RuleDefinition(code="income-rule", condition="annual_income", operator="<=", value=200000, priority=1)
    farmer_rule = RuleDefinition(code="farmer-rule", condition="is_farmer", operator="==", value=True, priority=2)

    income_result = service.evaluate(context, income_rule)
    farmer_result = service.evaluate(context, farmer_rule)

    assert income_result.passed is True
    assert farmer_result.passed is True


def test_ranking_service_combines_scores():
    ranking_service = RankingService()
    score = ranking_service.score(
        eligibility_percentage=95,
        similarity_score=92,
        benefit_score=80,
        profile_match_percentage=85,
        document_score=100,
        state_bonus=5,
        recency_bonus=2.5,
    )

    assert score > 80


def test_eligibility_engine_infers_dynamic_rules():
    context = build_context()
    engine = EligibilityEngineService.__new__(EligibilityEngineService)
    engine.REQUIRED_DOCUMENT_KEYWORDS = EligibilityEngineService.REQUIRED_DOCUMENT_KEYWORDS
    scheme = GovernmentScheme(
        id="scheme-1",
        scheme_name="PM Kisan Support",
        description="Income support for small and marginal farmers.",
        category="agriculture",
        department="Agriculture Department",
        government_level="central",
        state="Tamil Nadu",
        benefits="Annual income support",
        eligibility_summary="Small and marginal farmers",
        required_documents="Aadhaar, land record",
        application_process="Apply online",
        language="en",
        status="active",
        is_deleted=False,
    )
    candidate = SimpleNamespace(scheme=scheme, semantic_score=0.97, chunks=[], aggregated_text="Small and marginal farmers eligible with income limit 200000")

    rules = EligibilityEngineService._infer_dynamic_rules(engine, candidate)
    assert any(rule.condition == "is_farmer" for rule in rules)
    assert any(rule.condition == "annual_income" for rule in rules)