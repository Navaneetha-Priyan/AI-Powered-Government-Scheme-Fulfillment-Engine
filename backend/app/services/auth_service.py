"""Service Layer - Business Logic for Authentication"""
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.repositories.citizen_repository import CitizenRepository, LoginAuditRepository
from app.schemas.citizen import (
    CitizenRegisterRequest,
    CitizenLoginRequest,
    CitizenProfileResponse,
    CitizenUpdateProfileRequest,
    ChangePasswordRequest,
    TokenResponse,
)
from app.models.citizen import Citizen, CitizenStatus
from app.core.security import hash_password, verify_password, validate_password_strength
from app.core.jwt import create_access_token, create_refresh_token, verify_token
from app.validators.validators import (
    AadhaarValidator,
    RationCardValidator,
    EmailValidator,
    PhoneValidator,
    NameValidator,
    PincodeValidator,
)
from app.services.india_location_service import is_valid_state_district_pair
from app.exceptions.exceptions import (
    ValidationError,
    AuthenticationError,
    NotFoundError,
    ConflictError,
    DuplicateEmailError,
    DuplicatePhoneError,
    DuplicateAadhaarError,
    DuplicateRationCardError,
    InvalidCredentialsError,
    AccountDisabledError,
    WeakPasswordError,
)
from app.core.config import settings
from app.core.logging import get_auth_logger, get_audit_logger, get_logger

auth_logger = get_auth_logger()
audit_logger = get_audit_logger()
logger = get_logger(__name__)


