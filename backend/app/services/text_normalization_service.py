"""TextNormalizationService - Phase 4 Multilingual, Dialect & Intent Normalization.

Pipeline::

    Raw transcript
        -> language / code-switching detection
        -> optional LLM (Ollama) based semantic normalization + intent extraction
        -> deterministic heuristic fallback (if LLM unavailable/invalid)
        -> structured NormalizationResult

The service is intentionally independent of:
- the database
- the eligibility engine
- RAG / vector store
- authentication
- the Flutter client

It ONLY converts a raw transcript into a structured query for Phase 5.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import LLMUnavailableError, NormalizationError
from app.schemas.normalization import NormalizationResult
from app.services.llm_client import LLMClient, get_llm_client

logger = get_logger(__name__)

# Allowed intent values (shared with the schema Literal).
_ALLOWED_INTENTS = {
    "scheme_search",
    "scheme_eligibility",
    "application_status",
    "document_requirement",
    "profile_query",
    "unknown",
}

# Allowed language tags (shared with the schema Literal).
_ALLOWED_LANGUAGES = {"ta", "en", "ta-en", "unknown"}


class TextNormalizationService:
    """Normalize raw transcripts into a structured representation.

    Flow:
      1. Try the LLM (Ollama) for rich semantic interpretation.
      2. If the LLM is unavailable/times out/invalid, fall back to a small
         deterministic heuristic analyzer.
      3. Never crash just because the LLM is offline.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_heuristic_fallback: Optional[bool] = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.enable_heuristic_fallback = (
            settings.NORMALIZE_ENABLE_HEURISTIC_FALLBACK
            if enable_heuristic_fallback is None
            else enable_heuristic_fallback
        )

    # ── Public API ────────────────────────────────────────────────────────

    def normalize(self, text: str) -> NormalizationResult:
        """Normalize a raw transcript into a structured result.

        Falls back to the heuristic analyzer whenever the LLM path cannot
        produce a valid, structured result.
        """
        cleaned = (text or "").strip()
        if not cleaned:
            return NormalizationResult(
                language="unknown",
                intent="unknown",
                normalized_text="",
                entities={},
                confidence=0.0,
                source="heuristic",
            )

        # 1) Try the LLM.
        try:
            result = self._normalize_with_llm(cleaned)
            if result is not None:
                return result
        except LLMUnavailableError:
            logger.warning("LLM unavailable; using heuristic fallback")
        except NormalizationError:
            logger.warning("LLM returned invalid result; using heuristic fallback")

        # 2) Deterministic heuristic fallback.
        return self._normalize_with_heuristics(cleaned)

    # ── LLM path ──────────────────────────────────────────────────────────

    def _normalize_with_llm(self, text: str) -> Optional[NormalizationResult]:
        """Ask Ollama to interpret the query and parse a structured result."""
        prompt = self._build_user_prompt(text)
        raw = self.llm_client.chat(self._SYSTEM_PROMPT, prompt)
        return self._parse_llm_json(raw, text)

    @property
    def _SYSTEM_PROMPT(self) -> str:  # noqa: N802 - matches enclosing style
        """System prompt instructing the model to interpret, not answer."""
        return (
            "You are a multilingual language normalizer for a Tamil government "
            "scheme assistant. You understand Tamil, English, Tanglish, and "
            "Tamil-English code-switching, as well as colloquial Tamil and "
            "regional slang.\n\n"
            "Your ONLY job is to understand the USER'S MEANING and produce a "
            "structured interpretation. DO NOT answer the user's question, DO "
            "NOT give scheme recommendations, and DO NOT infer citizen "
            "attributes that are not explicitly present in the speech.\n\n"
            "Rules:\n"
            "1. Preserve the user's actual meaning.\n"
            "2. Recognize colloquial Tamil and common Tamil slang; normalize "
            "slang into standard semantic concepts (e.g. 'thuttu'/'kaasu' -> "
            "low income).\n"
            "3. Understand English words embedded in Tamil sentences and "
            "Tanglish/code-switching.\n"
            "4. Never invent facts. If unsure, set confidence low and use "
            "'unknown' for unidentified fields.\n"
            "5. Never change or assume citizen profile information.\n\n"
            "Return ONLY a single valid JSON object with EXACTLY these keys:\n"
            "{\n"
            "  \"language\": \"ta\" or \"en\" or \"ta-en\" or \"unknown\",\n"
            "  \"intent\": \"scheme_search\" or \"scheme_eligibility\" or "
            "\"application_status\" or \"document_requirement\" or "
            "\"profile_query\" or \"unknown\",\n"
            "  \"normalized_text\": \"a short meaning-preserving normalized "
            "representation in English or Tamil (no invented facts)\",\n"
            "  \"entities\": {\n"
            "    \"scheme_name\": \"...\" or null,\n"
            "    \"occupation\": \"...\" or null,\n"
            "    \"income_status\": \"low\" or \"medium\" or \"high\" or "
            "null,\n"
            "    \"land_ownership\": \"...\" or null,\n"
            "    \"land_area\": \"...\" or null,\n"
            "    \"crop\": \"...\" or null,\n"
            "    \"location\": \"...\" or null,\n"
            "    \"caste\": \"...\" or null,\n"
            "    \"age\": \"...\" or null,\n"
            "    \"gender\": \"...\" or null,\n"
            "    \"document_type\": \"...\" or null\n"
            "  },\n"
            "  \"confidence\": 0.0 to 1.0\n"
            "}\n\n"
            "Only include entity keys that are actually present in the "
            "speech. Omit or set to null everything else. Do not add "
            "explanatory text outside the JSON."
        )

    def _build_user_prompt(self, text: str) -> str:
        """Build the user message containing the raw transcript."""
        return f'Normalize this raw transcript: "{text}"'

    # ── Parsing / validation ──────────────────────────────────────────────

    def _parse_llm_json(self, raw: str, original_text: str) -> Optional[NormalizationResult]:
        """Parse and validate the LLM's JSON response into a result.

        Returns None if the response is not valid JSON or does not match the
        expected schema (so the caller can fall back to heuristics).
        """
        data = self._extract_json(raw)
        if data is None:
            logger.warning("LLM response was not valid JSON; cannot parse")
            return None

        # Require the essential keys to be present and valid; otherwise the
        # response is considered malformed and we fall back to heuristics.
        if "intent" not in data or "language" not in data:
            logger.warning("LLM response missing required fields")
            return None

        try:
            language = str(data.get("language", "unknown")).strip().lower()
            intent = str(data.get("intent", "unknown")).strip().lower()
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            logger.warning("LLM response had invalid scalar fields")
            return None

        if not math.isfinite(confidence):
            logger.warning("LLM response had non-finite confidence")
            return None

        language = language if language in _ALLOWED_LANGUAGES else "unknown"
        intent = intent if intent in _ALLOWED_INTENTS else "unknown"
        confidence = max(0.0, min(1.0, confidence))

        entities: Dict[str, Any] = {}
        raw_entities = data.get("entities")
        if isinstance(raw_entities, dict):
            for key, value in raw_entities.items():
                if value is None:
                    continue
                if isinstance(value, (str, int, float, bool)):
                    entities[key] = value

        normalized_text = str(data.get("normalized_text", "")).strip()
        if not normalized_text:
            normalized_text = original_text.strip()

        return NormalizationResult(
            language=language,
            intent=intent,
            normalized_text=normalized_text,
            entities=entities,
            confidence=confidence,
            source="llm",
        )

    @staticmethod
    def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
        """Extract a JSON object from model output.

        Handles cases where the model wraps the JSON in markdown fences or adds
        surrounding prose.
        """
        if not raw:
            return None

        text = raw.strip()

        # Strip markdown code fences if present.
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # Try a direct parse first.
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: locate the first '{' and last '}'.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return None
        return None

    # ── Heuristic fallback ────────────────────────────────────────────────

    def _normalize_with_heuristics(self, text: str) -> NormalizationResult:
        """Deterministic, small vocabulary fallback analyzer.

        Kept intentionally small, explainable, and easy to extend. It does NOT
        attempt a full Tamil dictionary.
        """
        lowered = text.lower()
        normalized = self._heuristic_normalized_text(text)

        entities: Dict[str, Any] = {}

        # Income status (Tamil slang / English / Tanglish).
        if self._contains_any(lowered, _INCOME_LOW_PATTERNS):
            entities["income_status"] = "low"

        # Occupation / domain.
        for occupation, patterns in _OCCUPATION_PATTERNS.items():
            if self._contains_any(lowered, patterns):
                entities["occupation"] = occupation
                break  # keep it simple: first recognized occupation wins

        # Crop.
        for crop, patterns in _CROP_PATTERNS.items():
            if self._contains_any(lowered, patterns):
                entities["crop"] = crop
                break

        # Land ownership.
        if self._contains_any(lowered, _LAND_OWNER_PATTERNS["owner"]):
            entities["land_ownership"] = "owner"
        elif self._contains_any(lowered, _LAND_OWNER_PATTERNS["tenant"]):
            entities["land_ownership"] = "tenant"
        elif self._contains_any(lowered, _LAND_OWNER_PATTERNS["landless"]):
            entities["land_ownership"] = "landless"

        # Document type.
        for doc_type, patterns in _DOCUMENT_PATTERNS.items():
            if self._contains_any(lowered, patterns):
                entities["document_type"] = doc_type
                break

        # Scheme name (explicit well-known names).
        for scheme_name, patterns in _SCHEME_NAME_PATTERNS.items():
            if self._contains_any(lowered, patterns, normalize=True):
                entities["scheme_name"] = scheme_name
                break

        # Intent.
        intent = self._detect_heuristic_intent(lowered)

        # Language.
        language = self._detect_heuristic_language(text)

        # Confidence: heuristic results are conservative.
        confidence = 0.55 if intent != "unknown" or entities else 0.3

        return NormalizationResult(
            language=language,
            intent=intent,
            normalized_text=normalized,
            entities=entities,
            confidence=confidence,
            source="heuristic",
        )

    def _detect_heuristic_intent(self, lowered: str) -> str:
        """Detect the most likely intent via keyword rules."""
        if self._contains_any(lowered, _INTENT_PATTERNS["eligibility"]):
            return "scheme_eligibility"
        if self._contains_any(lowered, _INTENT_PATTERNS["document"]):
            return "document_requirement"
        if self._contains_any(lowered, _INTENT_PATTERNS["application_status"]):
            return "application_status"
        if self._contains_any(lowered, _INTENT_PATTERNS["profile"]):
            return "profile_query"
        if self._contains_any(lowered, _INTENT_PATTERNS["search"]):
            return "scheme_search"
        return "unknown"

    def _detect_heuristic_language(self, text: str) -> str:
        """Approximate language detection based on Unicode ranges.

        Tamil words written in Latin script (Tanglish) are approximated by
        scanning for a small set of common Tamil-transliterated tokens.
        """
        tamil_chars = sum(1 for ch in text if 0x0B80 <= ord(ch) <= 0x0BFF)
        latin_chars = sum(1 for ch in text if ch.isascii() and ch.isalpha())

        if tamil_chars > 0 and latin_chars > 0:
            return "ta-en"
        if tamil_chars > 0:
            return "ta"
        if latin_chars > 0:
            # Could be English or Tanglish (Tamil written in Latin script).
            if self._contains_any(text.lower(), _TANGLISH_HINTS):
                return "ta-en"
            return "en"
        return "unknown"

    def _heuristic_normalized_text(self, text: str) -> str:
        """Return a light, meaning-preserving normalized string.

        This is intentionally conservative: it collapses whitespace and returns
        the trimmed text. Named-entity normalization is left to the LLM path.
        """
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _contains_any(lowered_text: str, patterns: list[str], normalize: bool = False) -> bool:
        """Return True if any pattern appears in the text."""
        if normalize:
            searchable = re.sub(r"[\s:,_-]+", "", lowered_text)
            for pattern in patterns:
                if re.sub(r"[\s:,_-]+", "", pattern) in searchable:
                    return True
            return False
        return any(pattern in lowered_text for pattern in patterns)


