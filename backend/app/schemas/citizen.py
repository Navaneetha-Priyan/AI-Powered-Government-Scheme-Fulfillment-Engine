"""Pydantic Schemas for Request/Response Validation"""
from pydantic import BaseModel, Field, EmailStr, validator, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum

# Enums
class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class CitizenStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


# Registration Schemas
class CitizenRegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    password: str = Field(
        ..., min_length=8, max_length=255, description="Password"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=255, description="Confirm password"
    )

    # Government Identities
    aadhaar_number: Optional[str] = Field(None, description="Aadhaar number (12 digits)")
    smart_ration_card: Optional[str] = Field(
        None, description="Smart Ration Card number"
    )

    # Personal Information
    gender: Optional[GenderEnum] = Field(
        None, description="Gender"
    )
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")

    # Address
    address_line1: Optional[str] = Field(None, max_length=255, description="Address Line 1")
    address_line2: Optional[str] = Field(None, max_length=255, description="Address Line 2")
    village: Optional[str] = Field(None, max_length=100, description="Village name")
    taluk: Optional[str] = Field(None, max_length=100, description="Taluk name")
    district: str = Field(..., max_length=100, description="District")
    state: str = Field(..., max_length=50, description="State")
    pincode: Optional[str] = Field(None, pattern=r"^\d{6}$", description="Pincode")

    # Preferences
    preferred_language: str = Field(default="en", description="Preferred language")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """Validate phone format"""
        import re
        if not re.match(r"^[6-9]\d{9}$", re.sub(r"[\s\-\(\)]", "", v)):
            raise ValueError("Invalid phone number")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        """Validate passwords match"""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "citizen@example.com",
                "phone": "9876543210",
                "full_name": "John Doe",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "aadhaar_number": "123456789012",
                "district": "Chennai",
                "state": "Tamil Nadu",
            }
        }


# Login Schemas
class CitizenLoginRequest(BaseModel):
    """User login request"""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "citizen@example.com",
                "password": "SecurePass123!",
            }
        }


# Token Schemas
class TokenResponse(BaseModel):
    """Token response"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


# Profile Schemas
class CitizenProfileResponse(BaseModel):
    """User profile response"""

    id: str = Field(..., description="Citizen ID")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    full_name: str = Field(..., description="Full name")

    # Government IDs
    aadhaar_number: Optional[str] = Field(None, description="Aadhaar number")
    smart_ration_card: Optional[str] = Field(None, description="Ration Card number")

    # Personal Details
    gender: Optional[str] = Field(None, description="Gender")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")

    # Address
    address_line1: Optional[str] = Field(None, description="Address Line 1")
    address_line2: Optional[str] = Field(None, description="Address Line 2")
    village: Optional[str] = Field(None, description="Village")
    taluk: Optional[str] = Field(None, description="Taluk")
    district: str = Field(..., description="District")
    state: str = Field(..., description="State")
    pincode: Optional[str] = Field(None, description="Pincode")

    # Status
    email_verified: bool = Field(..., description="Email verification status")
    phone_verified: bool = Field(..., description="Phone verification status")
    account_active: bool = Field(..., description="Account active status")
    status: str = Field(..., description="Account status")

    # Profile
    preferred_language: str = Field(..., description="Preferred language")
    profile_photo_url: Optional[str] = Field(None, description="Profile photo URL")
    last_login: Optional[datetime] = Field(None, description="Last login time")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")

    class Config:
        from_attributes = True


class CitizenUpdateProfileRequest(BaseModel):
    """Update profile request"""

    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[datetime] = None

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    village: Optional[str] = Field(None, max_length=100)
    taluk: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, pattern=r"^\d{6}$")

    # Preferences
    preferred_language: Optional[str] = None
    profile_photo_url: Optional[str] = Field(None, max_length=500)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """Validate phone format"""
        if v is None:
            return v
        import re
        if not re.match(r"^[6-9]\d{9}$", re.sub(r"[\s\-\(\)]", "", v)):
            raise ValueError("Invalid phone number")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe Updated",
                "gender": "male",
                "district": "Chennai",
                "state": "Tamil Nadu",
            }
        }


# Password Schemas
class ChangePasswordRequest(BaseModel):
    """Change password request"""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        """Validate passwords match"""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "old_password": "OldPass123!",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            }
        }


# Verification Schemas
class VerifyTokenRequest(BaseModel):
    """Verify token request"""

    token: str = Field(..., description="Token to verify")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


class VerifyTokenResponse(BaseModel):
    """Verify token response"""

    valid: bool = Field(..., description="Token validity")
    citizen_id: Optional[str] = Field(None, description="Citizen ID")
    email: Optional[str] = Field(None, description="Email")
    expires_at: Optional[datetime] = Field(None, description="Token expiry time")
    message: str = Field(..., description="Message")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "citizen_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "citizen@example.com",
                "expires_at": "2024-01-15T10:30:00",
                "message": "Token is valid",
            }
        }


# Response Schemas
class SuccessResponse(BaseModel):
    """Generic success response"""

    success: bool = Field(default=True, description="Success flag")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Response data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None,
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response"""

    success: bool = Field(default=False, description="Success flag")
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": {"field": "error_message"},
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Timestamp")
    database: str = Field(..., description="Database status")
    environment: str = Field(..., description="Environment")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "timestamp": "2024-01-15T10:30:00",
                "database": "connected",
                "environment": "development",
            }
        }
