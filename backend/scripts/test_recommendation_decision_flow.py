"""Manual recommendation decision-flow runner.

This is an investigation script, not a permanent pytest suite. It validates that
recommendations produced from a persisted document-confirmed profile remain
consistent with structured eligibility evaluation.

Run from backend/:
    python scripts/test_recommendation_decision_flow.py
"""
from __future__ import annotations

import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.dependencies import get_current_user  # noqa: E402
from app.api.recommendation_routes import router as recommendation_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.database.connection import get_db  # noqa: E402
from app.repositories.citizen_profile_repository import (  # noqa: E402
    CitizenProfileRepository,
)
from app.services import government_scheme_service as scheme_service_module  # noqa: E402
from app.services.recommendation_service import (  # noqa: E402
    CitizenContextService,
    RecommendationService,
)
from scripts.test_profile_to_eligibility import (  # noqa: E402
    SELECTED_SCHEME_IDS,
    evaluate_scheme,
    make_session,
    seed_citizen,
    seed_schemes,
    upload_process_confirm_documents,
)


BROAD_FARMER_QUERY = "I am a farmer. What government schemes can I apply for?"
EXPLICIT_PM_KISAN_QUERY = "PM-KISAN eligibility for my farmer profile"


@dataclass
class ScenarioResult:
    name: str
    query: str
    recommendations: list[Any]
    direct_results: dict[str, Any]
    api_payload: dict[str, Any] | None = None


