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
from app.services.scheme_query_helpers import detect_scheme_names_in_text
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

# Scheme-related occupations recognized by the normalization heuristics.
# Used to detect likely LLM hallucinations (e.g. "musician" from corrupted audio).
_KNOWN_SCHEME_OCCUPATIONS_SET = {
    "farmer", "cultivator", "agricultural labourer", "farm worker",
    "agricultural worker", "landowner", "tenant", "student", "laborer",
    "labourer", "none",
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
                return self._recover_scheme_names(cleaned, result)
        except LLMUnavailableError:
            logger.warning("LLM unavailable; using heuristic fallback")
        except NormalizationError:
            logger.warning("LLM returned invalid result; using heuristic fallback")

        # 2) Deterministic heuristic fallback.
        return self._recover_scheme_names(cleaned, self._normalize_with_heuristics(cleaned))

    def _recover_scheme_names(self, raw_text: str, result: NormalizationResult) -> NormalizationResult:
        """Reconcile LLM/heuristic output against scheme names found in the raw text.

        Whisper frequently corrupts or drops proper-noun scheme names (e.g. PM Kisan),
        and the LLM can then hallucinate an unrelated concept (e.g. "musician").
        This step detects known scheme names directly from the raw transcript
        (Tamil markers + romanized aliases) and ensures they are reflected in the
        output, so downstream retrieval has a chance to find them.

        This is intentionally conservative: it only ADDS a scheme name when one is
        detectable in the raw text but missing from the result, and it downgrades
        confidence when the LLM appears to have invented an unrelated occupation.
        """
        detected = detect_scheme_names_in_text(raw_text)
        if not detected:
            return result

        entities = dict(result.entities or {})
        existing_scheme = entities.get("scheme_name")
        existing_scheme_str = str(existing_scheme).strip() if existing_scheme else ""

        # If no scheme name was extracted but we detected one in the raw text,
        # add the first detected scheme name.
        new_scheme = None
        if not existing_scheme_str:
            new_scheme = detected[0]
            entities["scheme_name"] = new_scheme

        # Hallucination guard: if the LLM invented an occupation that is not a
        # known scheme-related occupation while a scheme name is present in the
        # raw text, the occupation is likely spurious. Downgrade confidence so
        # the pipeline treats the result as uncertain rather than confidently wrong.
        occupation = entities.get("occupation")
        if isinstance(occupation, str) and occupation:
            occ_key = occupation.strip().lower().replace("_", " ")
            if occ_key not in _KNOWN_SCHEME_OCCUPATIONS_SET and detected:
                confidence = min(result.confidence, 0.55)
                # Strip the hallucinated occupation from entities so downstream
                # retrieval uses the real query signal, not the hallucination.
                entities.pop("occupation", None)
                if new_scheme is None and not existing_scheme_str:
                    entities["scheme_name"] = detected[0]
                    new_scheme = detected[0]
                return NormalizationResult(
                    language=result.language,
                    intent=result.intent,
                    normalized_text=result.normalized_text,
                    entities=entities,
                    confidence=confidence,
                    source=result.source,
                )

        if new_scheme is None:
            return result

        return NormalizationResult(
            language=result.language,
            intent=result.intent,
            normalized_text=result.normalized_text,
            entities=entities,
            confidence=result.confidence,
            source=result.source,
        )

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
            "## Domain vocabulary (Tamil government schemes)\n\n"
            "Learn and preserve these meanings exactly:\n\n"
            "- விவசாயி = farmer\n"
            "- விவசாயிகள் = farmers\n"
            "- விவசாயம் = agriculture/farming\n"
            "- விவசாயிகளுக்கு = for farmers\n"
            "- விவசாயிகளுக்கான = for farmers\n"
            "- விவசாயத்துக்கு = for agriculture/farming\n"
            "- அரசு = government\n"
            "- திட்டம் = scheme\n"
            "- திட்டங்கள் = schemes\n"
            "- அரசு திட்டம் = government scheme\n"
            "- உதவி = assistance/help\n"
            "- துட்டு / காசு / காசு கம்மி = money/income is low\n"
            "- கம்மி = low/less\n"
            "- eligibleஆ = eligible\n"
            "- இருக்கா = is there/are there\n\n"
            "Also recognize common Tanglish forms: vivasayam/vivasaayam = "
            "agriculture/farming, enakku = for me, venum/vendum = need, "
            "irukka = is there, kaasu = money, kammi = low.\n\n"
            "## Intent classification\n\n"
            "Classify the user's intent precisely:\n\n"
            "- Use \"scheme_search\" when the user is:\n"
            "    * asking what government schemes are available\n"
            "    * asking whether any schemes exist\n"
            "    * asking to find schemes\n"
            "    * asking for schemes related to an occupation, crop, land, "
            "income group, etc.\n"
            "    * asking for general availability of government assistance\n\n"
            "  Examples:\n"
            "    * \"எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?\" -> "
            "scheme_search\n"
            "    * \"விவசாயிகளுக்கான திட்டங்கள் என்ன?\" -> scheme_search\n"
            "    * \"விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்\" -> "
            "scheme_search\n"
            "    * \"What government schemes are available for farmers?\" -> "
            "scheme_search\n"
            "    * \"Are there any government schemes available for "
            "agriculture?\" -> scheme_search\n"
            "    * \"Enakku farmer scheme edhavadhu irukka?\" -> "
            "scheme_search\n\n"
            "- Use \"scheme_eligibility\" ONLY when the user explicitly asks "
            "whether they personally qualify or are eligible for a specific "
            "named scheme or a clearly identified scheme.\n\n"
            "  Examples:\n"
            "    * \"PM Kisan schemeக்கு நான் eligibleஆ?\" -> "
            "scheme_eligibility\n"
            "    * \"Am I eligible for PM Kisan?\" -> scheme_eligibility\n"
            "    * \"நான் இந்த திட்டத்திற்கு தகுதியானவனா?\" -> "
            "scheme_eligibility\n"
            "    * \"இந்த திட்டத்திற்கு நான் தகுதியுள்ளவனா?\" -> "
            "scheme_eligibility\n"
            "    * \"Can I apply for PM Kisan?\" -> scheme_eligibility\n\n"
            "Critical distinction: Do NOT classify a question as "
            "\"scheme_eligibility\" merely because it contains \"இருக்கா?\" / "
            "\"is there?\", the word \"scheme\", an occupation such as farmer, "
            "or a request for government assistance. For example, "
            "\"எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?\" means "
            "\"Are there any government schemes available for agriculture?\" "
            "and is \"scheme_search\", NOT \"scheme_eligibility\". The word "
            "\"இருக்கா?\" means availability/existence in this context, not "
            "personal eligibility.\n\n"
            "## Critical rules\n\n"
            "1. Preserve the user's actual semantic meaning. If the user "
            "mentions farmers or agriculture (விவசாயி, விவசாயம், விவசாய, "
            "vivasayam, farmer, farming, agriculture), the normalized_text "
            "MUST preserve that meaning and the occupation entity MUST be "
            "\"farmer\".\n\n"
            "2. NEVER change \"farmer/agriculture\" into an unrelated "
            "occupation or domain such as \"professional\", \"professionals\", "
            "\"vocational\", \"healthcare\", \"teacher\", \"laborer\", or any "
            "other invented occupation. If the input contains farmer/agriculture "
            "words, output farmer.\n\n"
            "3. NEVER invent an occupation. Only set the occupation entity if "
            "the user explicitly mentions an occupation or domain.\n\n"
            "4. The normalized_text must be a short English semantic "
            "representation suitable for downstream semantic retrieval. For "
            "example:\n"
            "   - \"விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்\" -> \"I need "
            "government schemes for farmers\"\n"
            "   - \"எனக்கு விவசாய திட்டம் வேண்டும்\" -> \"I need a government "
            "scheme related to agriculture/farmers\"\n"
            "   - \"விவசாயிகளுக்கான திட்டங்கள் என்ன?\" -> \"What government "
            "schemes are available for farmers?\"\n"
            "   - \"எனக்கு விவசாயத்துக்கு ஏதாவது அரசு திட்டம் இருக்கா?\" -> "
            "\"Are there any government schemes available for "
            "farmers/agriculture?\"\n\n"
            "5. Do NOT merely paraphrase the Tamil input back into Tamil. The "
            "normalized_text should be in English.\n\n"
            "6. Do NOT classify a phrase as scheme_name unless it is an actual "
            "named government scheme (e.g., \"PM Kisan\", \"PM Awas Yojana\", "
            "\"PM Fasal Bima\", \"Kisan Credit Card\"). Generic phrases such "
            "as \"விவசாயிகளுக்கான திட்டங்கள்\", \"அரசு திட்டம்\", \"திட்டம்\" "
            "must NOT become scheme_name.\n\n"
            "7. Do not invent facts, scheme names, eligibility conditions, "
            "income, occupation, land size, or other profile information.\n\n"
            "8. If uncertain, preserve the user's original semantic meaning "
            "rather than guessing a different domain.\n\n"
            "9. Provide a conservative confidence estimate (0.0 to 1.0) based "
            "on how certain you are. Do not default to 1.0. Use lower "
            "confidence (e.g., 0.5-0.7) when the input is ambiguous or "
            "contains slang.\n\n"
            "10. Recognize colloquial Tamil and common Tamil slang; normalize "
            "slang into standard semantic concepts (e.g. 'thuttu'/'kaasu' -> "
            "low income).\n\n"
            "11. Understand English words embedded in Tamil sentences and "
            "Tanglish/code-switching.\n\n"
            "12. Never change or assume citizen profile information.\n\n"
            "13. The word \"இருக்கா?\" / \"is there?\" indicates availability "
            "or existence and maps to \"scheme_search\" in these contexts, not "
            "personal eligibility. Only classify as \"scheme_eligibility\" "
            "when the user explicitly asks whether they personally qualify "
            "for a specific named or clearly identified scheme.\n\n"
            "Return ONLY a single valid JSON object with EXACTLY these keys:\n"
            "{\n"
            "  \"language\": \"ta\" or \"en\" or \"ta-en\" or \"unknown\",\n"
            "  \"intent\": \"scheme_search\" or \"scheme_eligibility\" or "
            "\"application_status\" or \"document_requirement\" or "
            "\"profile_query\" or \"unknown\",\n"
            "  \"normalized_text\": \"a short meaning-preserving English "
            "representation (no invented facts)\",\n"
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
        the trimmed text. For common Tanglish/Tamil patterns, it converts to English
semantic representations suitable for retrieval.
        """
        normalized = re.sub(r"\s+", " ", text).strip()
        lowered = normalized.lower()

        # Tamil pattern -> English semantic mapping (small, deterministic)
        # Order matters: more specific patterns first.
        tamil_patterns = [
            # "விவசாயிகளுக்கு என்ன அரசு திட்டங்கள் இருக்கிறது?" -> "What government schemes are available for farmers?"
            (r"விவசாயி.+?க்கு\s+என்ன\s+அரசு\s+திட்டங்கள்?\s+இருக்க[^\s?]*\?", "What government schemes are available for farmers?"),
            # "விவசாயிகளுக்கான திட்டங்கள் என்ன?" -> "What government schemes for farmers?"
            (r"விவசாயி.+?க்கான\s+திட்டங்கள்?\s+என்ன", "What government schemes are available for farmers?"),
            # "விவசாயிகளுக்கு அரசு திட்டம் வேண்டும்" -> "I need government schemes for farmers"
            (r"விவசாயி.+?க்கு\s+அரசு\s+திட்டம்\s+வேண்டும்", "I need government schemes for farmers"),
            # "எனக்கு விவசாயத்திற்கு ஏதாவது அரசு திட்டம் இருக்கா?" -> "Are there any government schemes for agriculture?"
            (r"எனக்கு\s+விவசாய(?:த்தற்க|ம்)?\s+(?:ஏதாவது|எதாவது)\s+அரசு\s+திட்டம்\s+இருக்க(?:ா|ு)", "Are there any government schemes available for agriculture?"),
            # "எனக்கு விவசாய திட்டம் வேண்டும்" -> "I need a government scheme for agriculture"
            (r"எனக்கு\s+விவசாய\s+திட்டம்\s+வேண்டும்", "I need a government scheme for agriculture"),
            # Generic: "எனக்கு X திட்டம் வேண்டும்" -> "I need a government scheme for X"
            (r"எனக்கு\s+(.+?)\s+திட்டம்\s+வேண்டும்", "I need a government scheme for {0}"),
            # Generic: "X க்கு ஏதாவது அரசு திட்டம் இருக்கா?" -> "Are there any government schemes for X?"
            (r"(.+?)\s+(?:க்கு|க்காக)\s+(?:ஏதாவது|எதாவது)\s+அரசு\s+திட்டம்\s+இருக்க(?:ா|ு)", "Are there any government schemes available for {0}?"),
        ]

        for pattern, template in tamil_patterns:
            match = re.search(pattern, normalized)
            if match:
                if match.groups():
                    key_term = match.group(1).strip()
                    # Clean Tamil terms to English
                    key_term = self._clean_tamil_term(key_term)
                    if key_term:
                        return template.format(key_term)
                else:
                    return template

        # Code-mixed pattern -> English semantic mapping
        # Handle Tamil-English mixed queries like "எனக்கு agricultureக்கு ஏதாவது government scheme இருக்கா?"
        code_mixed_patterns = [
            # "எனக்கு X-க்கு ஏதாவது government scheme irukka/irukku/இருக்கா/இருக்கு" -> "Are there any government schemes for X?"
            (r"எனக்கு\s+(.+?)(?:க்கு|க்காக)\s+(?:ஏதாவது|எதாவது)\s+government\s+scheme\s+(?:irukka|irukku|இருக்கா|இருக்கு)", "Are there any government schemes available for {0}?"),
            # "X-க்கு government scheme irukka/irukku/இருக்கா/இருக்கு" -> "Are there any government schemes for X?"
            (r"(.+?)(?:க்கு|க்காக)\s+government\s+scheme\s+(?:irukka|irukku|இருக்கா|இருக்கு)", "Are there any government schemes available for {0}?"),
        ]

        for pattern, template in code_mixed_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                if match.groups():
                    key_term = match.group(1).strip()
                    key_term = self._clean_mixed_term(key_term)
                    if key_term:
                        return template.format(key_term)
                else:
                    return template

        # Tanglish pattern -> English semantic mapping (small, deterministic)
        # Order matters: more specific patterns first.
        tanglish_patterns = [
            # "enakku X scheme edhavadhu irukka/venum" -> "Are there any government schemes for X?" / "I need a government scheme for X"
            (r"\benakku\s+(.+?)\s+scheme\s+(?:edhavadhu|ethavathu|enna)?\s*(irukka|venum|vendum|irukku)\b", "Are there any government schemes available for {0}?"),
            # "X-ku government scheme irukka" -> "Are there any government schemes for X?"
            (r"\b(.+?)\s*[-]?ku\s+government\s+scheme\s+(irukka|irukku)\b", "Are there any government schemes available for {0}?"),
            # "X-ku scheme irukka/venum" -> "Are there any government schemes for X?" / "I need a government scheme for X"
            (r"\b(.+?)\s*[-]?ku\s+scheme\s+(irukka|venum|vendum|irukku)\b", "Are there any government schemes available for {0}?"),
            # "enakku X scheme venum/vendum" -> "I need a government scheme for X"
            (r"\benakku\s+(.+?)\s+scheme\s+(venum|vendum)\b", "I need a government scheme for {0}"),
            # "X scheme edhavadhu irukka" -> "Are there any government schemes for X?"
            (r"\b(.+?)\s+scheme\s+(?:edhavadhu|ethavathu|enna)?\s*(irukka|irukku)\b", "Are there any government schemes available for {0}?"),
            # "X scheme venum/vendum" -> "I need a government scheme for X"
            (r"\b(.+?)\s+scheme\s+(venum|vendum)\b", "I need a government scheme for {0}"),
            # "government scheme X" -> "government schemes for X"
            (r"\bgovernment\s+scheme\s+(.+)\b", "government schemes for {0}"),
            # "any scheme" / "any schemes" -> "any government schemes"
            (r"\bany\s+schemes?\b", "any government schemes"),
            # "govt scheme" -> "government scheme"
            (r"\bgovt\s+scheme\b", "government scheme"),
            # "scheme" alone -> "government scheme"
            (r"\bscheme\b", "government scheme"),
        ]

        for pattern, template in tanglish_patterns:
            match = re.search(pattern, lowered)
            if match:
                # Extract the key term(s) and clean them if pattern has capture groups
                if match.groups():
                    key_term = match.group(1).strip()
                    key_term = self._clean_tanglish_term(key_term)
                    if key_term:
                        return template.format(key_term)
                else:
                    # Pattern without capture groups - use template directly
                    return template

        return normalized

    def _clean_tanglish_term(self, term: str) -> str:
        """Clean and normalize a Tanglish term to English semantic equivalent."""
        term = term.lower().strip()

        # Map common Tanglish terms to English
        term_mapping = {
            # Occupation / domain
            "farmer": "farmers",
            "farmers": "farmers",
            "vivasayam": "farmers/agriculture",
            "vivasaayam": "farmers/agriculture",
            "vivasayi": "farmers",
            "agriculture": "agriculture",
            "agricultural": "agriculture",
            "farming": "farmers/agriculture",
            # Intent markers that should be removed from the term
            "edhavadhu": "",
            "ethavathu": "",
            "enna": "",
            "veenum": "",
            "vendum": "",
            "irukka": "",
            "irukku": "",
            "kudukka": "",
        }

        # Replace mapped terms
        for tanglish, english in term_mapping.items():
            if tanglish in term:
                term = term.replace(tanglish, english)

        # Clean up
        term = re.sub(r"[\s\-_]+", " ", term).strip()
        # Remove empty filler words
        filler = {"for", "the", "a", "an", "to", "me", "my", "i", "enakku", "enaku", "any", "some"}
        words = [w for w in term.split() if w not in filler]
        term = " ".join(words).strip()

        return term

    def _clean_tamil_term(self, term: str) -> str:
        """Clean and normalize a Tamil term to English semantic equivalent."""
        term = term.strip()

        # Map common Tamil terms to English
        term_mapping = {
            # Occupation / domain
            "விவசாயி": "farmers",
            "விவசாயிகள்": "farmers",
            "விவசாயம்": "agriculture",
            "விவசாய": "agriculture",
            "விவசாயத்திற்க": "agriculture",
            "விவசாயத்துக்கு": "agriculture",
            "விவசாயத்திற்கு": "agriculture",
            "அரசு": "government",
            "திட்டம்": "scheme",
            "திட்டங்கள்": "schemes",
            "ஏதாவது": "",
            "எதாவது": "",
            "என்ன": "",
            "வேண்டும்": "",
            "இருக்கிறது": "",
            "இருக்கிறதா": "",
            "இருக்கிறதா?": "",
            "இருக்கா": "",
            "இருக்கா?": "",
        }

        # Replace mapped terms
        for tamil, english in term_mapping.items():
            if tamil in term:
                term = term.replace(tamil, english)

        # Clean up
        term = re.sub(r"[\s\-_]+", " ", term).strip()
        # Remove empty filler words
        filler = {"for", "the", "a", "an", "to", "me", "my", "i", "any", "some", "available"}
        words = [w for w in term.split() if w not in filler]
        term = " ".join(words).strip()

        return term

    def _clean_mixed_term(self, term: str) -> str:
        """Clean and normalize a code-mixed (Tamil-English) term to English semantic equivalent."""
        term = term.strip()

        # Map common mixed terms to English
        term_mapping = {
            # Tamil words
            "விவசாயி": "farmers",
            "விவசாயிகள்": "farmers",
            "விவசாயம்": "agriculture",
            "விவசாய": "agriculture",
            "அரசு": "government",
            "திட்டம்": "scheme",
            "திட்டங்கள்": "schemes",
            "ஏதாவது": "",
            "எதாவது": "",
            "என்ன": "",
            "வேண்டும்": "",
            "இருக்க": "",  # matches irukka, irukku, etc.
            # English words
            "agriculture": "agriculture",
            "agricultural": "agriculture",
            "farming": "farmers/agriculture",
            "farmer": "farmers",
            "farmers": "farmers",
            "government": "government",
            "scheme": "scheme",
            "schemes": "schemes",
            "govt": "government",
        }

        # Replace mapped terms (case-insensitive for English)
        for key, english in term_mapping.items():
            if key.lower() in term.lower():
                # Replace preserving case-insensitively
                import re
                term = re.sub(re.escape(key), english, term, flags=re.IGNORECASE)

        # Clean up
        term = re.sub(r"[\s\-_]+", " ", term).strip()
        # Remove empty filler words
        filler = {"for", "the", "a", "an", "to", "me", "my", "i", "any", "some", "available", "enakku", "enaku", "எனக்கு", "எனக்க"}
        words = [w for w in term.split() if w not in filler]
        term = " ".join(words).strip()

        return term

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
        "cultivator",
        "agricultural worker",
        "agricultural labourer",
        "farm worker",
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
