"""Generate concise user-facing responses from authoritative voice results."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Optional

from app.core.logging import get_logger
from app.schemas.normalization import NormalizationResponse
from app.schemas.voice_recommendation import VoiceRecommendationResponse
from app.services.llm_client import LLMClient, get_llm_client

logger = get_logger(__name__)


class ResponseGenerationService:
    """Presentation-only response generation."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    def generate(
        self,
        normalization: NormalizationResponse,
        recommendation: VoiceRecommendationResponse,
    ) -> tuple[str, str]:
        try:
            response_language = self._response_language(normalization)
            structured, scheme_names, statuses = self._structured_input(
                normalization, recommendation
            )
            fallback = self._restore_scheme_names(
                self._fallback(
                    self._fallback_data(structured, statuses), response_language
                ),
                scheme_names,
            )

            if response_language == "en":
                return fallback, response_language

            raw = self.llm_client.chat(
                self._system_prompt(),
                json.dumps(structured, ensure_ascii=False),
            )
            generated = self._parse_response(raw)
            validated = self._validate_and_restore(
                generated, response_language, scheme_names, statuses
            )
            if validated:
                return validated, response_language
        except Exception as exc:  # Response generation must never break recommendations.
            logger.warning("Response generation failed; using deterministic fallback: %s", exc)

        return self.fallback(normalization, recommendation)

    def fallback(
        self,
        normalization: NormalizationResponse,
        recommendation: VoiceRecommendationResponse,
    ) -> tuple[str, str]:
        """Return a deterministic response without calling the model."""
        response_language = self._response_language(normalization)
        try:
            structured, _, statuses = self._structured_input(normalization, recommendation)
            scheme_names = [
                scheme.scheme_name
                for scheme in recommendation.schemes
                if isinstance(scheme.scheme_name, str) and scheme.scheme_name.strip()
            ]
            return (
                self._restore_scheme_names(
                    self._fallback(
                        self._fallback_data(structured, statuses), response_language
                    ),
                    list(dict.fromkeys(scheme_names)),
                ),
                response_language,
            )
        except Exception as exc:  # Defensive boundary for malformed presentation data.
            logger.exception("Deterministic response fallback failed: %s", exc)
            return (
                "தற்போதுள்ள தகவல்களின் அடிப்படையில் பதிலை உருவாக்க முடியவில்லை."
                if response_language == "ta"
                else "I could not generate a response from the recommendation.",
                response_language,
            )

    @staticmethod
    def _fallback_data(
        structured: dict[str, Any], statuses: list[str]
    ) -> dict[str, Any]:
        data = dict(structured)
        data["schemes"] = [
            {**scheme, "status": status}
            for scheme, status in zip(structured.get("schemes", []), statuses)
        ]
        return data

    @staticmethod
    def _response_language(normalization: NormalizationResponse) -> str:
        return "ta" if normalization.language in {"ta", "ta-en"} else "en"

    @staticmethod
    def _structured_input(
        normalization: NormalizationResponse,
        recommendation: VoiceRecommendationResponse,
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        scheme_names = [
            scheme.scheme_name
            for scheme in recommendation.schemes
            if isinstance(scheme.scheme_name, str) and scheme.scheme_name.strip()
        ]
        protected_names = {
            name: f"__SCHEME_{index}__"
            for index, name in enumerate(dict.fromkeys(scheme_names))
        }
        statuses = [scheme.eligibility_status for scheme in recommendation.schemes]

        def protect(value: Any) -> Any:
            if isinstance(value, str):
                for name, placeholder in protected_names.items():
                    value = value.replace(name, placeholder)
                return value
            if isinstance(value, list):
                return [protect(item) for item in value]
            if isinstance(value, dict):
                return {key: protect(item) for key, item in value.items()}
            return value

        schemes = []
        for scheme in recommendation.schemes:
            scheme_data = {
                "scheme_name": protected_names.get(
                    scheme.scheme_name, scheme.scheme_name
                ),
                "status": f"__STATUS_{len(schemes)}__",
                "reason": scheme.recommendation_reason,
                "missing_information": scheme.missing_requirements,
                "required_documents": scheme.required_documents,
                "benefits": scheme.benefits,
                "eligibility_percentage": scheme.eligibility_percentage,
                "estimated_benefit": scheme.estimated_benefit,
            }
            schemes.append(protect(scheme_data))
        structured = {
            "response_language": ResponseGenerationService._response_language(normalization),
            "intent": normalization.intent,
            "entities": protect(normalization.entities),
            "schemes": schemes,
            "message": protect(recommendation.message),
        }
        return structured, list(protected_names.keys()), statuses

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are the response layer of a government scheme voice assistant. "
            "Generate the user-facing response directly in natural Tamil script. "
            "There is no English answer to translate. Use simple conversational "
            "Tamil for ordinary citizens and keep the response concise.\n\n"
            "Use only the structured source data in the user message. Scheme names "
            "are protected placeholders: copy every placeholder exactly once and "
            "do not translate, transliterate, shorten, or rewrite them. Preserve "
            "eligibility status placeholders exactly once too; they are authoritative "
            "and must not be changed. "
            "ages, incomes, land areas, amounts, "
            "dates, documents, and other factual values. Do not invent facts or "
            "eligibility requirements. Do not make eligibility decisions. Never "
            "change eligible, potentially_eligible, not_eligible, or "
            "insufficient_information. An eligible result may be described as "
            "eligible; potentially_eligible must express possibility and need for "
            "confirmation; not_eligible must clearly say the criteria are not met; "
            "insufficient_information must say what information is missing when "
            "provided. Do not output Tanglish.\n\n"
            "Keep the answer to at most three short sentences. Do not repeat any "
            "sentence or paragraph. Do not output analysis or reasoning. Return "
            "only one valid JSON object: {\"response_text\": \"...\"}."
        )

    @staticmethod
    def _parse_response(raw: str) -> str:
        if not raw or not raw.strip():
            return ""
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return ""
        response_text = payload.get("response_text") if isinstance(payload, dict) else None
        return response_text.strip() if isinstance(response_text, str) else ""

    @staticmethod
    def _validate_and_restore(
        text: str,
        language: str,
        scheme_names: list[str],
        statuses: list[str],
    ) -> str:
        if not text or len(text) > 700 or "{" in text or "}" in text:
            return ""
        if language == "ta" and not re.search(r"[\u0B80-\u0BFF]", text):
            return ""

        scheme_placeholders = [
            f"__SCHEME_{index}__" for index in range(len(scheme_names))
        ]
        status_placeholders = [
            f"__STATUS_{index}__" for index in range(len(statuses))
        ]
        for placeholder in scheme_placeholders + status_placeholders:
            if text.count(placeholder) != 1:
                return ""
        all_placeholders = scheme_placeholders + status_placeholders
        if re.search(r"__(?:SCHEME|STATUS)_\d+__", text):
            unknown = set(re.findall(r"__(?:SCHEME|STATUS)_\d+__", text)) - set(all_placeholders)
            if unknown:
                return ""

        sentences = [part.strip() for part in re.split(r"[.!?。！？]+", text) if part.strip()]
        normalized_sentences = [re.sub(r"\s+", " ", sentence).casefold() for sentence in sentences]
        if len(normalized_sentences) != len(set(normalized_sentences)):
            return ""
        for scheme_name, placeholder in zip(scheme_names, scheme_placeholders):
            text = text.replace(placeholder, scheme_name)
        for status, placeholder in zip(statuses, status_placeholders):
            text = text.replace(
                placeholder,
                ResponseGenerationService._status_phrase(status, language),
            )
        return text.strip()

    @staticmethod
    def _status_phrase(status: str, language: str) -> str:
        phrases = {
            "ta": {
                "eligible": "நீங்கள் தகுதியானவர்",
                "potentially_eligible": "நீங்கள் தகுதி பெற வாய்ப்பு உள்ளது",
                "not_eligible": "நீங்கள் தகுதி நிபந்தனைகளை பூர்த்தி செய்யவில்லை",
                "insufficient_information": "தகுதியை உறுதிப்படுத்த கூடுதல் தகவல்கள் தேவை",
            },
            "en": {
                "eligible": "you appear eligible",
                "potentially_eligible": "you may be eligible, subject to confirmation",
                "not_eligible": "you do not meet the eligibility conditions",
                "insufficient_information": "more information is needed to confirm eligibility",
            },
        }
        return phrases.get(language, phrases["en"]).get(
            status, "the eligibility status requires confirmation"
        )

    @staticmethod
    def _restore_scheme_names(text: str, scheme_names: list[str]) -> str:
        for index, scheme_name in enumerate(scheme_names):
            text = text.replace(f"__SCHEME_{index}__", scheme_name)
        return text

    @staticmethod
    def _fallback(data: dict[str, Any], language: str) -> str:
        schemes = data.get("schemes") or []
        if not schemes:
            if language == "ta":
                return "தற்போதுள்ள தகவல்களின் அடிப்படையில் பொருத்தமான அரசு திட்டம் கிடைக்கவில்லை."
            return data.get("message") or "No matching government schemes were found."

        names = [
            str(scheme.get("scheme_name") or "இந்தத் திட்டம்").strip()
            for scheme in schemes
        ]
        names = list(dict.fromkeys(name for name in names if name))
        name = names[0] if names else "இந்தத் திட்டம்"
        display_names = name if len(names) == 1 else " மற்றும் ".join(names[:3])
        scheme = schemes[0]
        status = str(scheme.get("status") or "").lower().strip()
        missing = scheme.get("missing_information") or []
        if language == "ta":
            if status == "eligible":
                return f"உங்கள் விவரங்களின் அடிப்படையில், {display_names} திட்டத்திற்கு நீங்கள் தகுதியானவர்."
            if status == "potentially_eligible":
                return f"உங்கள் விவரங்களின் அடிப்படையில், {display_names} திட்டத்திற்கு நீங்கள் தகுதி பெற வாய்ப்பு உள்ளது. சில கூடுதல் தகவல்கள் தேவைப்படலாம்."
            if status == "not_eligible":
                return f"உங்கள் தற்போதைய விவரங்களின் அடிப்படையில், {display_names} திட்டத்திற்கான தகுதி நிபந்தனைகளை நீங்கள் பூர்த்தி செய்யவில்லை."
            if status == "insufficient_information":
                return f"{display_names} திட்டத்திற்கான உங்கள் தகுதியை உறுதிப்படுத்த சில கூடுதல் தகவல்கள் தேவைப்படுகின்றன."
            return f"{display_names} திட்டத்தைப் பற்றிய தகவல் கிடைத்துள்ளது."

        if status == "eligible":
            return f"You appear eligible for {display_names}."
        if status == "potentially_eligible":
            return f"You may be eligible for {display_names}, subject to confirmation."
        if status == "not_eligible":
            return f"Based on the available information, you are not eligible for {display_names}."
        if status == "insufficient_information":
            return f"More information is needed to confirm your eligibility for {display_names}."
        return data.get("message") or f"Here is information about {display_names}."


@lru_cache(maxsize=1)
def get_response_generation_service() -> ResponseGenerationService:
    return ResponseGenerationService()