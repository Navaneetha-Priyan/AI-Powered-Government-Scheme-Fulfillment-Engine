"""Pydantic schemas for Module 3."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class SchemeCreateRequest(BaseModel):
    scheme_name: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=10000)
    category: str = Field(min_length=2, max_length=100)
    department: str = Field(min_length=2, max_length=150)
    government_level: str = Field(pattern="^(central|state)$")
    state: Optional[str] = Field(default=None, max_length=100)
    benefits: Optional[str] = Field(default=None, max_length=10000)
    eligibility_summary: Optional[str] = Field(default=None, max_length=10000)
    required_documents: Optional[str] = Field(default=None, max_length=10000)
    application_process: Optional[str] = Field(default=None, max_length=10000)
    official_link: Optional[HttpUrl] = None
    language: str = Field(default="en", max_length=20)
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")

    @field_validator("scheme_name", "category", "department", "government_level", "language", "status", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() if value in {"draft", "active", "archived", "central", "state"} else value.strip()
        return value


class SchemeUpdateRequest(BaseModel):
    scheme_name: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=10, max_length=10000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    department: Optional[str] = Field(default=None, min_length=2, max_length=150)
    government_level: Optional[str] = Field(default=None, pattern="^(central|state)$")
    state: Optional[str] = Field(default=None, max_length=100)
    benefits: Optional[str] = Field(default=None, max_length=10000)
    eligibility_summary: Optional[str] = Field(default=None, max_length=10000)
    required_documents: Optional[str] = Field(default=None, max_length=10000)
    application_process: Optional[str] = Field(default=None, max_length=10000)
    official_link: Optional[HttpUrl] = None
    language: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, pattern="^(draft|active|archived)$")

    @field_validator("scheme_name", "category", "department", "government_level", "language", "status", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() if value in {"draft", "active", "archived", "central", "state"} else value.strip()
        return value


class SchemeSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = Field(default=None, max_length=100)


class SchemeDocumentStatusRequest(BaseModel):
    processing_status: Optional[str] = None


class SchemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scheme_name: str
    description: str
    category: str
    department: str
    government_level: str
    state: Optional[str] = None
    benefits: Optional[str] = None
    eligibility_summary: Optional[str] = None
    required_documents: Optional[str] = None
    application_process: Optional[str] = None
    official_link: Optional[str] = None
    language: str
    status: str
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class SchemeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scheme_id: str
    file_name: str
    file_path: str
    file_size: int
    uploaded_by: Optional[str] = None
    version: int
    processing_status: str
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class SchemeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scheme_id: str
    document_id: str
    chunk_text: str
    page_number: int
    section_name: Optional[str] = None
    embedding_id: str
    token_count: int
    created_at: datetime


class SchemeSearchResult(BaseModel):
    scheme_id: str
    scheme_name: str
    category: str
    department: str
    similarity_score: float
    matched_content: str
    relevant_content: str
    benefits: Optional[str] = None
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    document_id: Optional[str] = None


class SchemeSearchResponse(BaseModel):
    items: List[SchemeSearchResult]
    query: str
    limit: int
    total: int