class AuthenticationService:
    """Authentication and Authorization Service"""

    def __init__(self, db: Session):
        self.db = db
        self.citizen_repo = CitizenRepository(db)
        self.audit_repo = LoginAuditRepository(db)

    def register(
        self, register_data: CitizenRegisterRequest
    ) -> Tuple[Citizen, TokenResponse]:
        """
        Register a new citizen
        Returns: (citizen_object, token_response)
        """
        # Validate email format
        is_valid, error_msg = EmailValidator.validate(register_data.email)
        if not is_valid:
            raise ValidationError(error_msg, details={"field": "email"})

        # Check email uniqueness
        if self.citizen_repo.email_exists(register_data.email):
            raise DuplicateEmailError(register_data.email)

        # Validate phone format
        is_valid, error_msg = PhoneValidator.validate(register_data.phone)
        if not is_valid:
            raise ValidationError(error_msg, details={"field": "phone"})

        # Check phone uniqueness
        if self.citizen_repo.phone_exists(register_data.phone):
            raise DuplicatePhoneError(register_data.phone)

        # Validate name
        is_valid, error_msg = NameValidator.validate(register_data.full_name)
        if not is_valid:
            raise ValidationError(error_msg, details={"field": "full_name"})

        # Validate password strength
        is_valid, error_msg = validate_password_strength(register_data.password)
        if not is_valid:
            raise WeakPasswordError(error_msg)

        # Validate Aadhaar if provided
        if register_data.aadhaar_number:
            is_valid, error_msg = AadhaarValidator.validate(
                register_data.aadhaar_number
            )
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "aadhaar_number"})

            # Check Aadhaar uniqueness
            if self.citizen_repo.aadhaar_exists(register_data.aadhaar_number):
                raise DuplicateAadhaarError(register_data.aadhaar_number)

        # Validate Ration Card if provided
        if register_data.smart_ration_card:
            is_valid, error_msg = RationCardValidator.validate(
                register_data.smart_ration_card
            )
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "smart_ration_card"})

            # Check Ration Card uniqueness
            if self.citizen_repo.ration_card_exists(
                register_data.smart_ration_card
            ):
                raise DuplicateRationCardError(register_data.smart_ration_card)

        # Validate pincode if provided
        if register_data.pincode:
            is_valid, error_msg = PincodeValidator.validate(register_data.pincode)
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "pincode"})

        # Validate state and district pairing
        is_valid, error_msg = is_valid_state_district_pair(
            register_data.state,
            register_data.district,
        )
        if not is_valid:
            raise ValidationError(error_msg, details={"field": "district"})

        # Create citizen
        citizen_data = {
            "email": register_data.email,
            "phone": register_data.phone,
            "full_name": register_data.full_name,
            "password_hash": hash_password(register_data.password),
            "aadhaar_number": register_data.aadhaar_number,
            "smart_ration_card": register_data.smart_ration_card,
            "gender": register_data.gender,
            "date_of_birth": register_data.date_of_birth,
            "address_line1": register_data.address_line1,
            "address_line2": register_data.address_line2,
            "village": register_data.village,
            "taluk": register_data.taluk,
            "district": register_data.district,
            "state": register_data.state,
            "pincode": register_data.pincode,
            "preferred_language": register_data.preferred_language,
            "status": CitizenStatus.ACTIVE,
            "email_verified": False,
            "phone_verified": False,
            "account_active": True,
        }

        citizen = self.citizen_repo.create(citizen_data)

        # Create tokens
        token_response = self._create_tokens(citizen)

        # Log registration
        auth_logger.info(
            f"Citizen registered successfully: {citizen.id} ({citizen.email})"
        )

        return citizen, token_response

    def login(
        self, login_data: CitizenLoginRequest, ip_address: str = None
    ) -> TokenResponse:
        """
        Login citizen with email and password
        Returns: token_response
        """
        # Validate email format
        is_valid, error_msg = EmailValidator.validate(login_data.email)
        if not is_valid:
            raise InvalidCredentialsError()

        # Get citizen by email
        citizen = self.citizen_repo.get_by_email(login_data.email)
        if not citizen:
            # Log failed login attempt
            self._log_failed_login(
                citizen_id="unknown",
                failure_reason="Invalid email",
                ip_address=ip_address,
            )
            raise InvalidCredentialsError()

        # Check if account is locked
        if citizen.account_locked:
            raise AuthenticationError("Account is locked due to multiple failed attempts")

        # Check if account is active
        if not citizen.can_login():
            raise AccountDisabledError()

        # Verify password
        if not verify_password(login_data.password, citizen.password_hash):
            # Increment failed login attempts
            citizen.increment_failed_login()
            self.db.commit()

            # Log failed login attempt
            self._log_failed_login(
                citizen_id=citizen.id,
                failure_reason="Invalid password",
                ip_address=ip_address,
            )

            raise InvalidCredentialsError()

        # Reset failed login attempts
        citizen.reset_failed_login()
        citizen.update_last_login(ip_address)
        self.db.commit()

        # Create tokens
        token_response = self._create_tokens(citizen)

        # Log successful login
        self._log_successful_login(citizen_id=citizen.id, ip_address=ip_address)
        auth_logger.info(f"Citizen logged in successfully: {citizen.id} ({citizen.email})")

        return token_response

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        # Verify refresh token
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        # Get citizen
        citizen_id = payload.get("sub")
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen or not citizen.can_login():
            raise AuthenticationError("Invalid refresh token")

        # Create new tokens
        token_response = self._create_tokens(citizen)
        auth_logger.info(f"Token refreshed for citizen: {citizen_id}")

        return token_response

    def get_profile(self, citizen_id: str) -> CitizenProfileResponse:
        """Get citizen profile"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        return CitizenProfileResponse.model_validate(citizen)

    def update_profile(
        self, citizen_id: str, update_data: CitizenUpdateProfileRequest
    ) -> CitizenProfileResponse:
        """Update citizen profile"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        # Validate phone if provided
        if update_data.phone and update_data.phone != citizen.phone:
            is_valid, error_msg = PhoneValidator.validate(update_data.phone)
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "phone"})

            # Check phone uniqueness
            if self.citizen_repo.phone_exists(update_data.phone, exclude_id=citizen_id):
                raise DuplicatePhoneError(update_data.phone)

        # Validate state/district combination when either field is updated.
        if update_data.state or update_data.district:
            state = update_data.state or citizen.state
            district = update_data.district or citizen.district
            is_valid, error_msg = is_valid_state_district_pair(state, district)
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "district"})

        # Validate name if provided
        if update_data.full_name:
            is_valid, error_msg = NameValidator.validate(update_data.full_name)
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "full_name"})

        # Validate pincode if provided
        if update_data.pincode:
            is_valid, error_msg = PincodeValidator.validate(update_data.pincode)
            if not is_valid:
                raise ValidationError(error_msg, details={"field": "pincode"})

        # Update citizen
        update_dict = update_data.model_dump(exclude_unset=True)
        updated_citizen = self.citizen_repo.update(citizen_id, update_dict)

        audit_logger.info(f"Citizen profile updated: {citizen_id}")
        return CitizenProfileResponse.model_validate(updated_citizen)

    def change_password(
        self, citizen_id: str, password_data: ChangePasswordRequest
    ) -> bool:
        """Change password"""
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise NotFoundError("Citizen not found", resource="citizen")

        # Verify old password
        if not verify_password(password_data.old_password, citizen.password_hash):
            raise AuthenticationError("Invalid current password")

        # Validate new password strength
        is_valid, error_msg = validate_password_strength(password_data.new_password)
        if not is_valid:
            raise WeakPasswordError(error_msg)

        # Check if new password is same as old password
        if verify_password(password_data.new_password, citizen.password_hash):
            raise ValidationError(
                "New password must be different from old password",
                details={"field": "new_password"},
            )

        # Update password
        citizen.password_hash = hash_password(password_data.new_password)
        self.db.commit()

        auth_logger.info(f"Password changed for citizen: {citizen_id}")
        return True

    def logout(self, citizen_id: str) -> bool:
        """Logout citizen (mainly for audit logging)"""
        audit_logger.info(f"Citizen logged out: {citizen_id}")
        return True

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify token validity"""
        payload = verify_token(token)
        if not payload:
            raise AuthenticationError("Invalid token")

        citizen_id = payload.get("sub")
        citizen = self.citizen_repo.get_by_id(citizen_id)
        if not citizen:
            raise AuthenticationError("Invalid token")

        return {
            "valid": True,
            "citizen_id": citizen_id,
            "email": citizen.email,
            "expires_at": datetime.fromtimestamp(payload.get("exp")),
        }

    def _create_tokens(self, citizen: Citizen) -> TokenResponse:
        """Create access and refresh tokens"""
        token_data = {"sub": citizen.id, "email": citizen.email, "role": "citizen"}

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def _log_successful_login(
        self, citizen_id: str, ip_address: str = None
    ) -> None:
        """Log successful login"""
        try:
            self.audit_repo.create(
                {
                    "citizen_id": citizen_id,
                    "login_type": "password",
                    "success": True,
                    "ip_address": ip_address,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log successful login: {str(e)}")

    def _log_failed_login(
        self, citizen_id: str, failure_reason: str, ip_address: str = None
    ) -> None:
        """Log failed login"""
        try:
            self.audit_repo.create(
                {
                    "citizen_id": citizen_id,
                    "login_type": "password",
                    "success": False,
                    "failure_reason": failure_reason,
                    "ip_address": ip_address,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log failed login: {str(e)}")
