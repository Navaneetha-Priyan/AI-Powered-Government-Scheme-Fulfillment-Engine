"""Integration tests for Module 4 recommendation APIs."""
from types import SimpleNamespace

from app.core.jwt import create_access_token
from app.models.citizen import Citizen
from app.models.citizen_profile import CitizenProfile
from app.models.government_scheme import GovernmentScheme
from app.services import government_scheme_service as scheme_service_module


class FakeSearchService:
    def __init__(self, scheme_id: str):
        self.scheme_id = scheme_id

    def semantic_search(self, query, limit=5, category=None):
        del query, limit, category
        return [
            {
                "scheme_id": self.scheme_id,
                "scheme_name": "PM Kisan Support",
                "category": "agriculture",
                "department": "Agriculture Department",
                "similarity_score": 0.96,
                "matched_content": "Small and marginal farmers receive annual support.",
                "relevant_content": "Small and marginal farmers receive annual support.",
                "benefits": "Annual income support",
                "page_number": 1,
                "section_name": "Eligibility",
                "document_id": "document-1",
            }
        ]


def create_profile(test_db, citizen_id: str):
    profile = CitizenProfile(
        citizen_id=citizen_id,
        father_name="Ravi Kumar",
        mother_name="Lakshmi Devi",
        occupation="Farmer",
        annual_income=85000,
        income_category="bpl",
        caste="Vanniyar",
        community="MBC",
        is_disabled=False,
        is_farmer=True,
        education_level="10th",
        family_member_count=4,
        profile_completion_percentage=90,
        sync_status="synced",
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


def create_scheme(test_db):
    scheme = GovernmentScheme(
        scheme_name="PM Kisan Support",
        description="Income support for eligible farmers.",
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
    test_db.add(scheme)
    test_db.commit()
    test_db.refresh(scheme)
    return scheme


def create_citizen(test_db):
    citizen = Citizen(
        email="test.rec@example.com",
        phone="9876543999",
        password_hash="placeholder-hash",
        full_name="Recommendation User",
        district="Chennai",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    token = create_access_token({"sub": citizen.id, "email": citizen.email, "role": "citizen"})
    return citizen, {"Authorization": f"Bearer {token}"}


def test_recommendation_apis_require_authentication(client):
    assert client.get("/api/recommendations").status_code == 401


def test_generate_and_fetch_recommendations(client, test_db, monkeypatch):
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    scheme = create_scheme(test_db)

    monkeypatch.setattr(scheme_service_module.GovernmentSchemeService, "semantic_search", lambda self, query, limit=5, category=None: FakeSearchService(scheme.id).semantic_search(query, limit, category))

    generate_response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert generate_response.status_code == 201, generate_response.json()
    payload = generate_response.json()["data"]
    assert payload["eligible_count"] >= 1
    assert payload["recommendations"][0]["scheme_name"] == "PM Kisan Support"
    assert payload["recommendations"][0]["eligibility_status"] == "eligible"

    latest_response = client.get("/api/recommendations", headers=auth_headers)
    assert latest_response.status_code == 200
    assert latest_response.json()["data"]["recommendations"][0]["scheme_name"] == "PM Kisan Support"

    recommendation_id = latest_response.json()["data"]["recommendations"][0]["id"]
    detail_response = client.get(f"/api/recommendations/{recommendation_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["scheme_name"] == "PM Kisan Support"

    history_response = client.get("/api/recommendations/history", headers=auth_headers)
    assert history_response.status_code == 200
    assert len(history_response.json()["data"]) >= 1

    eligibility_response = client.get(
        "/api/eligibility/check",
        headers=auth_headers,
        params={"scheme_id": scheme.id},
    )
    assert eligibility_response.status_code == 200
    assert eligibility_response.json()["data"]["eligible"] is True

    rules_response = client.get("/api/eligibility/rules", headers=auth_headers)
    assert rules_response.status_code == 200
    assert len(rules_response.json()["data"]) >= 1