# ── Heuristic pattern tables (small, deterministic, easy to extend) ─────────

# Common Tamil words written in Latin script used to detect Tanglish.
_TANGLISH_HINTS = [
    "enakku",
    "kaasu",
    "kammi",
    "thuttu",
    "tuttu",
    "irukka",
    "venum",
    "vendum",
    "vivasayam",
    "vivasaayam",
    "sondha",
    "tozhilali",
]

_INCOME_LOW_PATTERNS = [
    "kaasu kammi",
    "kammi",
    "thuttu",
    "tuttu",
    "வருமானம் கம்மி",
    "வருமானம்",
    "வருமானம் குறைவு",
    "income low",
    "low income",
    "money kur",
    "kaasu romba kammi",
    "துட்டு",
    "காசு",
    "money less",
    "poor",
    "வசதி இல்லை",
]

_OCCUPATION_PATTERNS = {
    "farmer": [
        "farmer",
        "விவசாயி",
        "விவசாயம்",
        "விவசாய",
        "farming",
        "vivasaayam",
        "vivasayam",
        "agriculture",
        "agricultural",
    ],
    "laborer": [
        "labor",
        "labour",
        "கூலி",
        "tozhilali",
        "daily wages",
    ],
    "student": ["student", "மாணவ", "college", "school"],
}

