"""Citizen Profile API Routes (Module 2)"""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.citizen import SuccessResponse
from app.schemas.citizen_profile import CitizenProfileUpdateRequest
from app.services.citizen_profile_service import CitizenProfileService
from app.services.digilocker_service import DigiLockerService
from app.services.document_processing_service import DocumentProcessingService
from app.exceptions.exceptions import (
    AppException,
    DocumentOcrError,
    DocumentProcessingError,
    UnsupportedDocumentTypeError,
)
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/citizen", tags=["Citizen Profile"])


async def _save_upload(file: UploadFile, citizen_id: str, folder: str) -> str:
    """Save a citizen upload and return a relative file path."""
    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": f"File must be {settings.MAX_UPLOAD_SIZE_MB} MB or smaller",
            },
        )

    original_name = Path(file.filename or "upload.bin").name
    safe_name = f"{uuid4()}{Path(original_name).suffix.lower()}"
    upload_dir = Path(settings.UPLOAD_DIR) / folder / citizen_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)
    return str(file_path).replace("\\", "/")


@router.get(
    "/profile",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get extended citizen profile",
    description="Retrieve the extended DigiLocker-synced profile for the authenticated citizen",
)
async def get_profile(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get extended citizen profile"""
    try:
        service = CitizenProfileService(db)
        profile = service.get_profile(current_user_id)
        return SuccessResponse(
            success=True,
            message="Profile retrieved successfully",
            data=_profile_to_dict(profile),
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve profile"},
        )


@router.get(
    "/profile/details",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get full citizen profile details",
    description="Retrieve combined auth profile and extended profile details",
)
async def get_profile_details(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full citizen profile details"""
    try:
        service = CitizenProfileService(db)
        result = service.get_full_profile(current_user_id)
        citizen = result["citizen"]
        profile = result["profile"]

        data = {
            "citizen_id": citizen.id,
            "full_name": citizen.full_name,
            "email": citizen.email,
            "phone": citizen.phone,
            "gender": citizen.gender,
            "date_of_birth": citizen.date_of_birth.isoformat() if citizen.date_of_birth else None,
            "aadhaar_number": citizen.aadhaar_number,
            "smart_ration_card": citizen.smart_ration_card,
            "address_line1": citizen.address_line1,
            "address_line2": citizen.address_line2,
            "village": citizen.village,
            "taluk": citizen.taluk,
            "district": citizen.district,
            "state": citizen.state,
            "pincode": citizen.pincode,
            "profile_photo_url": citizen.profile_photo_url,
            "extended_profile": _profile_to_dict(profile) if profile else None,
        }
        return SuccessResponse(
            success=True,
            message="Profile details retrieved successfully",
            data=data,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get profile details error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve profile details"},
        )


@router.put(
    "/profile",
    response_model=SuccessResponse,
    status_code=200,
    summary="Update extended citizen profile",
    description="Update the extended profile fields for the authenticated citizen",
)
async def update_profile(
    update_data: CitizenProfileUpdateRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update extended citizen profile"""
    try:
        service = CitizenProfileService(db)
        profile = service.update_profile(current_user_id, update_data)
        return SuccessResponse(
            success=True,
            message="Profile updated successfully",
            data=_profile_to_dict(profile),
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to update profile"},
        )


@router.get(
    "/dashboard",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get citizen dashboard",
    description="Get complete citizen dashboard with profile, documents, and land records",
)
async def get_dashboard(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get citizen dashboard"""
    try:
        service = CitizenProfileService(db)
        dashboard = service.get_dashboard(current_user_id)

        # Serialize nested objects
        dashboard["extended_profile"] = _profile_to_dict(dashboard.get("extended_profile"))
        dashboard["land_records"] = [_land_to_dict(r) for r in dashboard.get("land_records", [])]
        if dashboard.get("date_of_birth"):
            dashboard["date_of_birth"] = dashboard["date_of_birth"].isoformat()
        if dashboard.get("last_login"):
            dashboard["last_login"] = dashboard["last_login"].isoformat()
        if dashboard.get("last_synced_at"):
            dashboard["last_synced_at"] = dashboard["last_synced_at"].isoformat()

        return SuccessResponse(
            success=True,
            message="Dashboard retrieved successfully",
            data=dashboard,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get dashboard error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve dashboard"},
        )


@router.get(
    "/income",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get income details",
    description="Get income and economic classification details for the authenticated citizen",
)
async def get_income(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get income details"""
    try:
        service = CitizenProfileService(db)
        data = service.get_income_details(current_user_id)
        return SuccessResponse(
            success=True,
            message="Income details retrieved successfully",
            data=data,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get income error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve income details"},
        )


@router.get(
    "/caste",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get caste and community details",
    description="Get caste, community, and religion details for the authenticated citizen",
)
async def get_caste(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get caste and community details"""
    try:
        service = CitizenProfileService(db)
        data = service.get_caste_details(current_user_id)
        return SuccessResponse(
            success=True,
            message="Caste details retrieved successfully",
            data=data,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get caste error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve caste details"},
        )


@router.get(
    "/land-records",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get land records",
    description="Get all land ownership records for the authenticated citizen",
)
async def get_land_records(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get land records"""
    try:
        service = CitizenProfileService(db)
        result = service.get_land_records(current_user_id)
        result["land_records"] = [_land_to_dict(r) for r in result.get("land_records", [])]
        return SuccessResponse(
            success=True,
            message="Land records retrieved successfully",
            data=result,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get land records error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve land records"},
        )


@router.post(
    "/land-records/upload",
    response_model=SuccessResponse,
    status_code=201,
    summary="Upload land record",
    description="Add a citizen-submitted land record with supporting document",
)
async def upload_land_record(
    survey_number: str = Form(...),
    village: str = Form(...),
    district: str = Form(...),
    land_type: str = Form(...),
    land_area: float = Form(...),
    ownership_type: str = Form(...),
    file: UploadFile = File(...),
    taluk: str | None = Form(None),
    state: str | None = Form(None),
    patta_number: str | None = Form(None),
    document_type: str = Form("land_record"),
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a land record and create a pending land-record document.

    ``document_type`` is supplied explicitly by the client (defaults to
    ``land_record``). When the uploaded file is a real PDF/image, the new
    document processing pipeline (PDF text extraction or OCR → field extraction
    → existing mapper → existing enrichment) attempts to read the file. The
    manually supplied land fields remain the source of truth and are preserved
    even when automatic extraction fails (backward compatible).
    """
    try:
        saved_path = await _save_upload(file, current_user_id, "land-records")
        service = CitizenProfileService(db)
        record = service.add_land_record(
            current_user_id,
            {
                "survey_number": survey_number,
                "land_area": land_area,
                "land_area_unit": "acres",
                "land_type": land_type,
                "village": village,
                "taluk": taluk,
                "district": district,
                "state": state,
                "ownership_type": ownership_type,
                "patta_number": patta_number,
            },
        )

        digilocker_service = DigiLockerService(db)
        doc = digilocker_service.add_uploaded_document(
            citizen_id=current_user_id,
            document_type="land_record",
            document_name=f"Land Record - {survey_number}",
            document_number=patta_number or survey_number,
            download_url=saved_path,
            metadata=f"Uploaded by citizen on {datetime.utcnow().isoformat()}",
        )

        # Route the created GovernmentDocument through the canonical
        # document → profile enrichment pipeline. The raw upload has no
        # OCR-derived structured metadata yet, so this is a no-op unless the
        # document carries structured metadata. The manually supplied land
        # fields remain the source of truth for this upload (backward
        # compatible). No duplicate land record is created because the
        # enrichment service dedupes on citizen_id + survey_number.
        digilocker_service.enrich_document(doc)

        # Real-document processing: attempt PDF text extraction or OCR, then
        # feed the extracted fields through the existing Step 3 mapper and
        # Step 4 enrichment. Failures are non-fatal — the manual record above
        # remains the source of truth and the upload still succeeds.
        processing_status = "not_processed"
        processing_result = None
        processing_error = None
        try:
            processing_service = DocumentProcessingService(db)
            processing_result = processing_service.process_file(
                file_path=saved_path,
                document_type=document_type,
                citizen_id=current_user_id,
                document_id=doc.id,
            )
            processing_status = "processed"
        except (DocumentProcessingError, DocumentOcrError) as e:
            logger.warning(
                "Document processing failed for upload %s: %s",
                saved_path,
                e.message,
            )
            processing_status = "failed"
            processing_error = "Document uploaded, but we could not read all details automatically."
        except UnsupportedDocumentTypeError as e:
            logger.warning(
                "Unsupported document type for upload %s: %s",
                saved_path,
                e.message,
            )
            processing_status = "failed"
            processing_error = "Document uploaded, but its type is not supported yet."

        return SuccessResponse(
            success=True,
            message="Land record uploaded successfully",
            data={
                "land_record": _land_to_dict(record),
                "document": _doc_to_dict(doc),
                "processing_status": processing_status,
                "processing": (
                    processing_result.model_dump(mode="json")
                    if processing_result
                    else None
                ),
                "processing_error": processing_error,
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload land record error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to upload land record"},
        )


@router.post(
    "/documents/upload",
    response_model=SuccessResponse,
    status_code=201,
    summary="Upload a government document",
    description=(
        "Upload a citizen-submitted government document (Aadhaar, Income "
        "Certificate, Caste Certificate, Ration Card, Residence Certificate, "
        "Farmer ID, Disability Certificate, or Land Record). The backend runs "
        "the real document processing pipeline (PDF text extraction or OCR → "
        "field extraction → mapper → profile enrichment) and returns the "
        "processing result."
    ),
)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a generic government document and process it through the real
    document pipeline.

    The citizen identity comes from the authenticated session. Only the
    document type and file are required — no manual profile fields are needed.
    The backend's ``DocumentProcessingService`` reads the file (PDF text or
    OCR), extracts normalized fields, maps them to canonical domain fields,
    and enriches the citizen profile via ``ProfileEnrichmentService``.
    """
    try:
        # Validate document type against the canonical enum.
        try:
            from app.schemas.citizen_profile import DocumentTypeEnum

            resolved_type = DocumentTypeEnum(document_type.strip().lower())
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "UNSUPPORTED_DOCUMENT_TYPE",
                    "message": f"Unsupported document type: {document_type}",
                },
            )

        saved_path = await _save_upload(file, current_user_id, "documents")
        digilocker_service = DigiLockerService(db)

        # Create the GovernmentDocument row so it appears in My Documents.
        doc = digilocker_service.add_uploaded_document(
            citizen_id=current_user_id,
            document_type=resolved_type.value,
            document_name=f"{resolved_type.value.replace('_', ' ').title()}",
            document_number=None,
            download_url=saved_path,
            metadata=f"Uploaded by citizen on {datetime.utcnow().isoformat()}",
        )

        # Run the real document processing pipeline.
        processing_status = "not_processed"
        processing_result = None
        processing_error = None
        try:
            processing_service = DocumentProcessingService(db)
            processing_result = processing_service.process_file(
                file_path=saved_path,
                document_type=resolved_type.value,
                citizen_id=current_user_id,
                document_id=doc.id,
            )
            processing_status = "processed"
        except (DocumentProcessingError, DocumentOcrError) as e:
            logger.warning(
                "Document processing failed for upload %s: %s",
                saved_path,
                e.message,
            )
            processing_status = "failed"
            processing_error = "Document uploaded, but we could not read all details automatically."
        except UnsupportedDocumentTypeError as e:
            logger.warning(
                "Unsupported document type for upload %s: %s",
                saved_path,
                e.message,
            )
            processing_status = "failed"
            processing_error = "Document uploaded, but its type is not supported yet."

        return SuccessResponse(
            success=True,
            message=(
                "Document processed successfully"
                if processing_status == "processed"
                else "Document uploaded successfully"
            ),
            data={
                "document": _doc_to_dict(doc),
                "processing_status": processing_status,
                "processing": (
                    processing_result.model_dump(mode="json")
                    if processing_result
                    else None
                ),
                "processing_error": processing_error,
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload document error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to upload document"},
        )


@router.get(
    "/documents",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get citizen documents",
    description="Get all government documents linked via DigiLocker for the authenticated citizen",
)
async def get_documents(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get citizen documents"""
    try:
        digilocker_service = DigiLockerService(db)
        docs = digilocker_service.get_documents(current_user_id)
        return SuccessResponse(
            success=True,
            message="Documents retrieved successfully",
            data={
                "citizen_id": current_user_id,
                "total_documents": len(docs),
                "documents": [_doc_to_dict(d) for d in docs],
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get documents error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": "Failed to retrieve documents"},
        )


# ─── Serialization helpers ─────────────────────────────────────────────────────

def _profile_to_dict(profile) -> dict:
    if not profile:
        return None
    return {
        "id": profile.id,
        "citizen_id": profile.citizen_id,
        "father_name": profile.father_name,
        "mother_name": profile.mother_name,
        "occupation": profile.occupation,
        "marital_status": profile.marital_status,
        "blood_group": profile.blood_group,
        "nationality": profile.nationality,
        "annual_income": profile.annual_income,
        "income_category": profile.income_category,
        "caste": profile.caste,
        "community": profile.community,
        "sub_caste": profile.sub_caste,
        "religion": profile.religion,
        "is_disabled": profile.is_disabled,
        "disability_type": profile.disability_type,
        "disability_percentage": profile.disability_percentage,
        "is_farmer": profile.is_farmer,
        "farmer_id": profile.farmer_id,
        "education_level": profile.education_level,
        "education_institution": profile.education_institution,
        "family_member_count": profile.family_member_count,
        "family_details": profile.family_details,
        "profile_completion_percentage": profile.profile_completion_percentage,
        "sync_status": profile.sync_status,
        "last_synced_at": profile.last_synced_at.isoformat() if profile.last_synced_at else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _land_to_dict(record) -> dict:
    if not record:
        return None
    return {
        "id": record.id,
        "citizen_id": record.citizen_id,
        "survey_number": record.survey_number,
        "land_area": record.land_area,
        "land_area_unit": record.land_area_unit,
        "land_type": record.land_type,
        "village": record.village,
        "taluk": record.taluk,
        "district": record.district,
        "state": record.state,
        "ownership_type": record.ownership_type,
        "patta_number": record.patta_number,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


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
