"""Module 3 REST APIs."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.database.connection import SessionLocal, get_db
from app.exceptions.exceptions import AppException
from app.models.government_scheme import ProcessingStatus
from app.schemas.citizen import SuccessResponse
from app.schemas.government_scheme import (
    SchemeCreateRequest,
    SchemeDocumentResponse,
    SchemeSearchRequest,
    SchemeSearchResponse,
    SchemeUpdateRequest,
)
from app.services.government_scheme_service import GovernmentSchemeService

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Government Scheme Knowledge Base"])


def _serialize_model(model):
    if model is None:
        return None
    if hasattr(model, "model_validate"):
        return model.model_validate(model).model_dump(mode="json")
    if hasattr(model, "__dict__") and hasattr(model, "__table__"):
        payload = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if isinstance(value, datetime):
                payload[column.name] = value.isoformat()
            elif hasattr(value, "value"):
                payload[column.name] = value.value
            else:
                payload[column.name] = value
        return payload
    return model


def _process_document_background(document_id: str, db: Session) -> None:
    del db
    background_db = SessionLocal()
    try:
        GovernmentSchemeService(background_db).process_document(document_id)
    except Exception as exc:
        logger.exception("Background processing failed for document %s: %s", document_id, exc)
    finally:
        background_db.close()


@router.post("/schemes", response_model=SuccessResponse, status_code=201)
async def create(
    payload: SchemeCreateRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        scheme = GovernmentSchemeService(db).create_scheme(payload.model_dump())
        return SuccessResponse(success=True, message="Scheme created successfully", data=_serialize_model(scheme))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/schemes", response_model=SuccessResponse)
async def list_schemes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status: str | None = None,
    query: str | None = None,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = GovernmentSchemeService(db).list_schemes(skip, limit, category, status, query)
    return SuccessResponse(
        success=True,
        message="Schemes retrieved successfully",
        data={
            "items": [_serialize_model(item) for item in items],
            "skip": skip,
            "limit": limit,
            "total": total,
        },
    )


@router.get("/schemes/{scheme_id}", response_model=SuccessResponse)
async def get_scheme(
    scheme_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        scheme = GovernmentSchemeService(db).get_scheme(scheme_id)
        return SuccessResponse(success=True, message="Scheme retrieved successfully", data=_serialize_model(scheme))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.put("/schemes/{scheme_id}", response_model=SuccessResponse)
async def update(
    scheme_id: str,
    payload: SchemeUpdateRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        scheme = GovernmentSchemeService(db).update_scheme(scheme_id, payload.model_dump(exclude_unset=True))
        return SuccessResponse(success=True, message="Scheme updated successfully", data=_serialize_model(scheme))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.delete("/schemes/{scheme_id}", response_model=SuccessResponse)
async def delete(
    scheme_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        GovernmentSchemeService(db).delete_scheme(scheme_id)
        return SuccessResponse(success=True, message="Scheme deleted successfully", data=None)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.post("/schemes/{scheme_id}/documents/upload", response_model=SuccessResponse, status_code=201)
async def upload(
    scheme_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = GovernmentSchemeService(db)
        document = service.save_pdf(scheme_id, file, current_user_id)
        if db.bind is not None and getattr(db.bind.dialect, "name", "") == "sqlite":
            service.process_document(document.id)
        elif background_tasks is not None:
            background_tasks.add_task(_process_document_background, document.id, db)
        return SuccessResponse(
            success=True,
            message="PDF uploaded successfully",
            data={
                **_serialize_model(document),
                "processing_status": ProcessingStatus.PENDING.value,
            },
        )
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.post("/documents/{document_id}/process", response_model=SuccessResponse)
async def process(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = GovernmentSchemeService(db)
        if db.bind is not None and getattr(db.bind.dialect, "name", "") == "sqlite":
            chunks_created = service.process_document(document_id)
            return SuccessResponse(success=True, message="Document processed successfully", data={"chunks_created": chunks_created})

        if background_tasks is not None:
            background_tasks.add_task(_process_document_background, document_id, db)
            document = service.get_document(document_id)
            return SuccessResponse(
                success=True,
                message="Document processing started successfully",
                data={
                    **_serialize_model(document),
                    "processing_status": ProcessingStatus.PROCESSING.value,
                },
            )

        chunks_created = service.process_document(document_id)
        return SuccessResponse(success=True, message="Document processed successfully", data={"chunks_created": chunks_created})
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.get("/documents/{document_id}/status", response_model=SuccessResponse)
async def status(
    document_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        document = GovernmentSchemeService(db).get_document(document_id)
        return SuccessResponse(success=True, message="Document status retrieved successfully", data=_serialize_model(document))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc


@router.post("/search/schemes", response_model=SuccessResponse)
async def search(
    payload: SchemeSearchRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        items = GovernmentSchemeService(db).semantic_search(payload.query, payload.limit, payload.category)
        response = SchemeSearchResponse(items=items, query=payload.query, limit=payload.limit, total=len(items))
        return SuccessResponse(success=True, message="Semantic search completed successfully", data=response.model_dump(mode="json"))
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc
