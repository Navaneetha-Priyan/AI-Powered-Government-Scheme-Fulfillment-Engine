"""Citizen Profile API Routes (Module 2)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.citizen import SuccessResponse
from app.schemas.citizen_profile import CitizenProfileUpdateRequest
from app.services.citizen_profile_service import CitizenProfileService
from app.services.digilocker_service import DigiLockerService
from app.exceptions.exceptions import AppException
from app.api.dependencies import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/citizen", tags=["Citizen Profile"])


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
