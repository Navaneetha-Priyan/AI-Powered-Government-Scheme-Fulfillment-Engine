"""Unit tests for TextNormalizationService (Phase 4 - Multilingual Normalization).

These tests NEVER call a real external LLM API. The LLMClient is always mocked.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.exceptions.exceptions import LLMUnavailableError
from app.services.text_normalization_service import TextNormalizationService


def _make_service(llm_response: str | None = None, raise_error: Exception | None = None):
    """Build a TextNormalizationService with a mocked LLM client."""
    llm = MagicMock()
    if raise_error is not None:
        llm.chat.side_effect = raise_error
    else:
        llm.chat.return_value = llm_response if llm_response is not None else "{}"
    return TextNormalizationService(llm_client=llm, enable_heuristic_fallback=True)


def _llm_json(**overrides):
    """Build a valid LLM JSON response dict, then dump to a string."""
    base = {
        "language": "ta-en",
        "intent": "scheme_search",
        "normalized_text": "Looking for a farmer scheme with low income",
        "entities": {"occupation": "farmer", "income_status": "low"},
        "confidence": 0.9,
    }
    base.update(overrides)
    return json.dumps(base, ensure_ascii=False)


# ── LLM success path ──────────────────────────────────────────────────────

class TestLLMSuccess:
    def test_standard_tamil(self):
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="Need a government scheme for farming",
                entities={"occupation": "farmer"},
            )
        )
        result = service.normalize("எனக்கு விவசாயத்திற்கு அரசு திட்டம் வேண்டும்")
        assert result.source == "llm"
        assert result.language == "ta"
        assert result.intent == "scheme_search"
        assert result.entities.get("occupation") == "farmer"

    def test_english(self):
        service = _make_service(
            _llm_json(
                language="en",
                intent="scheme_search",
                entities={"occupation": "farmer"},
            )
        )
        result = service.normalize("I need a government scheme for farming")
        assert result.source == "llm"
        assert result.language == "en"
        assert result.intent == "scheme_search"

    def test_tamil_english_mixed(self):
        service = _make_service(
            _llm_json(
                language="ta-en",
                intent="scheme_eligibility",
                entities={"scheme_name": "PM Kisan"},
            )
        )
        result = service.normalize("PM Kisan schemeக்கு நான் eligibleஆ?")
        assert result.source == "llm"
        assert result.language == "ta-en"
        assert result.intent == "scheme_eligibility"
        assert result.entities.get("scheme_name") == "PM Kisan"

    def test_scheme_eligibility_question(self):
        service = _make_service(
            _llm_json(
                language="ta-en",
                intent="scheme_eligibility",
                entities={"scheme_name": "PM Kisan"},
            )
        )
        result = service.normalize("PM Kisan schemeக்கு நான் eligibleஆ?")
        assert result.intent == "scheme_eligibility"

    def test_document_requirement_question(self):
        service = _make_service(
            _llm_json(
                language="ta",
                intent="document_requirement",
                entities={"document_type": "income_certificate"},
            )
        )
        result = service.normalize("இந்த திட்டத்திற்கு என்ன ஆவணம் வேண்டும்?")
        assert result.intent == "document_requirement"
        assert result.entities.get("document_type") == "income_certificate"

    def test_llm_json_wrapped_in_markdown_fence(self):
        service = _make_service(
            "```json\n" + _llm_json(intent="scheme_search") + "\n```"
        )
        result = service.normalize("some query")
        assert result.source == "llm"
        assert result.intent == "scheme_search"

    def test_llm_json_with_surrounding_prose(self):
        service = _make_service(
            "Here is the result: " + _llm_json(intent="scheme_search")
        )
        result = service.normalize("some query")
        assert result.source == "llm"
        assert result.intent == "scheme_search"


# ── LLM failure / fallback path ───────────────────────────────────────────

class TestLLMFailureAndFallback:
    def test_llm_unavailable_falls_back_to_heuristic(self):
        service = _make_service(raise_error=LLMUnavailableError("down"))
        result = service.normalize("எனக்கு துட்டு ரொம்ப கம்மி farmer scheme இருக்கா?")
        assert result.source == "heuristic"
        assert result.entities.get("income_status") == "low"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"

    def test_llm_timeout_falls_back_to_heuristic(self):
        service = _make_service(raise_error=LLMUnavailableError("timeout"))
        result = service.normalize("money romba kammi, teacher scheme irukka?")
        assert result.source == "heuristic"
        assert result.entities.get("income_status") == "low"

    def test_invalid_json_falls_back_to_heuristic(self):
        service = _make_service("this is not json at all {")
        result = service.normalize("எனக்கு விவசாய திட்டம் வேண்டும்")
        assert result.source == "heuristic"
        assert result.entities.get("occupation") == "farmer"

    def test_malformed_structured_response_falls_back(self):
        # Valid JSON but missing the required fields -> parse returns unknown.
        service = _make_service('{"foo": "bar"}')
        result = service.normalize("enakkau farmer scheme venum")
        assert result.source == "heuristic"

    def test_malformed_scalar_types_falls_back(self):
        service = _make_service(
            '{"language": 123, "intent": "scheme_search", "confidence": "NaN"}'
        )
        result = service.normalize("some text with scheme")
        assert result.source == "heuristic"

    def test_empty_input_returns_unknown(self):
        service = _make_service()
        result = service.normalize("   ")
        assert result.language == "unknown"
        assert result.intent == "unknown"
        assert result.confidence == 0.0


# ── Heuristic behavior (no LLM) ───────────────────────────────────────────

class TestHeuristicFallback:
    def make_heuristic(self):
        return _make_service(raise_error=LLMUnavailableError("offline"))

    def test_tanglish_low_income_farmer(self):
        service = self.make_heuristic()
        result = service.normalize("enakku kaasu romba kammi, farmer scheme irukka?")
        assert result.source == "heuristic"
        assert result.entities.get("income_status") == "low"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"

    def test_colloquial_tamil_low_income(self):
        service = self.make_heuristic()
        result = service.normalize("எனக்கு துட்டு கம்மி, ஏதாவது உதவி கிடைக்குமா?")
        assert result.entities.get("income_status") == "low"
        assert result.intent == "scheme_search"

    def test_income_low_english(self):
        service = self.make_heuristic()
        result = service.normalize("my income low, any scheme?")
        assert result.entities.get("income_status") == "low"

    def test_scheme_name_detection(self):
        service = self.make_heuristic()
        result = service.normalize("PM Kisan scheme eligible a?")
        assert result.entities.get("scheme_name") == "PM Kisan"

    def test_eligibility_intent(self):
        service = self.make_heuristic()
        result = service.normalize("PM Kisan scheme eligible a?")
        assert result.intent == "scheme_eligibility"

    def test_language_detection_tamil(self):
        service = self.make_heuristic()
        result = service.normalize("எனக்கு விவசாயத்திற்கு அரசு திட்டம் வேண்டும்")
        assert result.language == "ta"

    def test_language_detection_english(self):
        service = self.make_heuristic()
        result = service.normalize("I need a government scheme for farming")
        assert result.language == "en"

    def test_language_detection_mixed(self):
        service = self.make_heuristic()
        result = service.normalize("enakku farmer scheme irukka?")
        assert result.language == "ta-en"

    def test_unknown_intent(self):
        service = self.make_heuristic()
        result = service.normalize("hello world")
        assert result.intent == "unknown"

    def test_document_requirement_heuristic(self):
        service = self.make_heuristic()
        result = service.normalize("எந்த certificate வேண்டும்?")
        assert result.intent == "document_requirement"


# ── Confidence / no-inference safety ──────────────────────────────────────

class TestSafety:
    def test_does_not_infer_absent_entities(self):
        service = _make_service(
            _llm_json(intent="scheme_search", entities={"occupation": "farmer"})
        )
        result = service.normalize("I need a farmer scheme")
        # No income_status inferred because the LLM denied it.
        assert "income_status" not in result.entities

    def test_llm_confidence_clamped(self):
        service = _make_service(_llm_json(confidence=5.0))
        result = service.normalize("some query")
        assert result.confidence <= 1.0
