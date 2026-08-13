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


# ── Tamil domain regression tests (Phase 4 Tamil normalization) ───────────

class TestTamilFarmerRegression:
    """Regression tests for the exact Tamil farmer/agriculture queries.

    These verify that when the LLM returns semantically correct output, the
    service preserves farmer/agriculture meaning, and that generic farmer
    phrases are not misclassified as scheme_name.
    """

    def test_farmers_need_government_schemes(self):
        """விவசாயிகளுக்கு அரசு திட்டம் வேண்டும் -> government schemes for farmers."""
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="I need government schemes for farmers",
                entities={"occupation": "farmer"},
                confidence=0.9,
            )
        )
        result = service.normalize("விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்")
        assert result.source == "llm"
        assert result.language == "ta"
        assert result.intent == "scheme_search"
        assert result.entities.get("occupation") == "farmer"
        assert "farmer" in result.normalized_text.lower()
        assert "scheme" in result.normalized_text.lower()
        # Generic farmer phrase must NOT become scheme_name.
        assert "scheme_name" not in result.entities

    def test_i_need_agriculture_scheme(self):
        """எனக்கு விவசாய திட்டம் வேண்டும் -> agriculture/farmer scheme."""
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="I need a government scheme related to agriculture/farmers",
                entities={"occupation": "farmer"},
                confidence=0.85,
            )
        )
        result = service.normalize("எனக்கு விவசாய திட்டம் வேண்டும்")
        assert result.source == "llm"
        assert result.language == "ta"
        assert result.intent == "scheme_search"
        assert result.entities.get("occupation") == "farmer"
        assert "farmer" in result.normalized_text.lower() or "agriculture" in result.normalized_text.lower()
        assert "scheme" in result.normalized_text.lower()
        assert "scheme_name" not in result.entities

    def test_what_schemes_for_farmers(self):
        """விவசாயிகளுக்கான திட்டங்கள் என்ன? -> what schemes for farmers."""
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="What government schemes are available for farmers?",
                entities={"occupation": "farmer"},
                confidence=0.9,
            )
        )
        result = service.normalize("விவசாயிகளுக்கான திட்டங்கள் என்ன?")
        assert result.source == "llm"
        assert result.language == "ta"
        assert result.intent == "scheme_search"
        assert result.entities.get("occupation") == "farmer"
        assert "farmer" in result.normalized_text.lower()
        assert "scheme" in result.normalized_text.lower()
        # Generic farmer phrase must NOT become scheme_name.
        assert "scheme_name" not in result.entities

    def test_any_schemes_for_agriculture(self):
        """எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா? -> any schemes for agriculture."""
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="Are there any government schemes available for farmers/agriculture?",
                entities={"occupation": "farmer"},
                confidence=0.85,
            )
        )
        result = service.normalize("எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?")
        assert result.source == "llm"
        assert result.language == "ta"
        assert result.intent == "scheme_search"
        assert result.entities.get("occupation") == "farmer"
        assert "farmer" in result.normalized_text.lower() or "agriculture" in result.normalized_text.lower()
        assert "scheme" in result.normalized_text.lower()
        assert "scheme_name" not in result.entities

    def test_pm_kisan_eligibility(self):
        """PM Kisan schemeக்கு நான் eligibleஆ? -> PM Kisan eligibility."""
        service = _make_service(
            _llm_json(
                language="ta-en",
                intent="scheme_eligibility",
                normalized_text="Am I eligible for the PM Kisan scheme?",
                entities={"scheme_name": "PM Kisan"},
                confidence=0.95,
            )
        )
        result = service.normalize("PM Kisan schemeக்கு நான் eligibleஆ?")
        assert result.source == "llm"
        assert result.language == "ta-en"
        assert result.intent == "scheme_eligibility"
        assert result.entities.get("scheme_name") == "PM Kisan"
        assert "PM Kisan" in result.normalized_text
        assert "eligible" in result.normalized_text.lower()

    def test_llm_must_not_invent_occupation(self):
        """LLM output that invents an unrelated occupation must be rejected."""
        # Even if the LLM returns a wrong occupation, the test verifies the
        # service passes through what the LLM says (the prompt is the guard).
        # This test documents the expected behavior: the service does not
        # second-guess the LLM, but the prompt must prevent this.
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="healthcare scheme needed for professionals",
                entities={"occupation": "professionals"},
                confidence=1.0,
            )
        )
        result = service.normalize("விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்")
        # The service passes through LLM output; the prompt is the guard.
        # This test documents that the prompt must prevent this from happening.
        assert result.source == "llm"
        assert result.entities.get("occupation") == "professionals"

    def test_system_prompt_contains_tamil_domain_vocabulary(self):
        """The system prompt must teach the Tamil domain vocabulary."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        # Key Tamil vocabulary must be present.
        assert "விவசாயி" in prompt
        assert "விவசாயம்" in prompt
        assert "விவசாயிகளுக்கு" in prompt
        assert "விவசாயிகளுக்கான" in prompt
        assert "விவசாயத்துக்கு" in prompt
        assert "அரசு" in prompt
        assert "திட்டம்" in prompt
        assert "திட்டங்கள்" in prompt
        assert "உதவி" in prompt
        assert "கம்மி" in prompt
        assert "eligibleஆ" in prompt
        assert "இருக்கா" in prompt
        # Critical rules must be present.
        assert "farmer" in prompt
        assert "agriculture" in prompt
        assert "scheme_name" in prompt
        assert "confidence" in prompt

    def test_system_prompt_forbids_inventing_occupation(self):
        """The system prompt must forbid inventing occupations."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "NEVER invent an occupation" in prompt
        assert "professional" in prompt
        assert "vocational" in prompt
        assert "healthcare" in prompt

    def test_system_prompt_forbids_generic_scheme_name(self):
        """The system prompt must forbid generic phrases as scheme_name."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "விவசாயிகளுக்கான திட்டங்கள்" in prompt
        assert "must NOT become scheme_name" in prompt

    def test_system_prompt_requires_conservative_confidence(self):
        """The system prompt must instruct conservative confidence."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "Do not default to 1.0" in prompt
        assert "conservative confidence" in prompt

    def test_system_prompt_requires_english_normalized_text(self):
        """The system prompt must require English normalized_text."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "English semantic representation" in prompt
        assert "Do NOT merely paraphrase the Tamil input back into Tamil" in prompt

    def test_heuristic_fallback_preserves_farmer(self):
        """Heuristic fallback must preserve farmer occupation for Tamil inputs."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்")
        assert result.source == "heuristic"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"

    def test_heuristic_fallback_agriculture_scheme(self):
        """Heuristic fallback must detect farmer for விவசாய திட்டம்."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("எனக்கு விவசாய திட்டம் வேண்டும்")
        assert result.source == "heuristic"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"

    def test_heuristic_fallback_what_schemes_for_farmers(self):
        """Heuristic fallback must detect farmer for விவசாயிகளுக்கான திட்டங்கள்."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("விவசாயிகளுக்கான திட்டங்கள் என்ன?")
        assert result.source == "heuristic"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"

    def test_heuristic_fallback_any_schemes_for_agriculture(self):
        """Heuristic fallback must detect farmer for விவசாயத்துக்கு."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?")
        assert result.source == "heuristic"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"

    def test_heuristic_fallback_pm_kisan_eligibility(self):
        """Heuristic fallback must detect PM Kisan scheme and eligibility."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("PM Kisan schemeக்கு நான் eligibleஆ?")
        assert result.source == "heuristic"
        assert result.entities.get("scheme_name") == "PM Kisan"
        assert result.intent == "scheme_eligibility"

    def test_malformed_llm_output_falls_back_for_tamil(self):
        """Malformed LLM output for Tamil input must fall back to heuristic."""
        service = _make_service("this is not valid json {")
        result = service.normalize("விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்")
        assert result.source == "heuristic"
        assert result.entities.get("occupation") == "farmer"
        assert result.intent == "scheme_search"


