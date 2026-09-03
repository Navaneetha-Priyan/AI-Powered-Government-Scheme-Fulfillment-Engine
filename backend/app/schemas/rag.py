"""Pydantic schemas for the Government Scheme RAG API.

These schemas define the request/response contract for
``POST /api/schemes/rag/query``.

The RAG system provides **policy information** grounded ONLY in the retrieved
government-scheme PDF content. It does NOT perform citizen-specific eligibility
evaluation — that remains the responsibility of the existing eligibility engine.
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    """Request body for ``POST /api/schemes/rag/query``."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language question about government schemes "
        "(Tamil, English, Tanglish, or code-mixed).",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve. Defaults to RAG_TOP_K.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Preferred response language (e.g. 'en', 'ta'). "
        "If omitted, the query language is detected automatically.",
    )


class RagSource(BaseModel):
    """A single source chunk that contributed to the RAG answer."""

    scheme_name: str = Field(..., description="Name of the scheme (from PDF filename or metadata).")
    source_file: str = Field(..., description="PDF filename the chunk was extracted from.")
    page_number: Optional[int] = Field(default=None, description="1-based page number in the PDF.")
    score: float = Field(..., description="Similarity score (0.0 to 1.0).")
    chunk_text: Optional[str] = Field(
        default=None,
        description="The retrieved chunk text (may be omitted for brevity).",
    )
    section_name: Optional[str] = Field(default=None, description="Section heading if detected.")
    document_type: str = Field(default="government_scheme", description="Type of source document.")


class RagQueryResponse(BaseModel):
    """Response body for ``POST /api/schemes/rag/query``."""

    query: str = Field(..., description="The original query.")
    answer: str = Field(..., description="Grounded answer generated from retrieved chunks.")
    sources: List[RagSource] = Field(
        default_factory=list,
        description="Source chunks that informed the answer.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Detected or requested response language.",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence in the answer (0.0 to 1.0).",
    )
    is_grounded: bool = Field(
        default=True,
        description="Whether the answer was grounded in retrieved content.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Additional message (e.g. when no relevant content was found).",
    )
