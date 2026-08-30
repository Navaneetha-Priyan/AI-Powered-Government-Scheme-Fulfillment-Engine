"""SchemeRetrievalService — Government Scheme RAG retrieval layer.

This service provides a clean abstraction over the existing ChromaDB vector
store for retrieving relevant government-scheme document chunks. It hides all
ChromaDB implementation details from the rest of the application.

Design rules:
- Reuses the existing ``SchemeEmbeddingService`` and ``VectorStoreService``.
- Does NOT duplicate the existing ``GovernmentSchemeService.semantic_search``
  used by the recommendation engine; instead it provides a dedicated,
  RAG-specific retrieval path with its own collection.
- Returns structured results with chunk text, scheme name, source file,
  page number, and similarity score.
- Never fabricates results — if no chunks match, returns an empty list.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import VectorDatabaseError
from app.services.scheme_embedding_service import (
    SchemeEmbeddingService,
    get_scheme_embedding_service,
)

logger = get_logger(__name__)

_DOMAIN_TERMS = {
    "agriculture": {
        "agriculture",
        "agricultural",
        "farmer",
        "farmers",
        "farming",
        "crop",
        "crops",
        "irrigation",
        "kisan",
        "krishi",
        "mandi",
        "market",
        "patta",
        "land",
        "uzhavar",
    },
    "low_income": {
        "poor",
        "poverty",
        "income",
        "low",
        "families",
        "family",
        "ration",
        "food",
        "subsidy",
        "ujjwala",
        "jan",
        "dhan",
    },
}

_GENERIC_QUERY_TERMS = {
    "government",
    "scheme",
    "schemes",
    "available",
    "availability",
    "assistance",
    "help",
    "benefit",
    "benefits",
    "need",
    "provide",
    "provides",
    "related",
    "document",
    "documents",
    "required",
    "apply",
    "application",
    "what",
    "which",
    "for",
    "the",
    "and",
    "does",
    "any",
    "are",
    "is",
    "i",
    "me",
    "a",
    "an",
}


def _derive_scheme_name(filename: str) -> str:
    """Derive a human-readable scheme name from a PDF filename.

    Converts e.g. ``PM_Kisan_Samman_Nidhi.pdf`` → ``PM Kisan Samman Nidhi``.
    Falls back to the filename stem if no transformation is possible.
    """
    stem = Path(filename).stem
    # Replace underscores and hyphens with spaces.
    name = re.sub(r"[_\-]+", " ", stem)
    # Collapse multiple spaces.
    name = re.sub(r"\s+", " ", name).strip()
    # Remove common version suffixes like "_2", "_3" appended during download.
    name = re.sub(r"\s*\b(v\d+|version\s*\d+)\s*$", "", name, flags=re.IGNORECASE)
    return name or stem


def _normalize_for_match(text: str) -> str:
    """Normalize names/queries for lightweight deterministic matching.

    Preserves:
    - Tamil letters (Lo), combining marks (Mn, Mc)
    - English letters, digits
    - Tanglish / mixed Tamil-English text
    """
    if not text:
        return ""

    # Normalize Unicode to NFC form (composed characters)
    normalized = unicodedata.normalize("NFC", text.lower())

    # Remove file extensions
    normalized = re.sub(r"\.[a-z0-9]+$", "", normalized)
    # Replace underscores and hyphens with spaces
    normalized = re.sub(r"[_\-]+", " ", normalized)

    # Keep: letters (all scripts), marks (combining), numbers, spaces
    # Remove: punctuation, symbols, control chars, etc.
    kept_chars = []
    for ch in normalized:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("M") or cat.startswith("N") or ch.isspace():
            kept_chars.append(ch)
        else:
            kept_chars.append(" ")
    normalized = "".join(kept_chars)

    # Remove version suffixes like "v2", "version 3"
    normalized = re.sub(r"\b(v|version)\s*\d+\b", " ", normalized)
    # Remove trailing standalone numbers
    normalized = re.sub(r"\b\d+\b$", " ", normalized)

    return re.sub(r"\s+", " ", normalized).strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _normalize_for_match(text).split()
        if token and token not in _GENERIC_QUERY_TERMS
    }


def _canonical_scheme_key(scheme_name: str, source_file: str = "") -> str:
    """Return a duplicate-resistant key for one scheme across PDF versions."""
    base = _normalize_for_match(scheme_name) or _normalize_for_match(source_file)
    return re.sub(r"\s+", " ", base).strip()


def _query_domains(query_tokens: set[str]) -> set[str]:
    domains: set[str] = set()
    for domain, terms in _DOMAIN_TERMS.items():
        if query_tokens & terms:
            domains.add(domain)
    return domains


class SchemeRetrievalService:
    """Retrieve relevant government-scheme document chunks via semantic search.

    This is the single abstraction for RAG vector retrieval. All ChromaDB
    logic lives inside this service (via the existing ``VectorStoreService``).
    """

    def __init__(
        self,
        embedding_service: Optional[SchemeEmbeddingService] = None,
    ) -> None:
        if embedding_service is None:
            embedding_service = SchemeEmbeddingService(
                model_name=settings.RAG_EMBEDDING_MODEL,
                dimension=settings.RAG_EMBEDDING_DIMENSION,
            )
        self.embedding_service = embedding_service
        self._collection = None
        self._all_chunks_cache: Optional[List[dict[str, Any]]] = None

    # ── ChromaDB collection management ────────────────────────────────────

    @property
    def collection(self):
        """Lazily create / retrieve the RAG ChromaDB collection."""
        if self._collection is not None:
            return self._collection
        self._collection = self._get_or_create_collection()
        return self._collection

    def _get_or_create_collection(self):
        """Create the RAG collection if it does not exist."""
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - import guard
            raise VectorDatabaseError(
                "ChromaDB dependencies are not installed"
            ) from exc

        try:
            client = chromadb.PersistentClient(
                path=settings.RAG_PERSIST_DIRECTORY
            )
            return client.get_or_create_collection(
                name=settings.RAG_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorDatabaseError(
                f"Unable to connect to ChromaDB: {exc}"
            ) from exc

    def _get_client(self):
        """Return the underlying ChromaDB PersistentClient."""
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - import guard
            raise VectorDatabaseError(
                "ChromaDB dependencies are not installed"
            ) from exc
        return chromadb.PersistentClient(path=settings.RAG_PERSIST_DIRECTORY)

    # ── Ingestion support ───────────────────────────────────────────────────

    def add_chunks(
        self,
        chunks: Sequence[dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        """Add pre-computed chunk embeddings to the RAG collection.

        Each ``chunk`` dict must contain:
            - ``chunk_id``: unique identifier
            - ``text``: the chunk text
            - ``scheme_name``: derived scheme name
            - ``source_file``: PDF filename
            - ``page_number``: 1-based page number
            - ``document_type``: always "government_scheme"
            - ``section_name``: optional section heading
        """
        if not chunks:
            return 0

        try:
            ids = [chunk["chunk_id"] for chunk in chunks]
            documents = [
                chunk.get("text", "")
                for chunk in chunks
            ]
            metadatas = [
                {
                    "scheme_name": chunk.get("scheme_name", ""),
                    "normalized_scheme_name": _canonical_scheme_key(
                        chunk.get("scheme_name", ""),
                        chunk.get("source_file", ""),
                    ),
                    "source_file": chunk.get("source_file", ""),
                    "page_number": chunk.get("page_number", 0),
                    "document_type": chunk.get("document_type", "government_scheme"),
                    "section_name": chunk.get("section_name", ""),
                    "chunk_id": chunk.get("chunk_id", ""),
                }
                for chunk in chunks
            ]
            self.collection.upsert(
                ids=ids,
                embeddings=list(embeddings),
                documents=documents,
                metadatas=metadatas,
            )
            self._all_chunks_cache = None
            return len(ids)
        except Exception as exc:
            raise VectorDatabaseError(
                f"Unable to upsert RAG chunks: {exc}"
            ) from exc

    def delete_all(self) -> int:
        """Delete all documents from the RAG collection (full rebuild)."""
        try:
            # ChromaDB does not have a direct "delete all" — we delete by
            # fetching all IDs first.
            result = self.collection.get(
                include=["metadatas"],
            )
            ids = result.get("ids", [])
            if ids:
                self.collection.delete(ids=ids)
            self._all_chunks_cache = None
            return len(ids)
        except Exception as exc:
            raise VectorDatabaseError(
                f"Unable to clear RAG collection: {exc}"
            ) from exc

    def reset_collection(self) -> None:
        """Delete the entire RAG collection and recreate it on next access.

        This is required when the embedding dimension changes (e.g. switching
        from all-MiniLM-L6-v2 to BAAI/bge-m3), because ChromaDB collections
        are locked to the dimension they were created with.
        """
        try:
            client = self._get_client()
            client.delete_collection(name=settings.RAG_COLLECTION_NAME)
        except Exception:
            pass
        self._collection = None
        self._all_chunks_cache = None

    def count(self) -> int:
        """Return the number of documents in the RAG collection."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    # ── Retrieval ───────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> List[dict[str, Any]]:
        """Retrieve the top-k most relevant chunks for a query.

        Returns a list of dicts, each containing:
            - ``text``: the chunk text
            - ``scheme_name``: scheme name
            - ``source_file``: PDF filename
            - ``page_number``: page number
            - ``score``: similarity score (0.0 to 1.0)
            - ``section_name``: section heading (if any)
            - ``document_type``: "government_scheme"
            - ``metadata``: full metadata dict
        """
        if not query or not query.strip():
            return []

        try:
            query_embedding = self.embedding_service.embed_query(query)
        except Exception as exc:
            logger.warning("Embedding generation failed for query: %s", exc)
            return []

        fetch_k = max(top_k, min(top_k * 8, 50))

        try:
            result = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=fetch_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorDatabaseError(
                f"Unable to query RAG collection: {exc}"
            ) from exc

        documents = result.get("documents", [[]])
        metadatas = result.get("metadatas", [[]])
        distances = result.get("distances", [[]])

        if not documents or not documents[0]:
            return []

        items: List[dict[str, Any]] = []
        for document_text, metadata, distance in zip(
            documents[0], metadatas[0], distances[0]
        ):
            similarity_score = max(0.0, round(1.0 - float(distance), 4))
            if similarity_score < similarity_threshold:
                continue
            items.append(self._build_item(document_text, metadata, similarity_score))

        items.extend(self._metadata_candidates(query))
        return self._rerank_and_diversify(query, items, top_k, similarity_threshold)

    def _build_item(
        self,
        document_text: str,
        metadata: dict[str, Any],
        similarity_score: float,
    ) -> dict[str, Any]:
        scheme_name = metadata.get("scheme_name", "")
        source_file = metadata.get("source_file", "")
        normalized_scheme = metadata.get("normalized_scheme_name") or _canonical_scheme_key(
            scheme_name, source_file
        )
        item = {
            "text": document_text,
            "scheme_name": scheme_name,
            "source_file": source_file,
            "page_number": metadata.get("page_number"),
            "score": similarity_score,
            "section_name": metadata.get("section_name", ""),
            "document_type": metadata.get("document_type", "government_scheme"),
            "metadata": metadata,
            "_scheme_key": normalized_scheme,
        }
        return item

    def _metadata_candidates(self, query: str) -> List[dict[str, Any]]:
        """Find exact/name/domain candidates from metadata, independent of vector rank."""
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        candidates: List[dict[str, Any]] = []
        for chunk in self._load_all_chunks():
            scheme_text = " ".join(
                [
                    chunk.get("scheme_name", ""),
                    chunk.get("source_file", ""),
                    chunk.get("text", "")[:500],
                ]
            )
            scheme_tokens = _tokens(scheme_text)
            if not scheme_tokens:
                continue

            overlap = query_tokens & scheme_tokens
            domains = _query_domains(query_tokens)
            domain_hit = any(scheme_tokens & _DOMAIN_TERMS[domain] for domain in domains)
            if overlap or domain_hit:
                scheme_match_score = self._scheme_name_match_score(query, chunk)
                if scheme_match_score >= 0.12:  # Strong exact match (query subset of scheme)
                    boost = 0.85
                elif scheme_match_score > 0:
                    boost = 0.15
                elif domain_hit:
                    boost = 0.10
                elif overlap:
                    boost = 0.05
                else:
                    boost = 0.0
                candidates.append({**chunk, "score": max(chunk.get("score", 0.0), boost)})
        return candidates

    def _load_all_chunks(self) -> List[dict[str, Any]]:
        if self._all_chunks_cache is not None:
            return self._all_chunks_cache
        try:
            result = self.collection.get(include=["documents", "metadatas"])
        except Exception:
            self._all_chunks_cache = []
            return self._all_chunks_cache

        if not isinstance(result, dict):
            self._all_chunks_cache = []
            return self._all_chunks_cache

        documents = result.get("documents", []) or []
        metadatas = result.get("metadatas", []) or []
        chunks: List[dict[str, Any]] = []
        for document_text, metadata in zip(documents, metadatas):
            if not isinstance(metadata, dict):
                continue
            chunks.append(self._build_item(document_text or "", metadata, 0.0))
        self._all_chunks_cache = chunks
        return chunks

    def _rerank_and_diversify(
        self,
        query: str,
        items: List[dict[str, Any]],
        top_k: int,
        similarity_threshold: float,
    ) -> List[dict[str, Any]]:
        if not items:
            return []

        best_by_chunk: Dict[str, dict[str, Any]] = {}
        for item in items:
            metadata = item.get("metadata", {})
            chunk_id = metadata.get("chunk_id") or (
                item.get("source_file", ""),
                item.get("page_number"),
                item.get("text", "")[:120],
            )
            current = best_by_chunk.get(str(chunk_id))
            if current is None or item.get("score", 0.0) > current.get("score", 0.0):
                best_by_chunk[str(chunk_id)] = item

        scored = []
        for item in best_by_chunk.values():
            final_score = self._combined_score(query, item)
            if final_score < similarity_threshold:
                continue
            scored.append((final_score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        selected: List[dict[str, Any]] = []
        seen_scheme_keys: set[str] = set()
        for final_score, item in scored:
            item = {**item, "score": round(max(item.get("score", 0.0), final_score), 4)}
            scheme_key = item.get("_scheme_key") or _canonical_scheme_key(
                item.get("scheme_name", ""), item.get("source_file", "")
            )
            if scheme_key and scheme_key in seen_scheme_keys:
                continue
            selected.append(item)
            if scheme_key:
                seen_scheme_keys.add(scheme_key)
            if len(selected) >= top_k:
                break

        for item in selected:
            item.pop("_scheme_key", None)
        return selected[:top_k]

    def _combined_score(self, query: str, item: dict[str, Any]) -> float:
        semantic = float(item.get("score", 0.0) or 0.0)
        exact = self._scheme_name_match_score(query, item)
        domain = self._domain_match_score(query, item)
        keyword = self._keyword_overlap_score(query, item)
        return min(1.0, semantic + exact + domain + keyword)

    def _scheme_name_match_score(self, query: str, item: dict[str, Any]) -> float:
        query_norm = _normalize_for_match(query)
        scheme_norm = _normalize_for_match(item.get("scheme_name", ""))
        source_norm = _normalize_for_match(item.get("source_file", ""))
        if not query_norm or not scheme_norm:
            return 0.0

        scheme_tokens = _tokens(scheme_norm)
        query_tokens = _tokens(query_norm)
        if scheme_norm in query_norm or source_norm in query_norm:
            return 0.15
        if query_tokens and query_tokens <= scheme_tokens:
            return 0.12
        if len(query_tokens & scheme_tokens) >= 2:
            return 0.08
        return 0.0

    def _domain_match_score(self, query: str, item: dict[str, Any]) -> float:
        query_tokens = _tokens(query)
        domains = _query_domains(query_tokens)
        if not domains:
            return 0.0
        item_text = " ".join(
            [
                item.get("scheme_name", ""),
                item.get("source_file", ""),
                item.get("text", "")[:1200],
            ]
        )
        item_tokens = _tokens(item_text)
        hits = sum(1 for domain in domains if item_tokens & _DOMAIN_TERMS[domain])
        # Increased from 0.08 to 0.18 per hit to allow domain evidence to overcome
        # moderate semantic gaps when query has strong domain signals.
        return min(0.30, hits * 0.18)

    def _keyword_overlap_score(self, query: str, item: dict[str, Any]) -> float:
        query_tokens = _tokens(query)
        if not query_tokens:
            return 0.0
        item_text = " ".join(
            [
                item.get("scheme_name", ""),
                item.get("source_file", ""),
                item.get("text", "")[:1200],
            ]
        )
        item_tokens = _tokens(item_text)
        overlap = query_tokens & item_tokens
        return min(0.04, 0.01 * len(overlap))


@lru_cache(maxsize=1)
def get_scheme_retrieval_service() -> SchemeRetrievalService:
    """Return the shared singleton SchemeRetrievalService instance."""
    return SchemeRetrievalService()
