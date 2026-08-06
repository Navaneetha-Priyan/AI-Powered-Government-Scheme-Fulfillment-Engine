"""ChromaDB adapter for Module 3 semantic retrieval."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable, Sequence

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import ProcessingFailedError, VectorDatabaseError
from app.services.scheme_embedding_service import SchemeEmbeddingService, get_scheme_embedding_service

logger = get_logger(__name__)


class VectorStoreService:
    """Keeps ChromaDB details behind a reusable Module 4-ready interface."""

    def __init__(self, embedding_service: SchemeEmbeddingService | None = None):
        self.embedding_service = embedding_service or get_scheme_embedding_service()
        self.collection = self._get_collection()

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_collection():
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - import guard
            raise ProcessingFailedError("ChromaDB dependencies are not installed") from exc

        try:
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
            return client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorDatabaseError(f"Unable to connect to ChromaDB: {exc}") from exc

    def upsert_chunks(self, chunks: Sequence[Any], scheme: Any, document: Any, embeddings: Sequence[Sequence[float]]) -> int:
        if not chunks:
            return 0

        try:
            ids = [chunk.embedding_id for chunk in chunks]
            documents = [chunk.chunk_text for chunk in chunks]
            metadatas = [
                {
                    "scheme_id": scheme.id,
                    "scheme_name": scheme.scheme_name,
                    "category": scheme.category,
                    "department": scheme.department,
                    "government_level": scheme.government_level,
                    "benefits": getattr(scheme, "benefits", None),
                    "document_id": document.id,
                    "document_version": document.version,
                    "page_number": chunk.page_number,
                    "section": chunk.section_name or "",
                    "processing_status": document.processing_status.value if hasattr(document.processing_status, "value") else str(document.processing_status),
                    "is_deleted": bool(getattr(scheme, "is_deleted", False)),
                }
                for chunk in chunks
            ]
            self.collection.upsert(ids=ids, embeddings=list(embeddings), documents=documents, metadatas=metadatas)
            return len(ids)
        except Exception as exc:
            raise VectorDatabaseError(f"Unable to upsert embeddings: {exc}") from exc

    def delete_document(self, chunks: Sequence[Any]) -> int:
        if not chunks:
            return 0

        try:
            ids = [chunk.embedding_id if hasattr(chunk, "embedding_id") else chunk for chunk in chunks]
            self.collection.delete(ids=ids)
            return len(ids)
        except Exception as exc:
            raise VectorDatabaseError(f"Unable to delete document vectors: {exc}") from exc

    def delete_scheme(self, scheme_id: str) -> int:
        try:
            self.collection.delete(where={"scheme_id": scheme_id})
            return 1
        except Exception as exc:
            raise VectorDatabaseError(f"Unable to delete scheme vectors: {exc}") from exc

    def search(self, query: str, limit: int = 5, category: str | None = None) -> list[dict[str, Any]]:
        try:
            query_embedding = self.embedding_service.embed_query(query)
            where = {"is_deleted": False}
            if category:
                where["category"] = category

            result = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorDatabaseError(f"Unable to query ChromaDB: {exc}") from exc

        documents = result.get("documents", [[]])
        metadatas = result.get("metadatas", [[]])
        distances = result.get("distances", [[]])
        if not documents or not documents[0]:
            return []

        items: list[dict[str, Any]] = []
        for document_text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
            similarity_score = max(0.0, round(1.0 - float(distance), 4))
            items.append(
                {
                    "scheme_id": metadata.get("scheme_id", ""),
                    "scheme_name": metadata.get("scheme_name", ""),
                    "category": metadata.get("category", ""),
                    "department": metadata.get("department", ""),
                    "similarity_score": similarity_score,
                    "matched_content": document_text,
                    "relevant_content": document_text,
                    "benefits": metadata.get("benefits"),
                    "page_number": metadata.get("page_number"),
                    "section_name": metadata.get("section", ""),
                    "document_id": metadata.get("document_id"),
                }
            )

        return items
