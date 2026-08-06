"""Pydantic schemas for Module 4 eligibility and recommendation APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class EligibilityCheckRequest(BaseModel):
    scheme_id: Optional[str] = Field(default=None, description="Specific scheme ID to evaluate")
    scheme_name: Optional[str] = Field(default=None, description="Optional scheme name filter")
    category: Optional[str] = Field(default=None, description="Optional scheme category filter")
    state: Optional[str] = Field(default=None, description="Optional scheme state filter")


class RecommendationGenerateRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    query_override: Optional[str] = Field(default=None, max_length=1000)
    refresh: bool = Field(default=False)


class RecommendationRefreshRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)


class EligibilityRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    condition: str
    operator: str
    value: Optional[Any] = None
    priority: int
    description: Optional[str] = None
    examples: Optional[Any] = None
    scope_type: str
    scope_value: Optional[str] = None
    is_mandatory: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class EligibilityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_id: str
    history_id: Optional[str] = None
    scheme_id: Optional[str] = None
    rule_id: Optional[str] = None
    rule_code: Optional[str] = None
    condition: str
    operator: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    passed: bool
    severity: str
    details: Optional[Any] = None
    created_at: datetime


class RecommendationMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_id: str
    history_id: str
    scheme_id: str
    scheme_name: str
    description: Optional[str] = None
    benefits: Optional[str] = None
    eligibility_status: str
    eligibility_percentage: float
    similarity_score: float
    confidence_score: float
    overall_score: float
    ranking_position: int
    recommendation_reason: Optional[str] = None
    matched_rules: Optional[Any] = None
    missing_requirements: Optional[Any] = None
    required_documents: Optional[Any] = None
    estimated_benefit: Optional[str] = None
    application_ready: bool
    profile_match_percentage: float
    semantic_query: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class RecommendationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_id: str
    request_type: str
    query_text: Optional[str] = None
    top_k: int
    total_candidates: int
    eligible_count: int
    overall_confidence: float
    status: str
    execution_time_ms: int
    context_snapshot: Optional[Any] = None
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    matches: Optional[list[RecommendationMatchResponse]] = None


class RecommendationFeedbackRequest(BaseModel):
    scheme_id: str
    history_id: str
    rating: int = Field(ge=1, le=5)
    is_helpful: bool = True
    feedback_text: Optional[str] = Field(default=None, max_length=2000)


class RecommendationFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_id: str
    history_id: str
    scheme_id: str
    rating: int
    is_helpful: bool
    feedback_text: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class RecommendationSummaryResponse(BaseModel):
    citizen_id: str
    generated_at: datetime
    total_candidates: int
    eligible_count: int
    top_ranked_scheme: Optional[str] = None
    overall_confidence: float
    recommendations: list[RecommendationMatchResponse]
    history: RecommendationHistoryResponse


class EligibilityCheckResponse(BaseModel):
    citizen_id: str
    evaluated_at: datetime
    total_rules: int
    passed_rules: int
    eligibility_percentage: float
    eligible: bool
    matched_rules: list[dict[str, Any]]
    missing_requirements: list[dict[str, Any]]
    required_documents: list[str]
    application_ready: bool
    reasoning: str


class EligibilityPreviewResponse(BaseModel):
    citizen_id: str
    generated_at: datetime
    query: str
    total_candidates: int
    eligible_count: int
    items: list[RecommendationMatchResponse]


class RecommendationListResponse(BaseModel):
    citizen_id: str
    generated_at: datetime
    total: int
    items: list[RecommendationMatchResponse]