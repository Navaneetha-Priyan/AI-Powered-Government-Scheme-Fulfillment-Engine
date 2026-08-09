"""Pydantic schemas for Phase 4 - Multilingual, Dialect & Intent Normalization.

These models define the request/response contract for ``POST /voice/normalize``
and the internal structured representation produced by
``TextNormalizationService``.
"""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

# Supported language tags. We intentionally keep this coarse-grain: the goal is
# semantic interpretation, not perfect linguistic classification.
LanguageTag = Literal["ta", "en", "ta-en", "unknown"]

# Supported intents. ``unknown`` is used when the request cannot be confidently
# mapped to any known intent.
Intent = Literal[
    "scheme_search",
    "scheme_eligibility",
    "application_status",
    "document_requirement",
    "profile_query",
    "unknown",
]

# Source of a normalized result.
NormalizationSource = Literal["llm", "heuristic"]


class NormalizationRequest(BaseModel):
    """Request body for ``POST /voice/normalize``.

    ``text`` is the raw transcript produced by the speech-to-text layer.
    """

    text: str = Field(
        ...,
        min_length=1,
        description="Raw transcript to normalize (Tamil, English, or mixed).",
    )


class NormalizationResponse(BaseModel):
    """Structured representation of a citizen's voice query.

    Phase 4 only produces this structured query. It is not yet evaluated by the
    eligibility engine or RAG (that is Phase 5).
    """

    language: LanguageTag = Field(
        default="unknown",
        description="Approximate language tag: ta, en, ta-en, or unknown.",
    )
    intent: Intent = Field(
        default="unknown",
        description="Semantic intent of the user's request.",
    )
    normalized_text: str = Field(
        default="",
        description="Normalized, meaning-preserving representation of the transcript.",
    )
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Extracted entities. Only attributes explicitly present in the user's "
            "speech are included. No citizen attributes are inferred."
        ),
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the structured interpretation (0.0 to 1.0).",
    )
    source: NormalizationSource = Field(
        default="heuristic",
        description="Whether the result came from the LLM or the heuristic fallback.",
    )


class NormalizationResult(NormalizationResponse):
    """Internal result type used by ``TextNormalizationService``.

    Mirrors ``NormalizationResponse`` but is kept as a separate model so the
    service can attach internal metadata (e.g. raw LLM payload) without
    affecting the public API contract. For now it is an alias of the response
    model; extend this class if internal-only fields are needed later.
    """
