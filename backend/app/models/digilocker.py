"""SQLAlchemy Models for Mock DigiLocker Documents (Module 2)"""
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Text,
    Index,
    Enum,
    CHAR,
    ForeignKey,
    JSON,
)
from datetime import datetime
from uuid import uuid4
import enum

from app.database.connection import Base


class DocumentType(str, enum.Enum):
    """Government document types"""

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


class DocumentVerificationStatus(str, enum.Enum):
    """Document verification status"""

    VERIFIED = "verified"
    PENDING = "pending"
    EXPIRED = "expired"
    REJECTED = "rejected"


class DigiLockerRecord(Base):
    """Mock DigiLocker — master record per citizen"""

    __tablename__ = "digilocker_records"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(
        CHAR(36),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # DigiLocker account simulation
    digilocker_id = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_count = Column(String(10), default="0")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DigiLockerRecord(citizen_id={self.citizen_id}, digilocker_id={self.digilocker_id})>"

    __table_args__ = (
        Index("ix_digilocker_citizen_id", "citizen_id"),
        Index("ix_digilocker_id", "digilocker_id"),
    )


class GovernmentDocument(Base):
    """Individual government document linked to a citizen via DigiLocker"""

    __tablename__ = "government_documents"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(
        CHAR(36),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    digilocker_record_id = Column(
        CHAR(36),
        ForeignKey("digilocker_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type = Column(
        Enum(DocumentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    document_number = Column(String(100), nullable=True)
    document_name = Column(String(200), nullable=False)

    # Dates
    issue_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # Verification
    verification_status = Column(
        Enum(
            DocumentVerificationStatus,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DocumentVerificationStatus.VERIFIED,
        nullable=False,
    )
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Mock download URL
    download_url = Column(String(500), nullable=True)

    # Flexible metadata (issuing authority, remarks, etc.)
    doc_metadata = Column(Text, nullable=True)  # JSON string

    # Soft delete
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<GovernmentDocument(citizen_id={self.citizen_id}, type={self.document_type})>"

    def is_expired(self) -> bool:
        """Check if document is expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.utcnow()

    __table_args__ = (
        Index("ix_gov_doc_citizen_id", "citizen_id"),
        Index("ix_gov_doc_type", "document_type"),
        Index("ix_gov_doc_verification_status", "verification_status"),
        Index("ix_gov_doc_digilocker_record_id", "digilocker_record_id"),
    )
