"""SQLAlchemy Models for Citizen Profile & Mock DigiLocker Integration (Module 2)"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    Float,
    Index,
    Enum,
    CHAR,
    ForeignKey,
)
from datetime import datetime
from uuid import uuid4
import enum

from app.database.connection import Base


class IncomeCategory(str, enum.Enum):
    """Income category classification"""

    BPL = "bpl"  # Below Poverty Line
    APL = "apl"  # Above Poverty Line
    EWS = "ews"  # Economically Weaker Section
    LIG = "lig"  # Lower Income Group
    MIG = "mig"  # Middle Income Group
    HIG = "hig"  # Higher Income Group


class MaritalStatus(str, enum.Enum):
    """Marital status"""

    SINGLE = "single"
    MARRIED = "married"
    WIDOWED = "widowed"
    DIVORCED = "divorced"
    SEPARATED = "separated"


class LandType(str, enum.Enum):
    """Type of land ownership"""

    AGRICULTURAL = "agricultural"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    FOREST = "forest"
    WASTELAND = "wasteland"


class ProfileSyncStatus(str, enum.Enum):
    """DigiLocker sync status"""

    NOT_SYNCED = "not_synced"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"
    SYNC_PENDING = "sync_pending"


class CitizenProfile(Base):
    """Extended citizen profile — populated from mock DigiLocker"""

    __tablename__ = "citizen_profiles"

    # Primary Key
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Key to citizens table
    citizen_id = Column(
        CHAR(36),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Personal Details
    father_name = Column(String(100), nullable=True)
    mother_name = Column(String(100), nullable=True)
    occupation = Column(String(100), nullable=True)
    marital_status = Column(
        Enum(MaritalStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    blood_group = Column(String(5), nullable=True)
    nationality = Column(String(50), default="Indian")

    # Economic Details
    annual_income = Column(Float, nullable=True)
    income_category = Column(
        Enum(IncomeCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Social Classification
    caste = Column(String(100), nullable=True)
    community = Column(String(100), nullable=True)
    sub_caste = Column(String(100), nullable=True)
    religion = Column(String(50), nullable=True)

    # Special Status Flags
    is_disabled = Column(Boolean, default=False)
    disability_type = Column(String(100), nullable=True)
    disability_percentage = Column(Integer, nullable=True)

    is_farmer = Column(Boolean, default=False)
    farmer_id = Column(String(50), nullable=True)

    # Education
    education_level = Column(String(100), nullable=True)
    education_institution = Column(String(200), nullable=True)

    # Family
    family_member_count = Column(Integer, nullable=True)
    family_details = Column(Text, nullable=True)  # JSON string

    # Profile Completion
    profile_completion_percentage = Column(Integer, default=0)
    sync_status = Column(
        Enum(ProfileSyncStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProfileSyncStatus.NOT_SYNCED,
        nullable=False,
    )
    last_synced_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CitizenProfile(citizen_id={self.citizen_id}, sync_status={self.sync_status})>"

    __table_args__ = (
        Index("ix_citizen_profile_citizen_id", "citizen_id"),
        Index("ix_citizen_profile_sync_status", "sync_status"),
        Index("ix_citizen_profile_income_category", "income_category"),
        Index("ix_citizen_profile_caste", "caste"),
        Index("ix_citizen_profile_is_farmer", "is_farmer"),
        Index("ix_citizen_profile_is_disabled", "is_disabled"),
    )


class LandRecord(Base):
    """Land ownership records for a citizen"""

    __tablename__ = "land_records"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    citizen_id = Column(
        CHAR(36),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    survey_number = Column(String(50), nullable=True)
    land_area = Column(Float, nullable=True)  # in acres
    land_area_unit = Column(String(20), default="acres")
    land_type = Column(
        Enum(LandType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    village = Column(String(100), nullable=True)
    taluk = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    ownership_type = Column(String(50), nullable=True)  # owned, leased, inherited
    patta_number = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<LandRecord(citizen_id={self.citizen_id}, survey={self.survey_number})>"

    __table_args__ = (
        Index("ix_land_record_citizen_id", "citizen_id"),
        Index("ix_land_record_district", "district"),
    )
