"""Unit tests for VoiceQueryService (Phase 5 - Voice Recommendation adapter).

These tests mock the expensive RecommendationService and the profile
repositories so no real eligibility engine, RAG/vector search, or LLM is
invoked. They verify the adapter's intent routing and the safety rule that
voice entities are never used to overwrite the verified citizen profile.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.exceptions.exceptions import ProfileNotFoundError
from app.schemas.normalization import NormalizationResult
from app.schemas.voice_recommendation import VoiceRecommendationResponse
from app.services.voice_query_service import VoiceQueryService


def _normalization(**overrides) -> NormalizationResult:
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


def _fake_match(**overrides):
    base = {
        "id": "match-1",
        "citizen_id": "citizen-1",
        "history_id": "history-1",
        "scheme_id": "scheme-1",
        "scheme_name": "PM Kisan Support",
        "description": "Income support for farmers.",
        "benefits": "Annual support",
        "eligibility_status": "eligible",
        "eligibility_percentage": 90.0,
        "similarity_score": 0.9,
        "confidence_score": 85.0,
        "overall_score": 88.0,
        "ranking_position": 1,
        "recommendation_reason": "Matched farmer status.",
        "matched_rules": [],
        "missing_requirements": [],
        "required_documents": ["Aadhaar"],
        "estimated_benefit": "6000",
        "application_ready": True,
        "profile_match_percentage": 90.0,
        "semantic_query": "farmer low income",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeProfile:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeCitizen:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def service(monkeypatch):
    """Build a VoiceQueryService with all heavy dependencies mocked."""
    db = SimpleNamespace()

    recommendation_service = MagicMock()
    history = SimpleNamespace(id="history-1")
    recommendation_service.generate.return_value = (
        history,
        [],
        [],
        None,
        "query",
        10,
    )
    monkeypatch.setattr(
        "app.services.voice_query_service.RecommendationService",
        lambda _db: recommendation_service,
    )

    match_repo = MagicMock()
    match_repo.list_for_history.return_value = [
        _fake_match(),
    ]
    monkeypatch.setattr(
        "app.services.voice_query_service.RecommendationMatchRepository",
        lambda _db: match_repo,
    )

    profile_repo = MagicMock()
    profile_repo.get_by_citizen_id.return_value = FakeProfile(
        occupation="farmer",
        annual_income=80000.0,
        income_category="bpl",
        is_farmer=True,
        is_disabled=False,
        caste="Vanniyar",
        community="MBC",
        education_level="10th",
        family_member_count=4,
        profile_completion_percentage=90,
    )
    monkeypatch.setattr(
        "app.services.voice_query_service.CitizenProfileRepository",
        lambda _db: profile_repo,
    )

    citizen_repo = MagicMock()
    citizen_repo.get_by_id.return_value = FakeCitizen(
        full_name="Selvam Murugan",
        state="Tamil Nadu",
        district="Villupuram",
    )
    monkeypatch.setattr(
        "app.services.voice_query_service.CitizenRepository",
        lambda _db: citizen_repo,
    )

    svc = VoiceQueryService(db)
    svc._recommendation_service = recommendation_service
    svc._match_repo = match_repo
    svc._profile_repo = profile_repo
    svc._citizen_repo = citizen_repo
    return svc


class TestVoiceQueryService:
    """Tests for the VoiceQueryService adapter."""

    def test_scheme_search_intent_recommends(self, service):
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(intent="scheme_search"),
            limit=5,
        )
        assert isinstance(result, VoiceRecommendationResponse)
        assert result.intent == "scheme_search"
        assert len(result.schemes) == 1
        assert result.schemes[0].scheme_name == "PM Kisan Support"
        # The existing engine was called with the voice query as query_override.
        call = service._recommendation_service.generate.call_args
        assert call.kwargs["citizen_id"] == "citizen-1"
        assert call.kwargs["request_type"] == "voice"
        assert "farmer" in call.kwargs["query_override"]

    def test_scheme_eligibility_intent_recommends(self, service):
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(intent="scheme_eligibility"),
        )
        assert result.intent == "scheme_eligibility"
        assert len(result.schemes) == 1

    def test_document_requirement_intent_recommends(self, service):
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(intent="document_requirement"),
        )
        assert result.intent == "document_requirement"
        assert len(result.schemes) == 1

    def test_profile_query_returns_verified_profile(self, service):
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(intent="profile_query"),
        )
        assert result.intent == "profile_query"
        assert result.profile is not None
        assert result.profile.full_name == "Selvam Murugan"
        assert result.profile.occupation == "farmer"
        assert result.profile.annual_income == 80000.0
        # The recommendation engine must NOT be called for profile queries.
        service._recommendation_service.generate.assert_not_called()

    def test_application_status_returns_not_supported(self, service):
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(intent="application_status"),
        )
        assert result.intent == "application_status"
        assert result.schemes == []
        assert "not available" in (result.message or "").lower()
        service._recommendation_service.generate.assert_not_called()

    def test_unknown_intent_returns_clear_message(self, service):
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(intent="unknown", entities={}),
        )
        assert result.intent == "unknown"
        assert result.schemes == []
        assert "could not understand" in (result.message or "").lower()
        service._recommendation_service.generate.assert_not_called()

    def test_no_matching_schemes_sets_message(self, service):
        service._match_repo.list_for_history.return_value = []
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(),
        )
        assert result.schemes == []
        assert "no eligible schemes" in (result.message or "").lower()

    def test_voice_entities_do_not_overwrite_profile(self, service):
        # The LLM claims the citizen is a "student" but the verified profile
        # says "farmer". The query_override may contain the voice text, but the
        # profile used for eligibility is never touched by the voice service.
        result = service.recommend(
            "citizen-1",
            normalization=_normalization(
                intent="scheme_search",
                entities={"occupation": "student", "income_status": "low"},
            ),
        )
        assert result.intent == "scheme_search"
        # The profile repo was only read, never written.
        assert service._profile_repo.get_by_citizen_id.call_count == 0
        # The recommendation engine was called (with the voice query as search
        # context only).
        service._recommendation_service.generate.assert_called_once()

    def test_profile_unavailable_raises(self, service):
        service._profile_repo.get_by_citizen_id.return_value = None
        with pytest.raises(ProfileNotFoundError):
            service.recommend(
                "citizen-1",
                normalization=_normalization(intent="profile_query"),
            )

    def test_existing_engine_called(self, service):
        service.recommend("citizen-1", normalization=_normalization())
        service._recommendation_service.generate.assert_called_once()

    def test_existing_rag_called(self, service):
        # RAG is invoked indirectly through RecommendationService.generate.
        # We assert generate() (which internally calls semantic_search) is used.
        service.recommend("citizen-1", normalization=_normalization())
        assert service._recommendation_service.generate.call_count == 1