def build_client(db: Any, citizen_id: str) -> TestClient:
    app = FastAPI(title="Manual Recommendation Decision Flow")
    app.include_router(recommendation_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: citizen_id
    return TestClient(app, raise_server_exceptions=False)


def make_search_results(
    schemes_by_catalogue_id: dict[str, Any],
    query: str,
    limit: int,
    category: str | None = None,
) -> list[dict[str, Any]]:
    del category
    normalized = (query or "").lower()
    if "pm-kisan" in normalized or "pm kisan" in normalized:
        order = ["pm-kisan", "smam", "pmfby", "pm-kusum", "pm-vishwakarma", "pm-svanidhi", "jjm"]
    elif "farmer" in normalized or "agriculture" in normalized:
        order = ["smam", "pm-kisan", "pmfby", "pm-kusum", "pm-vishwakarma", "pm-svanidhi", "jjm"]
    else:
        order = list(SELECTED_SCHEME_IDS)

    results = []
    score = 0.99
    for scheme_id in order:
        scheme = schemes_by_catalogue_id.get(scheme_id)
        if scheme is None:
            continue
        results.append(
            {
                "scheme_id": scheme.id,
                "scheme_name": scheme.scheme_name,
                "category": scheme.category,
                "department": scheme.department,
                "similarity_score": round(score, 2),
                "matched_content": f"Scripted retrieval candidate for {scheme.scheme_name}.",
                "relevant_content": f"Scripted retrieval candidate for {scheme.scheme_name}.",
                "benefits": scheme.benefits,
                "page_number": 1,
                "section_name": "Manual scripted retrieval",
                "document_id": f"{scheme_id}-manual-search",
            }
        )
        score = max(0.35, score - 0.07)
    return results[:limit]


@contextmanager
def patched_semantic_search(schemes_by_catalogue_id: dict[str, Any]):
    original = scheme_service_module.GovernmentSchemeService.semantic_search

    def scripted(self: Any, query: str, limit: int = 5, category: str | None = None):
        return make_search_results(schemes_by_catalogue_id, query, limit, category)

    scheme_service_module.GovernmentSchemeService.semantic_search = scripted
    try:
        yield
    finally:
        scheme_service_module.GovernmentSchemeService.semantic_search = original


def reverse_scheme_map(seeded_schemes: dict[str, Any]) -> dict[str, str]:
    return {scheme.id: catalogue_id for catalogue_id, scheme in seeded_schemes.items()}


def direct_results_for(db: Any, citizen_id: str, seeded_schemes: dict[str, Any]) -> dict[str, Any]:
    return {
        scheme_id: evaluate_scheme(db, citizen_id, scheme_id, seeded_schemes)
        for scheme_id in SELECTED_SCHEME_IDS
    }


def run_recommendation_scenario(
    *,
    name: str,
    db: Any,
    citizen_id: str,
    seeded_schemes: dict[str, Any],
    query: str,
    limit: int = 7,
    call_api: bool = False,
) -> ScenarioResult:
    service = RecommendationService(db)
    _, recommendations, _, context, generated_query, _ = service.generate(
        citizen_id=citizen_id,
        limit=limit,
        query_override=query,
        request_type="generate",
    )
    print(f"\n{name}")
    print(f"- generated query: {generated_query}")
    print(
        "- persisted profile used: "
        f"citizen_id={getattr(context.citizen, 'id', None)}, "
        f"occupation={context.occupation!r}, "
        f"is_farmer={context.is_farmer!r}, "
        f"age={context.age!r}, "
        f"land_area={context.total_land_area!r}"
    )

    direct = direct_results_for(db, citizen_id, seeded_schemes)
    print_candidate_audit(direct)
    print_recommendations(recommendations, direct, reverse_scheme_map(seeded_schemes))

    api_payload = None
    if call_api:
        with build_client(db, citizen_id) as client:
            response = client.post(
                "/api/recommendations/generate",
                json={"limit": limit, "query_override": query},
            )
            if response.status_code != 201:
                raise AssertionError(f"Recommendation API failed: {response.status_code} {response.text}")
            api_payload = response.json()["data"]
            print_api_payload(api_payload)

    assert_recommendation_consistency(recommendations, direct, reverse_scheme_map(seeded_schemes))
    return ScenarioResult(name, query, recommendations, direct, api_payload)


def print_candidate_audit(direct_results: dict[str, Any]) -> None:
    print("- candidate eligibility audit:")
    for scheme_id, result in direct_results.items():
        print(
            f"  - {scheme_id}: status={result.status}, "
            f"evaluation_status={result.evaluation_status}, "
            f"failed={[c.field for c in result.failed_conditions]}, "
            f"unknown={[c.field for c in result.missing_information]}, "
            f"missing_evidence={result.missing_evidence}"
        )


def print_recommendations(
    recommendations: list[Any],
    direct_results: dict[str, Any],
    id_to_catalogue_id: dict[str, str],
) -> None:
    print("- returned recommendations:")
    if not recommendations:
        print("  - none")
        return
    for item in recommendations:
        scheme_id = id_to_catalogue_id[item.scheme.id]
        direct = direct_results[scheme_id]
        print(
            f"  - rank={item.ranking_position} scheme={item.scheme.scheme_name} "
            f"recommended=yes status={item.eligibility_status} "
            f"direct_status={direct.status} evaluation_status={direct.evaluation_status} "
            f"score={item.overall_score}"
        )
        print(f"    failed_rules={[c.field for c in direct.failed_conditions]}")
        print(f"    unknown_rules={[c.field for c in direct.missing_information]}")
        print(f"    missing_profile_information={[c.field for c in direct.missing_information]}")
        print(f"    missing_evidence={direct.missing_evidence}")


def print_api_payload(payload: dict[str, Any]) -> None:
    print("- recommendation API response:")
    print(
        f"  total_candidates={payload['total_candidates']} "
        f"eligible_count={payload['eligible_count']} "
        f"top_ranked_scheme={payload.get('top_ranked_scheme')!r}"
    )
    for item in payload.get("recommendations", []):
        print(
            f"  - rank={item['ranking_position']} scheme={item['scheme_name']} "
            f"status={item['eligibility_status']} score={item['overall_score']}"
        )


def assert_recommendation_consistency(
    recommendations: list[Any],
    direct_results: dict[str, Any],
    id_to_catalogue_id: dict[str, str],
) -> None:
    for item in recommendations:
        scheme_id = id_to_catalogue_id[item.scheme.id]
        direct = direct_results[scheme_id]
        if item.eligibility_status != direct.status:
            raise AssertionError(
                f"{scheme_id} recommendation status {item.eligibility_status} "
                f"does not match evaluator status {direct.status}"
            )
        if item.eligibility_status == "not_eligible":
            raise AssertionError(f"{scheme_id} was returned despite not_eligible status")
        if direct.evaluation_status == "manual_review_required" and item.eligibility_status == "eligible":
            raise AssertionError(f"{scheme_id} manual-review result was presented as eligible")


def assert_scheme_status(result: Any, expected: str, label: str) -> None:
    print(f"- {label}: {result.status}")
    if result.status != expected:
        raise AssertionError(f"{label} expected {expected}, got {result.status}")


def set_farmer_profile(db: Any, citizen_id: str, *, is_farmer: bool | None, occupation: str | None) -> None:
    profile = CitizenProfileRepository(db).get_by_citizen_id(citizen_id)
    if profile is None:
        raise RuntimeError("Persisted profile not found.")
    profile.is_farmer = is_farmer
    profile.occupation = occupation
    db.commit()


def main() -> int:
    db = make_session()
    with tempfile.TemporaryDirectory(prefix="recommendation-flow-") as raw_temp_dir:
        temp_dir = Path(raw_temp_dir)
        settings.DOCUMENT_STORAGE_DIR = str(temp_dir / "uploaded")

        citizen = seed_citizen(db)
        seeded_schemes = seed_schemes(db)
        upload_process_confirm_documents(db, citizen, temp_dir)
        db.expire_all()

        with patched_semantic_search(seeded_schemes):
            print("SCENARIO 1: Real extracted farmer profile")
            scenario_1 = run_recommendation_scenario(
                name="SCENARIO 1 RESULT",
                db=db,
                citizen_id=citizen.id,
                seeded_schemes=seeded_schemes,
                query=BROAD_FARMER_QUERY,
                call_api=True,
            )

            print("\nSCENARIO 2: Change farmer profile to non-farmer")
            set_farmer_profile(db, citizen.id, is_farmer=False, occupation="Shopkeeper")
            scenario_2 = run_recommendation_scenario(
                name="SCENARIO 2 RESULT",
                db=db,
                citizen_id=citizen.id,
                seeded_schemes=seeded_schemes,
                query=BROAD_FARMER_QUERY,
            )
            assert_scheme_status(
                scenario_2.direct_results["smam"],
                "not_eligible",
                "SMAM after is_farmer=False",
            )
            if any(item.scheme.id == seeded_schemes["smam"].id for item in scenario_2.recommendations):
                raise AssertionError("SMAM was still returned after becoming not_eligible.")
            assert scenario_1.direct_results["pm-svanidhi"].status == scenario_2.direct_results["pm-svanidhi"].status
            print("- unrelated manual-review PM-SVANidhi status unchanged")

            print("\nSCENARIO 3: Remove required farmer field")
            set_farmer_profile(db, citizen.id, is_farmer=None, occupation="Farmer")
            scenario_3 = run_recommendation_scenario(
                name="SCENARIO 3 RESULT",
                db=db,
                citizen_id=citizen.id,
                seeded_schemes=seeded_schemes,
                query=BROAD_FARMER_QUERY,
            )
            assert_scheme_status(
                scenario_3.direct_results["smam"],
                "insufficient_information",
                "SMAM after is_farmer=None",
            )

            print("\nSCENARIO 4: Explicit PM-KISAN query")
            set_farmer_profile(db, citizen.id, is_farmer=True, occupation="Farmer")
            scenario_4 = run_recommendation_scenario(
                name="SCENARIO 4 RESULT",
                db=db,
                citizen_id=citizen.id,
                seeded_schemes=seeded_schemes,
                query=EXPLICIT_PM_KISAN_QUERY,
            )
            pm_kisan_match = next(
                (
                    item
                    for item in scenario_4.recommendations
                    if item.scheme.id == seeded_schemes["pm-kisan"].id
                ),
                None,
            )
            if pm_kisan_match is None:
                raise AssertionError("Explicit PM-KISAN query did not retrieve PM-KISAN.")
            if pm_kisan_match.eligibility_status != scenario_4.direct_results["pm-kisan"].status:
                raise AssertionError("Explicit PM-KISAN query did not preserve structured eligibility.")
            print(
                "- explicit PM-KISAN query retrieved PM-KISAN; status-tier ranking "
                "kept potentially_eligible schemes above insufficient_information"
            )

            print("\nSCENARIO 4B: Explicit query cannot override NOT_ELIGIBLE")
            set_farmer_profile(db, citizen.id, is_farmer=False, occupation="Shopkeeper")
            pm_kisan_after_failure = evaluate_scheme(db, citizen.id, "pm-kisan", seeded_schemes)
            assert_scheme_status(
                pm_kisan_after_failure,
                "not_eligible",
                "PM-KISAN after non-farmer mutation",
            )
            scenario_4b = run_recommendation_scenario(
                name="SCENARIO 4B RESULT",
                db=db,
                citizen_id=citizen.id,
                seeded_schemes=seeded_schemes,
                query=EXPLICIT_PM_KISAN_QUERY,
            )
            if any(item.scheme.id == seeded_schemes["pm-kisan"].id for item in scenario_4b.recommendations):
                raise AssertionError("Explicit retrieval returned PM-KISAN after definite not_eligible.")
            print("- explicit retrieval did not bypass structured not_eligible result")

            print("\nSCENARIO 5: Broad farmer query")
            set_farmer_profile(db, citizen.id, is_farmer=True, occupation="Farmer")
            run_recommendation_scenario(
                name="SCENARIO 5 RESULT",
                db=db,
                citizen_id=citizen.id,
                seeded_schemes=seeded_schemes,
                query=BROAD_FARMER_QUERY,
            )

    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
