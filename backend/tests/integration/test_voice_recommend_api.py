"""Integration tests for POST /voice/recommend (Phase 5 - Voice recommendation).

These tests mock the normalization service (via app state) and the semantic
search (RAG) service so no real Ollama or vector store is invoked. They reuse
the same in-memory DB + auth fixtures from conftest.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.normalization import NormalizationResult
from app.services import government_scheme_service as scheme_service_module


def _fake_result(**overrides) -> NormalizationResult:
    base = {
        "language": "ta-en",
        "intent": "scheme_search",
        "normalized_text": "Looking for a farmer scheme with low income",
        "entities": {"occupation": "farmer", "income_status": "low"},
        "confidence": 0.9,
        "source": "llm",
    }
    base.update(overrides)
    return NormalizationResult(**base)


@pytest.fixture(autouse=True)
def mock_normalization_service(client: TestClient):
    """Replace the actual TextNormalizationService with a fake."""
    fake = MagicMock()
    fake.normalize.return_value = _fake_result()
    client.app.state.normalization_service = fake
    yield
    client.app.state.normalization_service = None


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
    from app.models.citizen_profile import CitizenProfile

    profile = CitizenProfile(
        citizen_id=citizen_id,
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
    from app.models.government_scheme import GovernmentScheme

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


def test_voice_recommend_requires_authentication(client):
    response = client.post("/voice/recommend", json={"text": "farmer scheme"})
    assert response.status_code == 401


def test_voice_recommend_rejects_no_text(client, auth_headers):
    response = client.post("/voice/recommend", json={}, headers=auth_headers)
    assert response.status_code == 422


def test_voice_recommend_scheme_search(client, test_db, monkeypatch):
    from app.core.jwt import create_access_token
    from app.models.citizen import Citizen

    citizen = Citizen(
        email="voice.search@example.com",
        phone="9876543888",
        password_hash="placeholder-hash",
        full_name="Voice Search User",
        district="Villupuram",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    create_profile(test_db, citizen.id)
    scheme = create_scheme(test_db)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': citizen.id})}"}

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(scheme.id).semantic_search(query, limit, category),
    )

    response = client.post(
        "/voice/recommend",
        json={
            "normalization": {
                "language": "ta-en",
                "intent": "scheme_search",
                "normalized_text": "Looking for a farmer scheme with low income",
                "entities": {"occupation": "farmer", "income_status": "low"},
                "confidence": 0.9,
                "source": "llm",
            }
        },
        headers=headers,
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["intent"] == "scheme_search"
    assert len(data["schemes"]) >= 1
    assert data["schemes"][0]["scheme_name"] == "PM Kisan Support"
    assert data["schemes"][0]["eligibility_status"] == "eligible"


def test_voice_recommend_scheme_eligibility(client, test_db, monkeypatch):
    from app.core.jwt import create_access_token
    from app.models.citizen import Citizen

    citizen = Citizen(
        email="voice.elig@example.com",
        phone="9876543887",
        password_hash="placeholder-hash",
        full_name="Voice Eligibility User",
        district="Villupuram",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    create_profile(test_db, citizen.id)
    scheme = create_scheme(test_db)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': citizen.id})}"}

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(scheme.id).semantic_search(query, limit, category),
    )

    response = client.post(
        "/voice/recommend",
        json={
            "normalization": {
                "language": "en",
                "intent": "scheme_eligibility",
                "normalized_text": "Am I eligible for PM Kisan?",
                "entities": {"scheme_name": "PM Kisan"},
                "confidence": 0.85,
                "source": "llm",
            }
        },
        headers=headers,
    )
    assert response.status_code == 200, response.json()
    assert response.json()["intent"] == "scheme_eligibility"


def test_voice_recommend_profile_query(client, test_db):
    from app.core.jwt import create_access_token
    from app.models.citizen import Citizen

    citizen = Citizen(
        email="voice.profile@example.com",
        phone="9876543886",
        password_hash="placeholder-hash",
        full_name="Voice Profile User",
        district="Villupuram",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    create_profile(test_db, citizen.id)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': citizen.id})}"}

    response = client.post(
        "/voice/recommend",
        json={
            "normalization": {
                "language": "en",
                "intent": "profile_query",
                "normalized_text": "What is my profile?",
                "entities": {},
                "confidence": 0.9,
                "source": "llm",
            }
        },
        headers=headers,
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["intent"] == "profile_query"
    assert data["profile"] is not None
    assert data["profile"]["occupation"] == "Farmer"
    assert data["profile"]["full_name"] == "Voice Profile User"


def test_voice_recommend_unsupported_intent(client, auth_headers):
    response = client.post(
        "/voice/recommend",
        json={
            "normalization": {
                "language": "en",
                "intent": "application_status",
                "normalized_text": "Where is my application?",
                "entities": {},
                "confidence": 0.8,
                "source": "llm",
            }
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["intent"] == "application_status"
    assert "not available" in (data.get("message") or "").lower()


def test_voice_recommend_no_matching_schemes(client, test_db, monkeypatch):
    from app.core.jwt import create_access_token
    from app.models.citizen import Citizen

    citizen = Citizen(
        email="voice.nomatch@example.com",
        phone="9876543885",
        password_hash="placeholder-hash",
        full_name="Voice No Match User",
        district="Villupuram",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    # A profile is required for the recommendation pipeline.
    create_profile(test_db, citizen.id)
    # No scheme is created, so no eligible matches.
    headers = {"Authorization": f"Bearer {create_access_token({'sub': citizen.id})}"}

    # Force the semantic search to return nothing.
    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: [],
    )

    response = client.post(
        "/voice/recommend",
        json={
            "normalization": {
                "language": "en",
                "intent": "scheme_search",
                "normalized_text": "some scheme",
                "entities": {},
                "confidence": 0.7,
                "source": "heuristic",
            }
        },
        headers=headers,
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["schemes"] == []
    # A message is returned rather than an error.
    assert "no eligible" in (data.get("message") or "").lower()


def test_voice_recommend_raw_text_normalizes(client, test_db, monkeypatch):
    from app.core.jwt import create_access_token
    from app.models.citizen import Citizen

    citizen = Citizen(
        email="voice.raw@example.com",
        phone="9876543884",
        password_hash="placeholder-hash",
        full_name="Voice Raw User",
        district="Villupuram",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    create_profile(test_db, citizen.id)
    scheme = create_scheme(test_db)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': citizen.id})}"}

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(scheme.id).semantic_search(query, limit, category),
    )

    # Mocked normalization service returns a scheme_search result.
    response = client.post(
        "/voice/recommend",
        json={"text": "enakku farmer scheme irukka?"},
        headers=headers,
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["intent"] == "scheme_search"
    assert len(data["schemes"]) >= 1
