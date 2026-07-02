"""SQLAlchemy Models for Citizen Registration & Authentication"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    Index,
    Enum,
    CHAR,
    func,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from datetime import datetime
from uuid import uuid4
import enum

from app.database.connection import Base


class CitizenStatus(str, enum.Enum):
    """Citizen account status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class Gender(str, enum.Enum):
    """Gender enum"""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Citizen(Base):
    """Citizen Model - Core identity table"""

    __tablename__ = "citizens"

    # Primary Key
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))

    # Authentication
    email = Column(String(254), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Personal Information
    full_name = Column(String(100), nullable=False)
    gender = Column(Enum(Gender, values_callable=lambda x: [e.value for e in x]), nullable=True, default=Gender.PREFER_NOT_TO_SAY)
    date_of_birth = Column(DateTime, nullable=True)

    # Government Identities (Unique)
    aadhaar_number = Column(String(12), unique=True, nullable=True, index=True)
    smart_ration_card = Column(String(20), unique=True, nullable=True, index=True)

    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    village = Column(String(100), nullable=True)
    taluk = Column(String(100), nullable=True)
    district = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    pincode = Column(String(6), nullable=True)

    # Profile Information
    preferred_language = Column(String(20), default="en")
    profile_photo_url = Column(String(500), nullable=True)

    # Verification Status
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    phone_verified = Column(Boolean, default=False)
    phone_verified_at = Column(DateTime, nullable=True)

    # Account Status
    account_active = Column(Boolean, default=True)
    account_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv4 or IPv6

    # Status Management
    status = Column(
        Enum(CitizenStatus, values_callable=lambda x: [e.value for e in x]),
        default=CitizenStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    status_reason = Column(String(255), nullable=True)

    # Future Module 2: DigiLocker Integration
    digilocker_token = Column(String(500), nullable=True)
    digilocker_sync_at = Column(DateTime, nullable=True)

    # Future Module 6: Voice Processing
    preferred_voice_language = Column(String(20), nullable=True)
    voice_authentication_enabled = Column(Boolean, default=False)

    # Soft Delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Audit Trail
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)

    def __repr__(self) -> str:
        return f"<Citizen(id={self.id}, email={self.email}, full_name={self.full_name})>"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"

    def is_active(self) -> bool:
        """Check if citizen account is active"""
        return (
            self.account_active
            and not self.is_deleted
            and self.status == CitizenStatus.ACTIVE
        )

    def is_verified(self) -> bool:
        """Check if citizen email is verified"""
        return self.email_verified

    def can_login(self) -> bool:
        """Check if citizen can login"""
        return self.is_active() and not self.account_locked

    def is_account_locked(self) -> bool:
        """Check if account is locked due to failed attempts"""
        return self.account_locked

    def increment_failed_login(self) -> None:
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.account_locked = True

    def reset_failed_login(self) -> None:
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.account_locked = False

    def update_last_login(self, ip_address: str = None) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address

    # Indexes for query optimization
    __table_args__ = (
        Index("ix_citizen_email_status", "email", "status"),
        Index("ix_citizen_phone_status", "phone", "status"),
        Index("ix_citizen_aadhaar_status", "aadhaar_number", "status"),
        Index("ix_citizen_district_state", "district", "state"),
        Index("ix_citizen_created_at", "created_at"),
        Index("ix_citizen_updated_at", "updated_at"),
        Index("ix_citizen_is_deleted", "is_deleted"),
    )


class LoginAudit(Base):
    """Login Audit Log - Track login attempts and activities"""

    __tablename__ = "login_audits"

    # Primary Key
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Key
    citizen_id = Column(CHAR(36), nullable=False, index=True)

    # Login Details
    login_type = Column(String(20), nullable=False)  # password, refresh_token, etc
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255), nullable=True)

    # Network Information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<LoginAudit(citizen_id={self.citizen_id}, success={self.success}, created_at={self.created_at})>"

    __table_args__ = (
        Index("ix_login_audit_citizen_id", "citizen_id"),
        Index("ix_login_audit_success", "success"),
        Index("ix_login_audit_created_at", "created_at"),
    )
