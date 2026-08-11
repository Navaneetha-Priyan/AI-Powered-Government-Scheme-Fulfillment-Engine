"""Pydantic Schemas for Real Document Processing (OCR / PDF Text Extraction).

These schemas describe the *outcome* of processing a real uploaded document
through the new pipeline:

    User uploads PDF/Image
        -> DocumentProcessingService
        -> PdfTextExtractor / DocumentOcrService
        -> DocumentFieldExtractor
        -> ExtractedDocumentData
        -> DocumentProfileMapper      # existing Step 3
        -> ProfileEnrichmentService   # existing Step 4
        -> Database

The result intentionally does NOT expose raw OCR text or full document contents
to the frontend (privacy). It reports the extraction method, the extracted
fields, the mapped fields, and the enrichment outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.citizen_profile import DocumentTypeEnum
from app.schemas.document_profile import EnrichmentResult


class DocumentProcessingResult(BaseModel):
    """Structured outcome of processing one real uploaded document."""

    document_id: Optional[str] = Field(
        default=None,
        description="Provenance id of the source GovernmentDocument.",
    )
    document_type: DocumentTypeEnum = Field(
        ...,
        description="Canonical document type that was processed.",
    )
    extraction_method: str = Field(
        ...,
        description="How the raw text was obtained: 'pdf_text' or 'ocr'.",
    )
    extracted_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Normalized fields extracted from the document text.",
    )
    mapped_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Canonical domain fields the document would update.",
    )
    enrichment: Optional[EnrichmentResult] = Field(
        default=None,
        description="Outcome of the existing ProfileEnrichmentService run.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (e.g. OCR fallback used, missing fields).",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Fatal errors that prevented full processing.",
    )