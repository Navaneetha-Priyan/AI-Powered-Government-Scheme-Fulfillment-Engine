"""Pydantic Schemas for Citizen Profile & DigiLocker (Module 2)"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Any, Dict
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class IncomeCategoryEnum(str, Enum):
    BPL = "bpl"
    APL = "apl"
    EWS = "ews"
    LIG = "lig"
    MIG = "mig"
    HIG = "hig"


class MaritalStatusEnum(str, Enum):
    SINGLE = "single"
    MARRIED = "married"
    WIDOWED = "widowed"
    DIVORCED = "divorced"
    SEPARATED = "separated"


class LandTypeEnum(str, Enum):
    AGRICULTURAL = "agricultural"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    FOREST = "forest"
    WASTELAND = "wasteland"


class ProfileSyncStatusEnum(str, Enum):
    NOT_SYNCED = "not_synced"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"
    SYNC_PENDING = "sync_pending"


class DocumentTypeEnum(str, Enum):
    AADHAAR = "aadhaar"
    SMART_RATION_CARD = "smart_ration_card"
    INCOME_CERTIFICATE = "income_certificate"
    COMMUNITY_CERTIFICATE = "community_certificate"
    RESIDENCE_CERTIFICATE = "residence_certificate"
    LAND_RECORD = "land_record"
    DISABILITY_CERTIFICATE = "disability_certificate"
    FARMER_ID = "farmer_id"
    BIRTH_CERTIFICATE = "birth_certificate"
    CASTE_CERTIFICATE = "caste_certificate"


class DocumentVerificationStatusEnum(str, Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    EXPIRED = "expired"
    REJECTED = "rejected"


# ─── Citizen Profile Schemas ───────────────────────────────────────────────────

class CitizenProfileUpdateRequest(BaseModel):
    """Update extended citizen profile"""

    father_name: Optional[str] = Field(None, max_length=100)
    mother_name: Optional[str] = Field(None, max_length=100)
    occupation: Optional[str] = Field(None, max_length=100)
    marital_status: Optional[MaritalStatusEnum] = None
    blood_group: Optional[str] = Field(None, max_length=5)
    nationality: Optional[str] = Field(None, max_length=50)
    annual_income: Optional[float] = Field(None, ge=0)
    income_category: Optional[IncomeCategoryEnum] = None
    caste: Optional[str] = Field(None, max_length=100)
    community: Optional[str] = Field(None, max_length=100)
    sub_caste: Optional[str] = Field(None, max_length=100)
    religion: Optional[str] = Field(None, max_length=50)
    is_disabled: Optional[bool] = None
    disability_type: Optional[str] = Field(None, max_length=100)
    disability_percentage: Optional[int] = Field(None, ge=0, le=100)
    is_farmer: Optional[bool] = None
    farmer_id: Optional[str] = Field(None, max_length=50)
    education_level: Optional[str] = Field(None, max_length=100)
    education_institution: Optional[str] = Field(None, max_length=200)
    family_member_count: Optional[int] = Field(None, ge=1)

    class Config:
        json_schema_extra = {
            "example": {
                "father_name": "Ravi Kumar",
                "mother_name": "Lakshmi Devi",
                "occupation": "Farmer",
                "marital_status": "married",
                "blood_group": "O+",
                "annual_income": 85000.0,
                "income_category": "bpl",
                "caste": "Vanniyar",
                "community": "MBC",
                "religion": "Hindu",
                "is_farmer": True,
            }
        }


class LandRecordResponse(BaseModel):
    """Land record response"""

    id: str
    citizen_id: str
    survey_number: Optional[str]
    land_area: Optional[float]
    land_area_unit: Optional[str]
    land_type: Optional[str]
    village: Optional[str]
    taluk: Optional[str]
    district: Optional[str]
    state: Optional[str]
    ownership_type: Optional[str]
    patta_number: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CitizenProfileResponse(BaseModel):
    """Full extended citizen profile response"""

    id: str
    citizen_id: str

    # Personal
    father_name: Optional[str]
    mother_name: Optional[str]
    occupation: Optional[str]
    marital_status: Optional[str]
    blood_group: Optional[str]
    nationality: Optional[str]

    # Economic
    annual_income: Optional[float]
    income_category: Optional[str]

    # Social
    caste: Optional[str]
    community: Optional[str]
    sub_caste: Optional[str]
    religion: Optional[str]

    # Special status
    is_disabled: bool
    disability_type: Optional[str]
    disability_percentage: Optional[int]
    is_farmer: bool
    farmer_id: Optional[str]

    # Education
    education_level: Optional[str]
    education_institution: Optional[str]

    # Family
    family_member_count: Optional[int]
    family_details: Optional[str]

    # Completion
    profile_completion_percentage: int
    sync_status: str
    last_synced_at: Optional[datetime]

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CitizenDashboardResponse(BaseModel):
    """Combined dashboard — auth profile + extended profile + documents"""

    # Core identity (from citizens table)
    citizen_id: str
    full_name: str
    email: str
    phone: str
    gender: Optional[str]
    date_of_birth: Optional[datetime]
    profile_photo_url: Optional[str]
    aadhaar_number: Optional[str]
    smart_ration_card: Optional[str]

    # Address
    address_line1: Optional[str]
    address_line2: Optional[str]
    village: Optional[str]
    taluk: Optional[str]
    district: str
    state: str
    pincode: Optional[str]

    # Extended profile
    extended_profile: Optional[CitizenProfileResponse]

    # Land records summary
    land_records: List[LandRecordResponse]
    total_land_area: float

    # Document summary
    total_documents: int
    verified_documents: int
    digilocker_synced: bool
    last_synced_at: Optional[datetime]

    # Account
    account_active: bool
    last_login: Optional[datetime]
    profile_completion_percentage: int

    class Config:
        from_attributes = True


# ─── DigiLocker Schemas ────────────────────────────────────────────────────────

class DigiLockerSyncRequest(BaseModel):
    """Request to trigger DigiLocker sync"""

    force_refresh: bool = Field(
        default=False,
        description="Force re-sync even if already synced",
    )

    class Config:
        json_schema_extra = {"example": {"force_refresh": False}}


class GovernmentDocumentResponse(BaseModel):
    """Government document response"""

    id: str
    citizen_id: str
    document_type: str
    document_number: Optional[str]
    document_name: str
    issue_date: Optional[datetime]
    expiry_date: Optional[datetime]
    verification_status: str
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    download_url: Optional[str]
    doc_metadata: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DigiLockerStatusResponse(BaseModel):
    """DigiLocker sync status response"""

    citizen_id: str
    digilocker_id: Optional[str]
    is_active: bool
    last_sync_at: Optional[datetime]
    sync_count: str
    total_documents: int
    verified_documents: int
    pending_documents: int
    expired_documents: int

    class Config:
        from_attributes = True


class DigiLockerSyncResponse(BaseModel):
    """Response after DigiLocker sync"""

    citizen_id: str
    sync_status: str
    documents_synced: int
    profile_updated: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "citizen_id": "uuid-here",
                "sync_status": "synced",
                "documents_synced": 8,
                "profile_updated": True,
                "message": "DigiLocker sync completed successfully",
            }
        }
