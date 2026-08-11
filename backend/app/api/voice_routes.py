"""Voice Assistant REST APIs (Phase 2 - Speech-to-Text).

Phase 4 adds ``POST /voice/normalize`` for multilingual, dialect & intent
normalization. The existing ``POST /voice/transcribe`` endpoint is unchanged.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import AppException
from app.schemas.normalization import NormalizationRequest, NormalizationResponse
from app.schemas.voice_recommendation import (
    VoiceRecommendationRequest,
    VoiceRecommendationResponse,
)
from app.services.speech_to_text_service import (
    SpeechToTextModelNotLoadedError,
    SpeechToTextService,
    get_speech_to_text_service,
)
from app.services.text_normalization_service import (
    TextNormalizationService,
    get_text_normalization_service,
)
from app.services.voice_query_service import VoiceQueryService

logger = get_logger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice Assistant"])

_ALLOWED_AUDIO_EXTENSIONS = {".m4a", ".wav"}
_ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/vnd.wave",
    "application/octet-stream",
}


def _error_detail(error: str, message: str) -> dict:
    return {"error": error, "message": message, "details": {}}


def _safe_delete(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        logger.warning("Could not remove temporary audio file: %s", path)


def get_speech_service(request: Request) -> SpeechToTextService:
    """Dependency: resolve the shared SpeechToTextService from app state.

    In production the service is created and its model loaded once during the
    FastAPI lifespan; this fallback only guards against direct unit usage.
    """
    service: SpeechToTextService | None = getattr(request.app.state, "speech_service", None)
    if service is None:
        service = get_speech_to_text_service()
        request.app.state.speech_service = service
    return service


def _validate_audio(filename: str | None, content_type: str | None) -> None:
    """Validate that the uploaded file is a supported audio file."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_detail("INVALID_AUDIO_FILE", "Audio file name is required"),
        )

    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=_error_detail(
                "UNSUPPORTED_AUDIO_FORMAT",
                f"Unsupported audio format '{suffix}'. Only .m4a and .wav are supported.",
            ),
        )

    if content_type and content_type not in _ALLOWED_AUDIO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=_error_detail(
                "UNSUPPORTED_AUDIO_FORMAT",
                f"Unsupported media type '{content_type}'. Only .m4a and .wav are supported.",
            ),
        )


async def _save_upload(audio: UploadFile) -> str:
    """Save the uploaded file to a temporary location and return its path."""
    suffix = Path(audio.filename).suffix.lower() or ".wav"
    fd, temp_path = tempfile.mkstemp(prefix="voice_", suffix=suffix)
    if fd >= 0:
        os.close(fd)

    try:
        with open(temp_path, "wb") as buffer:
            while chunk := await audio.read(1024 * 1024):
                buffer.write(chunk)
        return temp_path
    except Exception as exc:
        _safe_delete(temp_path)
        logger.exception("Failed to save uploaded audio file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error_detail("AUDIO_SAVE_FAILED", "Failed to save the uploaded audio file"),
        ) from exc


@router.post(
    "/transcribe",
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio file",
    description=(
        "Upload a .m4a or .wav audio file and receive its transcription as text. "
        "The file is saved temporarily and deleted after processing."
    ),
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (.m4a or .wav)"),
    current_user_id: str = Depends(get_current_user),
    speech_service: SpeechToTextService = Depends(get_speech_service),
):
    """Transcribe the uploaded audio file and return the recognized text."""
    _validate_audio(audio.filename, audio.content_type)

    if not speech_service.is_loaded:
        raise SpeechToTextModelNotLoadedError(
            "Speech-to-text model is not loaded. Please restart the service."
        )

    temp_path: str | None = None
    try:
        temp_path = await _save_upload(audio)
        text = await asyncio.to_thread(speech_service.transcribe, temp_path)
        return {"text": text}
    finally:
        if temp_path is not None:
            _safe_delete(temp_path)


def get_normalization_service(request: Request) -> TextNormalizationService:
    """Dependency: resolve the shared TextNormalizationService from app state."""
    service: TextNormalizationService | None = getattr(
        request.app.state, "normalization_service", None
    )
    if service is None:
        service = get_text_normalization_service()
        request.app.state.normalization_service = service
    return service


def _validate_normalization_text(text: str) -> None:
    """Validate the transcript length to prevent oversized requests."""
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_error_detail("EMPTY_TEXT", "Text must not be empty"),
        )
    if len(text) > settings.NORMALIZE_MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_error_detail(
                "TEXT_TOO_LONG",
                f"Text exceeds the maximum length of "
                f"{settings.NORMALIZE_MAX_TEXT_LENGTH} characters",
            ),
        )


@router.post(
    "/normalize",
    status_code=status.HTTP_200_OK,
    summary="Normalize a raw transcript into a structured query",
    description=(
        "Accepts a raw speech transcript (Tamil, English, Tanglish, or mixed "
        "Tamil-English) and returns a structured representation with language, "
        "intent, normalized text, and extracted entities. The result is NOT "
        "evaluated against the eligibility engine or RAG in this phase."
    ),
)
async def normalize_text(
    payload: NormalizationRequest,
    current_user_id: str = Depends(get_current_user),
    normalization_service: TextNormalizationService = Depends(get_normalization_service),
) -> NormalizationResponse:
    """Normalize a raw transcript into a structured query (Phase 4)."""
    _validate_normalization_text(payload.text)
    result = await asyncio.to_thread(normalization_service.normalize, payload.text)
    return NormalizationResponse(
        language=result.language,
        intent=result.intent,
        normalized_text=result.normalized_text,
        entities=result.entities,
        confidence=result.confidence,
        source=result.source,
    )


async def _resolve_normalization(
    payload: VoiceRecommendationRequest,
    normalization_service: TextNormalizationService,
) -> NormalizationResponse:
    """Return a structured normalization for the request.

    If the caller supplied a fully-normalized ``normalization`` object it is
    reused as-is. Otherwise the raw ``text`` is normalized through the existing
    Phase 4 service (which reuses Ollama with a heuristic fallback).
    """
    if payload.normalization is not None:
        return payload.normalization

    text = (payload.text or "").strip()
    _validate_normalization_text(text)
    result = await asyncio.to_thread(normalization_service.normalize, text)
    return NormalizationResponse(
        language=result.language,
        intent=result.intent,
        normalized_text=result.normalized_text,
        entities=result.entities,
        confidence=result.confidence,
        source=result.source,
    )


@router.post(
    "/recommend",
    status_code=status.HTTP_200_OK,
    summary="Personalized scheme recommendation from a voice query",
    description=(
        "Accepts either a raw transcript (``text``) or a pre-normalized "
        "structured query (``normalization``) and returns personalized scheme "
        "recommendations for the authenticated citizen. The voice query is "
        "treated as query context only; the verified citizen profile and the "
        "existing eligibility/RAG engine remain authoritative."
    ),
    response_model=VoiceRecommendationResponse,
)
async def recommend_from_voice(
    payload: VoiceRecommendationRequest,
    current_user_id: str = Depends(get_current_user),
    normalization_service: TextNormalizationService = Depends(get_normalization_service),
    db: Session = Depends(get_db),
) -> VoiceRecommendationResponse:
    """Recommend schemes for an authenticated citizen from a voice query."""
    try:
        normalization = await _resolve_normalization(payload, normalization_service)
        service = VoiceQueryService(db)
        return service.recommend(
            citizen_id=current_user_id,
            normalization=normalization,
            limit=payload.limit,
        )
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc
