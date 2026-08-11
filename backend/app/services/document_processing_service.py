"""DocumentProcessingService — Phase 10: Real Document → Profile Enrichment.

Orchestrates the real-document pipeline for uploaded PDFs/images:

    User uploads PDF/Image
        -> DocumentProcessingService      # THIS STEP
        -> PdfTextExtractor / DocumentOcrService
        -> DocumentFieldExtractor
        -> ExtractedDocumentData
        -> DocumentProfileMapper          # existing Step 3
        -> ProfileEnrichmentService       # existing Step 4
        -> citizens / citizen_profiles / land_records

The service keeps API routes thin and reuses the existing Steps 2–5 components
unchanged. It never writes to ``citizen_profiles`` / ``land_records`` directly —
the only persistence layer remains ``ProfileEnrichmentService``.

Extraction decision (Phase 3):
- PDF → attempt ``PdfTextExtractor`` first.
- If the PDF has no meaningful text layer (or text extraction fails with a
  controlled error), fall back to ``DocumentOcrService``.
- Image files → OCR directly.

Privacy: the returned ``DocumentProcessingResult`` does NOT include raw OCR/PDF
text. Only normalized extracted fields are reported.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.exceptions.exceptions import (
    DocumentOcrError,
    DocumentProcessingError,
    DocumentTextExtractionError,
    UnsupportedDocumentTypeError,
)
from app.schemas.document_processing import DocumentProcessingResult
from app.schemas.document_profile import ExtractedDocumentData
from app.services.document_field_extractor import DocumentFieldExtractor
from app.services.document_ocr_service import DocumentOcrService
from app.services.document_profile_mapper import DocumentProfileMapper
from app.services.pdf_text_extractor import PdfTextExtractor
from app.services.profile_enrichment_service import ProfileEnrichmentService

logger = get_logger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class DocumentProcessingService:
    """Orchestrates real-document text extraction → field extraction → mapping
    → enrichment."""

    def __init__(self, db: Session):
        self.db = db
        self.pdf_extractor = PdfTextExtractor()
        self.ocr_service = DocumentOcrService()
        self.field_extractor = DocumentFieldExtractor()
        self.mapper = DocumentProfileMapper()

    def process_file(
        self,
        *,
        file_path: str,
        document_type: str,
        citizen_id: str,
        document_id: Optional[str] = None,
    ) -> DocumentProcessingResult:
        """Process a real uploaded file and enrich the citizen's profile.

        Returns a structured :class:`DocumentProcessingResult`. Raises
        ``DocumentProcessingError`` when the file cannot be processed at all.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentProcessingError(
                reason=f"Uploaded file not found: {path.name}",
                document_type=document_type,
                document_id=document_id or "",
            )

        suffix = path.suffix.lower()
        if suffix not in _IMAGE_EXTENSIONS and suffix != ".pdf":
            raise DocumentProcessingError(
                reason=f"Unsupported file type: {suffix or 'unknown'}",
                document_type=document_type,
                document_id=document_id or "",
            )

        # Phase 3: PDF → text extraction first, OCR fallback only when needed.
        raw_text: str
        extraction_method: str
        warnings: list[str] = []

        if suffix == ".pdf":
            try:
                raw_text = self.pdf_extractor.extract(file_path)
                extraction_method = "pdf_text"
            except DocumentTextExtractionError as exc:
                logger.info(
                    "PDF text extraction not usable for %s (%s); falling back to OCR",
                    path.name,
                    exc.message,
                )
                warnings.append("PDF had no usable text layer; OCR was used.")
                raw_text = self.ocr_service.ocr_file(file_path)
                extraction_method = "ocr"
        else:
            raw_text = self.ocr_service.ocr_file(file_path)
            extraction_method = "ocr"

        # Phase 5/6/7/8: raw text → normalized ExtractedDocumentData.
        extracted: ExtractedDocumentData = self.field_extractor.extract(
            document_type=document_type,
            raw_text=raw_text,
            document_id=document_id,
        )

        # Phase 9: reuse existing Step 3 mapper.
        mapped = self.mapper.map(extracted)

        # Phase 9: reuse existing Step 4 enrichment (the ONLY persistence layer).
        enrichment = ProfileEnrichmentService(self.db).enrich(
            citizen_id, mapped
        )

        result = DocumentProcessingResult(
            document_id=document_id,
            document_type=extracted.document_type,
            extraction_method=extraction_method,
            extracted_fields=extracted.fields,
            mapped_fields={
                "citizen_updates": mapped.citizen_updates,
                "profile_updates": mapped.profile_updates,
                "land_record_updates": [
                    land.model_dump(exclude_none=True)
                    for land in mapped.land_record_updates
                ],
            },
            enrichment=enrichment,
            warnings=warnings,
        )

        logger.info(
            "Processed %s (%s) via %s for citizen %s",
            path.name,
            extracted.document_type.value,
            extraction_method,
            citizen_id,
        )
        return result