_CROP_PATTERNS = {
    "paddy": ["paddy", "நெல்", "nell", "rice"],
    "sugarcane": ["sugarcane", "கரும்பு", "karumbu"],
    "cotton": ["cotton", "பருத்தி"],
    "vegetables": ["vegetable", "காய்கறி", "kaykari"],
}

_LAND_OWNER_PATTERNS = {
    "owner": ["land owner", "சொந்த நிலம்", "sondha nilam", "own land", "land"],
    "tenant": ["tenant", "குத்தகை", "kuthakai", "rented land", "lease"],
    "landless": ["landless", "நிலமற்ற", "no land", "illa nilam"],
}

_DOCUMENT_PATTERNS = {
    "aadhaar": ["aadhaar", "ஆதார்", "aadhar"],
    "ration_card": ["ration card", "ரேஷன்", "ration"],
    "income_certificate": ["income certificate", "வருமான சான்று", "income cert"],
    "caste_certificate": ["caste certificate", "இன சான்று", "caste cert"],
    "land_document": ["land document", "நில ஆவணம்", "patta", "land record"],
    "education_certificate": ["education certificate", "கல்வி சான்று", "marksheet"],
}

_SCHEME_NAME_PATTERNS = {
    "PM Kisan": ["pm kisan", "pmkisan", "pm-kisan"],
    "PM Awas Yojana": ["pm awas", "pmaay", "awas yojana"],
    "PM Fasal Bima": ["pm fasal", "fasal bima", "pmfby"],
    "Kisan Credit Card": ["kisan credit", "kcc", "kisan card"],
    "PM Kisan Samman Nidhi": ["samman nidhi", "kisan samman"],
    "National Food Security": ["food security", "nfsa", "food scheme"],
}

_INTENT_PATTERNS = {
    "eligibility": [
        "eligible",
        "தகுதியா",
        "தகுதி",
        "eligibleஆ",
        "eligible a",
        "entitled",
        "apply panna",
        "தகுதி இருக்கா",
    ],
    "search": [
        "scheme",
        "திட்டம்",
        "உதவி",
        "help",
        "assistance",
        "plan",
        "ஏதாவது",
        "which scheme",
        "irukka",
        "கிடைக்குமா",
        "available",
        "என்ன",
        "what scheme",
    ],
    "document": [
        "document",
        "ஆவணம்",
        "documents",
        "certificate",
        "சான்று",
        "papers",
        "what do i need",
        "என்ன வேண்டும்",
    ],
    "application_status": [
        "status",
        "நிலை",
        "application",
        "apply",
        "விண்ணப்பம்",
        "track",
        "where is my",
    ],
    "profile": [
        "my detail",
        "my profile",
        "என் விவரம்",
        "profile",
        "my information",
        "who am i",
    ],
}


@lru_cache(maxsize=1)
def get_text_normalization_service() -> TextNormalizationService:
    """Return the shared singleton TextNormalizationService instance."""
    return TextNormalizationService()
