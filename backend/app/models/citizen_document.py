"""Persistent records for citizen document intelligence."""
import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, CHAR, Column, DateTime, Enum, Float, ForeignKey, Index, String, Text
from app.database.connection import Base

class CitizenDocumentType(str, enum.Enum):
    UNKNOWN='unknown'; AADHAAR_CARD='aadhaar_card'; SMART_RATION_CARD='smart_ration_card'; INCOME_CERTIFICATE='income_certificate'; COMMUNITY_CERTIFICATE='community_certificate'; LAND_DOCUMENT='land_document'; FARMER_DOCUMENT='farmer_document'; DISABILITY_CERTIFICATE='disability_certificate'; BANK_PASSBOOK='bank_passbook'; EDUCATION_CERTIFICATE='education_certificate'
class DocumentProcessStatus(str, enum.Enum): UPLOADED='uploaded'; PROCESSING='processing'; PROCESSED='processed'; NEEDS_REVIEW='needs_review'; VERIFIED='verified'; FAILED='failed'
class VerificationStatus(str, enum.Enum): PENDING='pending'; VERIFIED='verified'; REJECTED='rejected'
class UploadedDocument(Base):
    __tablename__='uploaded_documents'
    id=Column(CHAR(36),primary_key=True,default=lambda:str(uuid4())); citizen_id=Column(CHAR(36),ForeignKey('citizens.id',ondelete='CASCADE'),nullable=False,index=True)
    document_type=Column(Enum(CitizenDocumentType,values_callable=lambda x:[e.value for e in x]),nullable=False,default=CitizenDocumentType.UNKNOWN,index=True)
    original_file_name=Column(String(255),nullable=False); file_path=Column(String(500),nullable=False); file_size=Column(Float,nullable=False); mime_type=Column(String(100),nullable=False)
    upload_status=Column(Enum(DocumentProcessStatus,values_callable=lambda x:[e.value for e in x]),nullable=False,default=DocumentProcessStatus.UPLOADED); verification_status=Column(Enum(VerificationStatus,values_callable=lambda x:[e.value for e in x]),nullable=False,default=VerificationStatus.PENDING); processing_error=Column(Text); created_at=Column(DateTime,nullable=False,default=datetime.utcnow); updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class ExtractedInformation(Base):
    __tablename__='extracted_information'
    id=Column(CHAR(36),primary_key=True,default=lambda:str(uuid4())); document_id=Column(CHAR(36),ForeignKey('uploaded_documents.id',ondelete='CASCADE'),nullable=False,index=True); field_name=Column(String(100),nullable=False,index=True); field_value=Column(Text,nullable=False); confidence_score=Column(Float,nullable=False,default=0.0); is_verified=Column(Boolean,nullable=False,default=False); created_at=Column(DateTime,nullable=False,default=datetime.utcnow)
class ProfileVerification(Base):
    __tablename__='profile_verifications'
    id=Column(CHAR(36),primary_key=True,default=lambda:str(uuid4())); citizen_id=Column(CHAR(36),ForeignKey('citizens.id',ondelete='CASCADE'),nullable=False,unique=True,index=True); verified_fields=Column(Text,nullable=False,default='[]'); pending_fields=Column(Text,nullable=False,default='[]'); verification_status=Column(Enum(VerificationStatus,values_callable=lambda x:[e.value for e in x]),nullable=False,default=VerificationStatus.PENDING); created_at=Column(DateTime,nullable=False,default=datetime.utcnow); updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class ProfileConflict(Base):
    __tablename__='profile_conflicts'
    id=Column(CHAR(36),primary_key=True,default=lambda:str(uuid4())); citizen_id=Column(CHAR(36),ForeignKey('citizens.id',ondelete='CASCADE'),nullable=False,index=True); field_name=Column(String(100),nullable=False,index=True); primary_document_id=Column(CHAR(36),ForeignKey('uploaded_documents.id',ondelete='CASCADE'),nullable=False); primary_value=Column(Text,nullable=False); conflicting_document_id=Column(CHAR(36),ForeignKey('uploaded_documents.id',ondelete='CASCADE'),nullable=False); conflicting_value=Column(Text,nullable=False); is_resolved=Column(Boolean,nullable=False,default=False); created_at=Column(DateTime,nullable=False,default=datetime.utcnow)
