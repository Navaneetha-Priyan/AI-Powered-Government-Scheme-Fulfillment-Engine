"""Module 4 recommendation and eligibility APIs."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.database.connection import get_db
from app.exceptions.exceptions import AppException
from app.schemas.citizen import SuccessResponse
from app.schemas.recommendation import (
    EligibilityCheckRequest,
    RecommendationGenerateRequest,
    RecommendationHistoryResponse,
    RecommendationListResponse,
    RecommendationMatchResponse,
    RecommendationSummaryResponse,
    EligibilityRuleResponse,
    EligibilityPreviewResponse,
)
from app.services.recommendation_service import RecommendationService

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Eligibility & Recommendations"])


def _build_service(db: Session) -> RecommendationService:
    return RecommendationService(db)


@router.post("/recommendations/generate", response_model=SuccessResponse, status_code=201)
async def generate_recommendations(
    payload: RecommendationGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = _build_service(db)
        service.generate(
            citizen_id=current_user_id,
            limit=payload.limit,
            category=payload.category,
            state=payload.state,
            query_override=payload.query_override,
            request_type="generate",
        )
        summary = service.get_latest_recommendations(current_user_id)
        if background_tasks is not None:
            background_tasks.add_task(logger.info, "Recommendation generation completed for citizen %s", current_user_id)
        return SuccessResponse(success=True, message="Recommendations generated successfully", data=summary.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/recommendations", response_model=SuccessResponse)
async def list_recommendations(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        summary = _build_service(db).get_latest_recommendations(current_user_id)
        return SuccessResponse(success=True, message="Recommendations retrieved successfully", data=summary.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/recommendations/history", response_model=SuccessResponse)
async def recommendation_history(
    limit: int = Query(20, ge=1, le=100),
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        history = _build_service(db).list_history(current_user_id, limit=limit)
        return SuccessResponse(success=True, message="Recommendation history retrieved successfully", data=[item.model_dump(mode="json") for item in history])
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/recommendations/{recommendation_id}", response_model=SuccessResponse)
async def get_recommendation(
    recommendation_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        recommendation = _build_service(db).get_recommendation(recommendation_id, current_user_id)
        return SuccessResponse(success=True, message="Recommendation retrieved successfully", data=recommendation.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.post("/recommendations/refresh", response_model=SuccessResponse, status_code=201)
async def refresh_recommendations(
    payload: RecommendationGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = _build_service(db)
        service.generate(
            citizen_id=current_user_id,
            limit=payload.limit,
            category=payload.category,
            state=payload.state,
            query_override=payload.query_override,
            request_type="refresh",
        )
        summary = service.get_latest_recommendations(current_user_id)
        if background_tasks is not None:
            background_tasks.add_task(logger.info, "Recommendation refresh completed for citizen %s", current_user_id)
        return SuccessResponse(success=True, message="Recommendations refreshed successfully", data=summary.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/eligibility/check", response_model=SuccessResponse)
async def eligibility_check(
    scheme_id: str | None = None,
    scheme_name: str | None = None,
    category: str | None = None,
    state: str | None = None,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        response = _build_service(db).eligibility_check(
            citizen_id=current_user_id,
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            category=category,
            state=state,
        )
        return SuccessResponse(success=True, message="Eligibility evaluated successfully", data=response.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.post("/eligibility/preview", response_model=SuccessResponse)
async def preview_eligible_schemes(
    payload: RecommendationGenerateRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        response = _build_service(db).preview(
            citizen_id=current_user_id,
            limit=payload.limit,
            category=payload.category,
            state=payload.state,
            query_override=payload.query_override,
        )
        return SuccessResponse(success=True, message="Eligibility preview generated successfully", data=response.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/eligibility/rules", response_model=SuccessResponse)
async def get_eligibility_rules(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rules = _build_service(db).list_rules()
        return SuccessResponse(success=True, message="Eligibility rules retrieved successfully", data=[EligibilityRuleResponse.model_validate(rule).model_dump(mode="json") for rule in rules])
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc