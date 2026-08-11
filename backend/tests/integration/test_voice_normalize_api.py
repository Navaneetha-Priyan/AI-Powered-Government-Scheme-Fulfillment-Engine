"""Integration tests for POST /voice/normalize (Phase 4 - Normalization).

These tests mock the TextNormalizationService via app state; they never make a
real HTTP call to Ollama.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.normalization import NormalizationResult


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


class TestVoiceNormalizeEndpoint:
    """Tests for POST /voice/normalize"""

    def _normalize(self, client: TestClient, auth_headers: dict, text: str):
        return client.post("/voice/normalize", json={"text": text}, headers=auth_headers)

    # ── Success cases ────────────────────────────────────────────────────

    def test_normalize_success(self, client: TestClient, auth_headers: dict):
        response = self._normalize(client, auth_headers, "எனக்கு விவசாய திட்டம் வேண்டும்")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "ta-en"
        assert data["intent"] == "scheme_search"
        assert data["entities"]["occupation"] == "farmer"
        assert data["source"] == "llm"
        assert 0.0 <= data["confidence"] <= 1.0

    def test_normalize_english(self, client: TestClient, auth_headers: dict):
        fake = client.app.state.normalization_service
        fake.normalize.return_value = _fake_result(language="en", source="heuristic")
        response = self._normalize(client, auth_headers, "I need a scheme for farming")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"
        assert data["source"] == "heuristic"

    def test_normalize_eligibility(self, client: TestClient, auth_headers: dict):
        fake = client.app.state.normalization_service
        fake.normalize.return_value = _fake_result(intent="scheme_eligibility")
        response = self._normalize(client, auth_headers, "PM Kisan eligible a?")
        assert response.status_code == 200
        assert response.json()["intent"] == "scheme_eligibility"

    # ── Authentication / validation ──────────────────────────────────────

    def test_requires_authentication(self, client: TestClient):
        response = client.post("/voice/normalize", json={"text": "some text"})
        assert response.status_code == 401

    def test_rejects_empty_text(self, client: TestClient, auth_headers: dict):
        response = self._normalize(client, auth_headers, "   ")
        assert response.status_code == 422

    def test_rejects_missing_text(self, client: TestClient, auth_headers: dict):
        response = client.post("/voice/normalize", json={}, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_too_long_text(self, client: TestClient, auth_headers: dict):
        long_text = "a" * 5000  # exceeds NORMALIZE_MAX_TEXT_LENGTH (2000)
        response = self._normalize(client, auth_headers, long_text)
        assert response.status_code == 422

    # ── Service exceptions propagate as 500 / 503 ────────────────────────

    def test_normalization_error_returns_500(self, client: TestClient, auth_headers: dict):
        from app.exceptions.exceptions import NormalizationError

        fake = client.app.state.normalization_service
        fake.normalize.side_effect = NormalizationError("boom")
        response = self._normalize(client, auth_headers, "some text")
        assert response.status_code == 500
        assert "NORMALIZATION_ERROR" in str(response.json())

    def test_llm_unavailable_falls_back(self, client: TestClient, auth_headers: dict):
        # Even if the LLM is unavailable, the service falls back to heuristic.
        fake = client.app.state.normalization_service
        fake.normalize.return_value = _fake_result(source="heuristic", confidence=0.55)
        response = self._normalize(client, auth_headers, "money kammi")
        assert response.status_code == 200
        assert response.json()["source"] == "heuristic"
