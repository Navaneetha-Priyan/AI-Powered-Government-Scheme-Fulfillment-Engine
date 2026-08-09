"""Pydantic schemas for Phase 5 - Voice → Personalized Scheme Recommendation.

These models define the request/response contract for ``POST /voice/recommend``.

The voice layer is a thin adapter. It reuses the existing Module 4
``RecommendationMatchResponse`` schema for the returned schemes so the Flutter
client can keep parsing recommendations exactly as it does for the text-based
flow.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.normalization import NormalizationResponse
from app.schemas.recommendation import RecommendationMatchResponse


class VoiceRecommendationRequest(BaseModel):
    """Request body for ``POST /voice/recommend``.

    Two mutually-supported input styles are allowed:

    1. ``text`` — a raw (or normalized) transcript. The backend will run it
       through the existing normalization service to obtain a structured query.
    2. ``normalization`` — a fully structured ``NormalizationResponse``
       (the output of ``POST /voice/normalize``). When provided, no additional
       normalization is performed.
    """

    text: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=2000,
        description="Raw or normalized voice text to interpret.",
    )
    normalization: Optional[NormalizationResponse] = Field(
        default=None,
        description="Pre-normalized structured query (output of POST /voice/normalize).",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of schemes to return.",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one input style is provided."""
        if not self.text and self.normalization is None:
            raise ValueError("Either 'text' or 'normalization' must be provided")


class VoiceRecommendationProfileView(BaseModel):
    """Minimal, verified profile view returned for a ``profile_query`` intent."""

    citizen_id: str
    full_name: Optional[str] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    income_category: Optional[str] = None
    is_farmer: Optional[bool] = None
    is_disabled: Optional[bool] = None
    caste: Optional[str] = None
    community: Optional[str] = None
    education_level: Optional[str] = None
    family_member_count: Optional[int] = None
    state: Optional[str] = None
    district: Optional[str] = None
    profile_completion_percentage: Optional[int] = None


class VoiceRecommendationResponse(BaseModel):
    """Response body for ``POST /voice/recommend``.

    Reuses the existing ``RecommendationMatchResponse`` for each scheme, so the
    client's existing recommendation rendering continues to work unchanged.
    Minimal voice metadata is appended for the UI.
    """

    schemes: List[RecommendationMatchResponse] = Field(
        default_factory=list,
        description="Personalized scheme recommendations (existing schema).",
    )
    intent: str = Field(
        default="unknown",
        description="The intent that was handled.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Approximate language tag of the query.",
    )
    normalized_text: Optional[str] = Field(
        default=None,
        description="Normalized representation of the citizen's query.",
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence in the structured interpretation (0.0 to 1.0).",
    )
    source: Optional[str] = Field(
        default=None,
        description="Whether normalization came from llm or heuristic.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-friendly message for unsupported intents / no results.",
    )
    profile: Optional[VoiceRecommendationProfileView] = Field(
        default=None,
        description="Verified profile returned for profile_query intents.",
    )
