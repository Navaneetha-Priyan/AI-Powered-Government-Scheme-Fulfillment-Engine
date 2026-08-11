"""Phase 5 - Voice → Personalized Government Scheme Recommendation Adapter.

This service is the *smallest* bridge between the Phase 4 normalized voice
query and the existing Module 4 recommendation/eligibility system.

It does NOT implement:
- eligibility rules (reused from ``EligibilityEngineService``)
- RAG / vector search (reused from ``GovernmentSchemeService.semantic_search``)
- scheme retrieval (reused from ``RecommendationService``)

It does NOT accept Aadhaar / ration card / citizen ID from the voice request,
and it never lets LLM-extracted entities overwrite the verified citizen profile.

Flow
----
NormalizationResponse
    -> intent mapping
    -> build a *search* query_override from `normalized_text` + entities
    -> RecommendationService.generate(citizen_id, query_override=..., request_type="voice")
    -> existing eligibility + RAG -> existing RecommendationMatchResponse list

The authenticated citizen profile remains the source of truth for eligibility.
Voice entities are treated as query/context information only.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.exceptions.exceptions import (
    ProfileNotFoundError,
    UnsupportedIntentError,
)
from app.repositories.citizen_repository import CitizenRepository
from app.repositories.citizen_profile_repository import CitizenProfileRepository
from app.repositories.recommendation_repository import RecommendationMatchRepository
from app.schemas.normalization import NormalizationResponse
from app.schemas.recommendation import RecommendationMatchResponse
from app.schemas.voice_recommendation import (
    VoiceRecommendationProfileView,
    VoiceRecommendationResponse,
)
from app.services.recommendation_service import RecommendationService

logger = get_logger(__name__)

# Intents that route through the existing eligibility/recommendation pipeline.
_SEARCH_LIKE_INTENTS = {
    "scheme_search",
    "scheme_eligibility",
    "document_requirement",
}


class VoiceQueryService:
    """Convert a normalized voice query into existing-system recommendations."""

    def __init__(self, db: Session):
        self.db = db
        self._recommendation_service = RecommendationService(db)
        self._profile_repo = CitizenProfileRepository(db)
        self._citizen_repo = CitizenRepository(db)

    def recommend(
        self,
        citizen_id: str,
        normalization: Optional[NormalizationResponse] = None,
        limit: int = 5,
    ) -> VoiceRecommendationResponse:
        """Handle a normalized voice query for the authenticated citizen.

        :param citizen_id: Verified citizen id from the JWT (source of truth).
        :param normalization: Structured Phase 4 query (may be None).
        :param limit: Maximum schemes to return.
        """
        normalization = normalization or self._empty_normalization()

        intent = self._resolved_intent(normalization)
        language = normalization.language
        normalized_text = normalization.normalized_text
        confidence = normalization.confidence
        source = normalization.source

        # 1) profile_query -> return the verified profile (no eligibility logic).
        if intent == "profile_query":
            return self._handle_profile_query(
                citizen_id,
                intent=intent,
                language=language,
                normalized_text=normalized_text,
                confidence=confidence,
                source=source,
            )

        # 2) application_status / unknown -> clear structured "not supported".
        if intent == "application_status":
            return self._unsupported_response(
                intent=intent,
                language=language,
                normalized_text=normalized_text,
                confidence=confidence,
                source=source,
                message=(
                    "Application status tracking is not available yet. "
                    "Try asking about schemes you may be eligible for."
                ),
            )

        if intent == "unknown":
            return self._unsupported_response(
                intent=intent,
                language=language,
                normalized_text=normalized_text,
                confidence=confidence,
                source=source,
                message=(
                    "I could not understand your request. "
                    "Try asking something like 'enakku farmer scheme irukka?'"
                ),
            )

        # 3) scheme_search / scheme_eligibility / document_requirement ->
        #    route through the existing recommendation/eligibility pipeline.
        if intent not in _SEARCH_LIKE_INTENTS:
            raise UnsupportedIntentError(f"Intent '{intent}' is not supported")

        return self._recommend_schemes(
            citizen_id,
            normalization,
            intent,
            limit,
        )

    # ── Intent handling ───────────────────────────────────────────────────

    def _recommend_schemes(
        self,
        citizen_id: str,
        normalization: NormalizationResponse,
        intent: str,
        limit: int,
    ) -> VoiceRecommendationResponse:
        """Reuse the existing recommendation pipeline for search-like intents."""
        query_override = self._build_search_query(normalization)

        # Reuses existing eligibility rules, RAG, scheme retrieval, ranking, and
        # persists the matches to the DB. `request_type="voice"` tags the
        # history as a voice interaction.
        history, _, _, _, _, _ = self._recommendation_service.generate(
            citizen_id=citizen_id,
            limit=limit,
            query_override=query_override,
            request_type="voice",
        )

        # Read the persisted CitizenSchemeMatch rows (the same source the
        # existing text-based recommendation flow uses), so the response schema
        # is identical to the existing recommendation API.
        matches = RecommendationMatchRepository(self.db).list_for_history(history.id)
        scheme_responses = [
            RecommendationMatchResponse.model_validate(match)
            for match in matches
        ]

        message = None
        if not scheme_responses:
            message = (
                "No eligible schemes matched your current profile. "
                "Update your profile or documents and try again."
            )

        return VoiceRecommendationResponse(
            schemes=scheme_responses,
            intent=intent,
            language=normalization.language,
            normalized_text=normalization.normalized_text,
            confidence=normalization.confidence,
            source=normalization.source,
            message=message,
        )

    def _handle_profile_query(
        self, citizen_id: str, **voice_meta: Any
    ) -> VoiceRecommendationResponse:
        """Return the verified citizen profile (no LLM-inferred facts)."""
        profile = self._profile_repo.get_by_citizen_id(citizen_id)
        if not profile:
            raise ProfileNotFoundError(citizen_id)

        citizen = self._citizen_repo.get_by_id(citizen_id)

        view = VoiceRecommendationProfileView(
            citizen_id=citizen_id,
            full_name=citizen.full_name if citizen else None,
            occupation=profile.occupation,
            annual_income=profile.annual_income,
            income_category=_enum_value(profile.income_category),
            is_farmer=profile.is_farmer,
            is_disabled=profile.is_disabled,
            caste=profile.caste,
            community=profile.community,
            education_level=profile.education_level,
            family_member_count=profile.family_member_count,
            state=citizen.state if citizen else None,
            district=citizen.district if citizen else None,
            profile_completion_percentage=profile.profile_completion_percentage,
        )

        return VoiceRecommendationResponse(
            schemes=[],
            intent="profile_query",
            language=voice_meta.get("language"),
            normalized_text=voice_meta.get("normalized_text"),
            confidence=voice_meta.get("confidence", 0.0),
            source=voice_meta.get("source"),
            message="Here is your verified profile information.",
            profile=view,
        )

    def _unsupported_response(self, **data: Any) -> VoiceRecommendationResponse:
        return VoiceRecommendationResponse(
            schemes=[],
            intent=data.get("intent", "unknown"),
            language=data.get("language"),
            normalized_text=data.get("normalized_text"),
            confidence=data.get("confidence", 0.0),
            source=data.get("source"),
            message=data.get("message", "This request is not supported."),
        )

    # ── Query building (search context only, never profile facts) ────────

    def _build_search_query(self, normalization: NormalizationResponse) -> str:
        """Build a *search* query from the voice query.

        The returned string is used ONLY as the ``query_override`` for the
        existing semantic search. It does not influence the eligibility rules,
        which always read from the verified citizen profile.
        """
        parts: list[str] = []
        if normalization.normalized_text:
            parts.append(normalization.normalized_text)

        entities = normalization.entities or {}
        for key in ("crop", "scheme_name", "document_type", "land_ownership"):
            value = entities.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())

        return " ".join(part for part in parts if part).strip()

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _resolved_intent(normalization: NormalizationResponse) -> str:
        intent = (normalization.intent or "unknown").strip().lower()
        return intent if intent else "unknown"

    @staticmethod
    def _empty_normalization() -> NormalizationResponse:
        return NormalizationResponse(
            language="unknown",
            intent="unknown",
            normalized_text="",
            entities={},
            confidence=0.0,
            source="heuristic",
        )


def _enum_value(value: Any) -> Optional[str]:
    """Return the string value of an enum (or the value itself)."""
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
