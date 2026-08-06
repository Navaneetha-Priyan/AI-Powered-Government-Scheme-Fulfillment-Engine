"""SQLAlchemy models for the Module 3 scheme knowledge base."""
from datetime import datetime
from uuid import uuid4
import enum

from sqlalchemy import Boolean, CHAR, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class SchemeStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GovernmentScheme(Base):
    __tablename__ = "government_schemes"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    scheme_name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    department = Column(String(150), nullable=False, index=True)
    government_level = Column(String(30), nullable=False)
    state = Column(String(100), nullable=True, index=True)
    benefits = Column(Text, nullable=True)
    eligibility_summary = Column(Text, nullable=True)
    required_documents = Column(Text, nullable=True)
    application_process = Column(Text, nullable=True)
    official_link = Column(String(500), nullable=True)
    language = Column(String(20), nullable=False, default="en")
    status = Column(
    Enum(
        SchemeStatus,
        values_callable=lambda x: [e.value for e in x]
    ),
    nullable=False,
    default=SchemeStatus.DRAFT.value)    
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    documents = relationship("SchemeDocument", back_populates="scheme", cascade="all, delete-orphan", passive_deletes=True)
    chunks = relationship("SchemeChunk", back_populates="scheme", cascade="all, delete-orphan", passive_deletes=True)
    __table_args__ = (Index("ix_scheme_category_status", "category", "status"),)

    def __repr__(self) -> str:
        return f"<GovernmentScheme(id={self.id}, scheme_name={self.scheme_name})>"


class SchemeDocument(Base):
    __tablename__ = "scheme_documents"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    scheme_id = Column(CHAR(36), ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(CHAR(36), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    processing_status = Column(Enum(ProcessingStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ProcessingStatus.PENDING, index=True)
    processing_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheme = relationship("GovernmentScheme", back_populates="documents")
    chunks = relationship("SchemeChunk", back_populates="document", cascade="all, delete-orphan", passive_deletes=True)
    __table_args__ = (Index("ix_scheme_document_version", "scheme_id", "version"),)

    def __repr__(self) -> str:
        return f"<SchemeDocument(id={self.id}, scheme_id={self.scheme_id}, version={self.version})>"


class SchemeChunk(Base):
    __tablename__ = "scheme_chunks"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    scheme_id = Column(CHAR(36), ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(CHAR(36), ForeignKey("scheme_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    section_name = Column(String(150), nullable=True)
    embedding_id = Column(String(100), nullable=False, unique=True, index=True)
    token_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    scheme = relationship("GovernmentScheme", back_populates="chunks")
    document = relationship("SchemeDocument", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<SchemeChunk(id={self.id}, document_id={self.document_id}, page_number={self.page_number})>"
