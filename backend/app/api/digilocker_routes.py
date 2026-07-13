"""DigiLocker API Routes (Module 2)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.citizen import SuccessResponse
from app.schemas.citizen_profile import DigiLockerSyncRequest
from app.services.digilocker_service import DigiLockerService
from app.exceptions.exceptions import AppException
from app.api.dependencies import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/digilocker", tags=["DigiLocker"])


@router.post(
    "/sync",
    response_model=SuccessResponse,
    status_code=200,
    summary="Sync DigiLocker",
    description="Trigger DigiLocker sync to fetch citizen profile and government documents",
)
async def sync_digilocker(
    sync_request: DigiLockerSyncRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync DigiLocker for the authenticated citizen"""
    try:
        service = DigiLockerService(db)
        result = service.sync(current_user_id, force_refresh=sync_request.force_refresh)
        return SuccessResponse(
            success=True,
            message=result["message"],
            data=result,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"DigiLocker sync error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "DigiLocker sync failed"},
        )


@router.get(
    "/status",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get DigiLocker status",
    description="Get the current DigiLocker sync status and document counts",
)
async def get_digilocker_status(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get DigiLocker sync status"""
    try:
        service = DigiLockerService(db)
        status = service.get_status(current_user_id)
        return SuccessResponse(
            success=True,
            message="DigiLocker status retrieved successfully",
            data={
                **status,
                "last_sync_at": status["last_sync_at"].isoformat() if status.get("last_sync_at") else None,
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"DigiLocker status error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve DigiLocker status"},
        )


@router.get(
    "/documents",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get DigiLocker documents",
    description="Get all government documents stored in DigiLocker for the authenticated citizen",
)
async def get_digilocker_documents(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all DigiLocker documents"""
    try:
        service = DigiLockerService(db)
        docs = service.get_documents(current_user_id)
        return SuccessResponse(
            success=True,
            message="DigiLocker documents retrieved successfully",
            data={
                "citizen_id": current_user_id,
                "total_documents": len(docs),
                "documents": [_doc_to_dict(d) for d in docs],
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"DigiLocker documents error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve documents"},
        )


@router.get(
    "/documents/{document_id}",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get specific document",
    description="Get a specific government document by ID",
)
async def get_document(
    document_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific document by ID"""
    try:
        service = DigiLockerService(db)
        doc = service.get_document_by_id(current_user_id, document_id)
        return SuccessResponse(
            success=True,
            message="Document retrieved successfully",
            data=_doc_to_dict(doc),
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve document"},
        )


def _doc_to_dict(doc) -> dict:
    if not doc:
        return None
    return {
        "id": doc.id,
        "citizen_id": doc.citizen_id,
        "document_type": doc.document_type,
        "document_number": doc.document_number,
        "document_name": doc.document_name,
        "issue_date": doc.issue_date.isoformat() if doc.issue_date else None,
        "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
        "verification_status": doc.verification_status,
        "verified_by": doc.verified_by,
        "verified_at": doc.verified_at.isoformat() if doc.verified_at else None,
        "download_url": doc.download_url,
        "doc_metadata": doc.doc_metadata,
        "is_active": doc.is_active,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
