"""Module 3 scheme management, PDF processing, and semantic retrieval."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import (
    ConflictError,
    DuplicateSchemeError,
    EmbeddingGenerationFailedError,
    InvalidPDFError,
    ProcessingFailedError,
    SchemeDocumentNotFoundError,
    SchemeNotFoundError,
    VectorDatabaseError,
)
from app.models.government_scheme import ProcessingStatus
from app.repositories.government_scheme_repository import (
    GovernmentSchemeRepository,
    SchemeDocumentRepository,
)
from app.services.scheme_embedding_service import SchemeEmbeddingService, get_scheme_embedding_service
from app.services.scheme_processing_service import SchemeProcessingService
from app.services.vector_store_service import VectorStoreService

logger = get_logger(__name__)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "scheme"


class GovernmentSchemeService:
    def __init__(self, db: Session):
        self.db = db
        self.schemes = GovernmentSchemeRepository(db)
        self.documents = SchemeDocumentRepository(db)
        self.processing_service = SchemeProcessingService()
        self.embedding_service = get_scheme_embedding_service()
        self.vector_store = VectorStoreService(self.embedding_service)

    def create_scheme(self, data: dict):
        if self.schemes.get_by_name(data["scheme_name"]):
            raise DuplicateSchemeError(data["scheme_name"])

        if "status" in data:
            from app.models.government_scheme import SchemeStatus
            data["status"] = SchemeStatus(data["status"])

        return self.schemes.create(data)

    def get_scheme(self, scheme_id: str):
        scheme = self.schemes.get(scheme_id)
        if not scheme:
            raise SchemeNotFoundError(scheme_id)
        return scheme

    def list_schemes(self, skip: int = 0, limit: int = 20, category: str | None = None, status: str | None = None, query: str | None = None):
        items = self.schemes.list(skip, limit, category, status, query)
        total = self.schemes.count(category, status, query)
        return items, total

    def update_scheme(self, scheme_id: str, data: dict):
        scheme = self.get_scheme(scheme_id)
        if "scheme_name" in data and data["scheme_name"]:
            existing = self.schemes.get_by_name(data["scheme_name"], exclude_id=scheme_id)
            if existing:
                raise DuplicateSchemeError(data["scheme_name"])
        return self.schemes.update(scheme, data)

    def delete_scheme(self, scheme_id: str):
        scheme = self.get_scheme(scheme_id)
        try:
            self.vector_store.delete_scheme(scheme_id)
        except VectorDatabaseError:
            logger.exception("Vector cleanup failed for scheme delete: %s", scheme_id)
            raise
        self.schemes.delete(scheme)

    def save_pdf(self, scheme_id: str, file: UploadFile, uploaded_by: str):
        scheme = self.get_scheme(scheme_id)
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise InvalidPDFError()
        if file.content_type not in {"application/pdf", "application/octet-stream", None}:
            raise InvalidPDFError()

        content = file.file.read()
        if len(content) > settings.MAX_SCHEME_PDF_SIZE_BYTES:
            raise InvalidPDFError("Uploaded PDF exceeds the maximum allowed size")
        if not content.startswith(b"%PDF"):
            raise InvalidPDFError("Uploaded file is not a valid PDF document")

        version = self.documents.get_latest_version(scheme_id) + 1
        category_folder = _slugify(scheme.category)
        scheme_folder = _slugify(scheme.scheme_name)
        storage_dir = Path(settings.SCHEME_STORAGE_DIR) / category_folder / scheme_folder
        storage_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{scheme_folder}_v{version}.pdf"
        stored_path = storage_dir / stored_name
        stored_path.write_bytes(content)

        logger.info(
            "Stored scheme document",
            extra={
                "scheme_id": scheme_id,
                "version": version,
                "file_path": str(stored_path),
                "uploaded_by": uploaded_by,
            },
        )

        return self.documents.create(
            {
                "scheme_id": scheme.id,
                "file_name": Path(file.filename).name,
                "file_path": str(stored_path),
                "file_size": len(content),
                "uploaded_by": uploaded_by,
                "version": version,
                "processing_status": ProcessingStatus.PENDING,
            }
        )

    def process_document(self, document_id: str):
        document = self.documents.get(document_id)
        if not document:
            raise SchemeDocumentNotFoundError(document_id)

        scheme = self.get_scheme(document.scheme_id)
        old_chunks = self.documents.get_chunks(document.id)
        old_chunk_ids = [chunk.embedding_id for chunk in old_chunks]
        if old_chunk_ids:
            self.vector_store.delete_document(old_chunk_ids)
        self.documents.clear_chunks(document.id)

        self.documents.set_processing_status(document, ProcessingStatus.PROCESSING, None)
        try:
            processed_chunks = self.processing_service.process_pdf(scheme.id, document.id, document.file_path)
            embeddings = self.embedding_service.embed_texts([chunk.chunk_text for chunk in processed_chunks])
            if len(embeddings) != len(processed_chunks):
                raise EmbeddingGenerationFailedError("Embedding count did not match chunk count")

            chunk_payloads = [
                {
                    "scheme_id": chunk.scheme_id,
                    "document_id": chunk.document_id,
                    "chunk_text": chunk.chunk_text,
                    "page_number": chunk.page_number,
                    "section_name": chunk.section_name,
                    "embedding_id": chunk.embedding_id,
                    "token_count": chunk.token_count,
                }
                for chunk in processed_chunks
            ]

            created_chunks = self.documents.add_chunks(chunk_payloads)
            self.vector_store.upsert_chunks(created_chunks, scheme, document, embeddings)
            self.documents.set_processing_status(document, ProcessingStatus.COMPLETED, None)
            logger.info(
                "Completed document processing",
                extra={"document_id": document_id, "chunk_count": len(created_chunks)},
            )
            return len(created_chunks)
        except SchemeDocumentNotFoundError:
            raise
        except (InvalidPDFError, EmbeddingGenerationFailedError, VectorDatabaseError) as exc:
            self.documents.set_processing_status(document, ProcessingStatus.FAILED, str(exc))
            raise ProcessingFailedError(str(exc)) from exc
        except Exception as exc:
            self.documents.set_processing_status(document, ProcessingStatus.FAILED, str(exc))
            logger.exception("Document processing failed for %s", document_id)
            raise ProcessingFailedError(str(exc)) from exc

    def get_document(self, document_id: str):
        document = self.documents.get(document_id)
        if not document:
            raise SchemeDocumentNotFoundError(document_id)
        return document

    def semantic_search(self, query: str, limit: int = 5, category: str | None = None):
        try:
            return self.vector_store.search(query=query, limit=limit, category=category)
        except VectorDatabaseError:
            logger.exception("Semantic search failed")
            raise
