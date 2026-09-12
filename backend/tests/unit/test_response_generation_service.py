"""Focused tests for structured voice response generation."""
from __future__ import annotations

from datetime import datetime

import pytest

from app.schemas.normalization import NormalizationResponse
from app.schemas.voice_recommendation import VoiceRecommendationResponse
from app.services.response_generation_service import ResponseGenerationService


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.system_prompt = ""
        self.user_message = ""

    def chat(self, system_prompt: str, user_message: str) -> str:
        self.system_prompt = system_prompt
        self.user_message = user_message
        return self.response


def _normalization(language: str = "ta") -> NormalizationResponse:
    return NormalizationResponse(
        language=language,
        intent="scheme_eligibility",
        normalized_text="Am I eligible for PM Kisan?",
        entities={"scheme_name": "PM Kisan", "age": 42, "land_area": "2 acres"},
        confidence=0.9,
        source="llm",
    )


def _recommendation(
    status: str = "eligible",
    scheme_name: str = "PM Kisan Support",
) -> VoiceRecommendationResponse:
    return VoiceRecommendationResponse(
        schemes=[
            {
                "id": "match-1",
                "citizen_id": "citizen-1",
                "history_id": "history-1",
                "scheme_id": "scheme-1",
                "scheme_name": scheme_name,
                "description": "Income support for farmers.",
                "benefits": "Annual support of Rs. 6000",
                "eligibility_status": status,
                "eligibility_percentage": 90,
                "similarity_score": 0.9,
                "confidence_score": 85,
                "overall_score": 88,
                "ranking_position": 1,
                "recommendation_reason": "Farmer profile matched.",
                "matched_rules": [],
                "missing_requirements": [] if status != "insufficient_information" else ["land record"],
                "required_documents": ["Aadhaar"],
                "estimated_benefit": "6000",
                "application_ready": True,
                "profile_match_percentage": 90,
                "semantic_query": "farmer scheme",
                "created_at": datetime(2024, 1, 1),
            }
        ],
        intent="scheme_eligibility",
        language="ta",
    )


def test_tamil_is_generated_directly_from_structured_result():
    llm = FakeLLM(
        '{"response_text":"__SCHEME_0__ திட்டத்திற்கு __STATUS_0__. சில கூடுதல் தகவல்கள் தேவை."}'
    )
    service = ResponseGenerationService(llm)

    text, language = service.generate(_normalization("ta-en"), _recommendation("potentially_eligible"))

    assert language == "ta"
    assert "PM Kisan Support" in text
    assert "English answer" not in llm.user_message
    assert "response_language" in llm.user_message
    assert '"status": "__STATUS_0__"' in llm.user_message
    assert '"age": 42' in llm.user_message
    assert '"land_area": "2 acres"' in llm.user_message
    assert '"estimated_benefit": "6000"' in llm.user_message


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("eligible", "தகுதியானவர்"),
        ("potentially_eligible", "வாய்ப்பு உள்ளது"),
        ("not_eligible", "பூர்த்தி செய்யவில்லை"),
        ("insufficient_information", "கூடுதல் தகவல்கள் தேவைப்படுகின்றன"),
    ],
)
def test_malformed_tamil_generation_uses_status_safe_fallback(status, expected):
    service = ResponseGenerationService(FakeLLM("not json"))

    text, language = service.generate(_normalization(), _recommendation(status))

    assert language == "ta"
    assert "PM Kisan Support" in text
    assert expected in text


def test_empty_tamil_generation_uses_fallback():
    service = ResponseGenerationService(FakeLLM(""))

    text, _ = service.generate(_normalization(), _recommendation("eligible"))

    assert text == "உங்கள் விவரங்களின் அடிப்படையில், PM Kisan Support திட்டத்திற்கு நீங்கள் தகுதியானவர்."


def test_llm_exception_does_not_fail_recommendation_response():
    class BrokenLLM:
        def chat(self, system_prompt, user_message):
            raise RuntimeError("ollama unavailable")

    service = ResponseGenerationService(BrokenLLM())

    text, language = service.generate(_normalization(), _recommendation("eligible"))

    assert language == "ta"
    assert "PM Kisan Support" in text
    assert "தகுதியானவர்" in text


def test_english_uses_existing_language_without_tamil_model_call():
    llm = FakeLLM('{"response_text":"should not be used"}')
    service = ResponseGenerationService(llm)

    text, language = service.generate(_normalization("en"), _recommendation("eligible"))

    assert language == "en"
    assert text == "You appear eligible for PM Kisan Support."
    assert llm.user_message == ""


def test_scheme_name_is_protected_and_restored_exactly():
    name = "PM RKVY and PKVY Guidelines"
    llm = FakeLLM(
        '{"response_text":"__SCHEME_0__ போன்ற திட்டங்கள் உங்களுக்கு பொருந்தக்கூடும்."}'
    )

    text, _ = ResponseGenerationService(llm).generate(
        _normalization(), _recommendation("potentially_eligible", name)
    )

    assert text.count(name) == 1
    assert "__SCHEME_0__" not in text
    assert "__SCHEME_0__" in llm.user_message
    assert "PM RKVY and PKVY Guidelines" not in llm.user_message


@pytest.mark.parametrize(
    "model_text",
    [
        '{"response_text":"__SCHEME_0__ __STATUS_0__. __SCHEME_0__ __STATUS_0__."}',
        '{"response_text":"இந்தத் திட்டம் பொருந்தும்."}',
        '{"response_text":"' + ("__SCHEME_0__ __STATUS_0__ தகவல். " * 80) + '"}',
        '{"response_text":"{\\"analysis\\":\\"reasoning\\"}"}',
    ],
)
def test_repeated_garbled_or_unprotected_output_uses_fallback(model_text):
    text, _ = ResponseGenerationService(FakeLLM(model_text)).generate(
        _normalization(), _recommendation("eligible")
    )

    assert text == "உங்கள் விவரங்களின் அடிப்படையில், PM Kisan Support திட்டத்திற்கு நீங்கள் தகுதியானவர்."