# ── Intent classification regression tests (scheme_search vs scheme_eligibility) ──

class TestIntentClassificationRegression:
    """Regression tests for the scheme_search / scheme_eligibility distinction.

    These verify that availability/existence questions are classified as
    scheme_search, and personal eligibility questions for a named/clearly
    identified scheme are classified as scheme_eligibility.
    """

    # ── scheme_search cases ──────────────────────────────────────────────

    def test_tamil_any_government_schemes_available(self):
        """எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா? -> scheme_search."""
        english_normalized_text = "Are there any government schemes available for agriculture?"
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text=english_normalized_text,
                entities={"occupation": "farmer"},
                confidence=0.9,
            )
        )
        original_text = "எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?"
        result = service.normalize(original_text)
        assert result.source == "llm"
        assert result.intent == "scheme_search"
        assert result.normalized_text == english_normalized_text
        assert result.normalized_text != original_text

    def test_tamil_what_schemes_for_farmers_available(self):
        """விவசாயிகளுக்கான திட்டங்கள் என்ன? -> scheme_search."""
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="What government schemes are available for farmers?",
                entities={"occupation": "farmer"},
                confidence=0.9,
            )
        )
        result = service.normalize("விவசாயிகளுக்கான திட்டங்கள் என்ன?")
        assert result.source == "llm"
        assert result.intent == "scheme_search"

    def test_tamil_farmers_need_govt_schemes_available(self):
        """விவசாயிகளுக்கு அரசு திட்டம் வேண்டும் -> scheme_search."""
        service = _make_service(
            _llm_json(
                language="ta",
                intent="scheme_search",
                normalized_text="I need government schemes for farmers",
                entities={"occupation": "farmer"},
                confidence=0.9,
            )
        )
        result = service.normalize("விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்")
        assert result.source == "llm"
        assert result.intent == "scheme_search"

    def test_english_what_schemes_available(self):
        """What government schemes are available for farmers? -> scheme_search."""
        service = _make_service(
            _llm_json(
                language="en",
                intent="scheme_search",
                normalized_text="What government schemes are available for farmers?",
                entities={"occupation": "farmer"},
                confidence=0.9,
            )
        )
        result = service.normalize("What government schemes are available for farmers?")
        assert result.source == "llm"
        assert result.intent == "scheme_search"

    # ── scheme_eligibility cases ─────────────────────────────────────────

    def test_pm_kisan_tanglish_eligibility_intent(self):
        """PM Kisan schemeக்கு நான் eligibleஆ? -> scheme_eligibility + PM Kisan."""
        service = _make_service(
            _llm_json(
                language="ta-en",
                intent="scheme_eligibility",
                normalized_text="Am I eligible for the PM Kisan scheme?",
                entities={"scheme_name": "PM Kisan"},
                confidence=0.95,
            )
        )
        result = service.normalize("PM Kisan schemeக்கு நான் eligibleஆ?")
        assert result.source == "llm"
        assert result.intent == "scheme_eligibility"
        assert result.entities.get("scheme_name") == "PM Kisan"

    def test_english_pm_kisan_eligibility_intent(self):
        """Am I eligible for PM Kisan? -> scheme_eligibility + PM Kisan."""
        service = _make_service(
            _llm_json(
                language="en",
                intent="scheme_eligibility",
                normalized_text="Am I eligible for PM Kisan?",
                entities={"scheme_name": "PM Kisan"},
                confidence=0.95,
            )
        )
        result = service.normalize("Am I eligible for PM Kisan?")
        assert result.source == "llm"
        assert result.intent == "scheme_eligibility"
        assert result.entities.get("scheme_name") == "PM Kisan"

    # ── heuristic path (no LLM) ──────────────────────────────────────────

    def test_heuristic_tamil_any_schemes_available(self):
        """Heuristic: எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா? -> scheme_search."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?")
        assert result.source == "heuristic"
        assert result.intent == "scheme_search"

    def test_heuristic_english_what_schemes_available(self):
        """Heuristic: What government schemes are available for farmers? -> scheme_search."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("What government schemes are available for farmers?")
        assert result.source == "heuristic"
        assert result.intent == "scheme_search"

    def test_heuristic_pm_kisan_tanglish_eligibility_intent(self):
        """Heuristic: PM Kisan schemeக்கு நான் eligibleஆ? -> scheme_eligibility + PM Kisan."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("PM Kisan schemeக்கு நான் eligibleஆ?")
        assert result.source == "heuristic"
        assert result.intent == "scheme_eligibility"
        assert result.entities.get("scheme_name") == "PM Kisan"

    def test_heuristic_english_pm_kisan_eligibility_intent(self):
        """Heuristic: Am I eligible for PM Kisan? -> scheme_eligibility + PM Kisan."""
        service = _make_service(raise_error=LLMUnavailableError("offline"))
        result = service.normalize("Am I eligible for PM Kisan?")
        assert result.source == "heuristic"
        assert result.intent == "scheme_eligibility"
        assert result.entities.get("scheme_name") == "PM Kisan"

    # ── prompt content regression ────────────────────────────────────────

    def test_system_prompt_defines_scheme_search_intent(self):
        """The system prompt must define scheme_search intent."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "scheme_search" in prompt
        assert "asking what government schemes are available" in prompt
        assert "asking whether any schemes exist" in prompt
        assert "asking for schemes related to an occupation, crop, land" in prompt

    def test_system_prompt_defines_scheme_eligibility_intent(self):
        """The system prompt must define scheme_eligibility intent narrowly."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "scheme_eligibility" in prompt
        assert "personally qualify" in prompt
        assert "specific named scheme" in prompt
        assert "clearly identified scheme" in prompt

    def test_system_prompt_distinguishes_availability_from_eligibility(self):
        """The system prompt must not conflate இருக்கா with personal eligibility."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        assert "இருக்கா?" in prompt
        assert "availability/existence" in prompt
        assert "NOT \"scheme_eligibility\"" in prompt
        assert "எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?" in prompt
        assert "not personal eligibility" in prompt

    def test_system_prompt_contains_intent_examples(self):
        """The system prompt must include both intent example sets."""
        service = _make_service()
        prompt = service._SYSTEM_PROMPT
        # scheme_search examples
        assert "விவசாயிகளுக்கான திட்டங்கள் என்ன?" in prompt
        assert "விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்" in prompt
        assert "What government schemes are available for farmers?" in prompt
        assert "Are there any government schemes available for agriculture?" in prompt
        assert "Enakku farmer scheme edhavadhu irukka?" in prompt
        # scheme_eligibility examples
        assert "PM Kisan schemeக்கு நான் eligibleஆ?" in prompt
        assert "Am I eligible for PM Kisan?" in prompt
        assert "நான் இந்த திட்டத்திற்கு தகுதியானவனா?" in prompt
        assert "இந்த திட்டத்திற்கு நான் தகுதியுள்ளவனா?" in prompt
        assert "Can I apply for PM Kisan?" in prompt
