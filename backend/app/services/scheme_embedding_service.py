"""Embedding service for Module 3 scheme chunks and semantic queries."""
from __future__ import annotations

import hashlib
import math
import threading
from functools import lru_cache
from typing import List

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import EmbeddingGenerationFailedError

logger = get_logger(__name__)


class SchemeEmbeddingService:
    """Generate embeddings with Sentence Transformers and a deterministic fallback."""

    def __init__(self, model_name: str | None = None, dimension: int = 1024):
        self.model_name = model_name or settings.RAG_EMBEDDING_MODEL
        self.dimension = dimension
        self._model = None
        self._fallback_mode = False
        self._load_lock = threading.Lock()
        self._warmed_up = False

    def _load_model(self) -> None:
        if self._model is not None or self._fallback_mode:
            return

        with self._load_lock:
            # Double-checked locking: another thread may have loaded
            # the model while this thread waited on the lock.
            if self._model is not None or self._fallback_mode:
                return
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info("Loaded embedding model: %s", self.model_name)
            except Exception as exc:
                self._fallback_mode = True
                logger.warning("Falling back to deterministic embeddings: %s", exc)

    def warm_up(self) -> None:
        """Pre-load the embedding model outside the request path.

        Called once at application startup (in a worker thread) so the
        FIRST recommendation request does not pay the ~30s cold-start
        cost of downloading/loading ``BAAI/bge-m3`` while the mobile
        client is waiting with a limited receive timeout.
        """
        if self._warmed_up:
            return
        self._load_model()
        if self._model is not None:
            try:
                # Encode a tiny query so lazy backends (tokenizer,
                # pooling layers) finish initialising now, not per-request.
                self._model.encode(
                    ["warmup"],
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Embedding warm-up encode failed: %s", exc)
        self._warmed_up = True

    @property
    def is_ready(self) -> bool:
        """True once the model (or deterministic fallback) is initialised."""
        return self._model is not None or self._fallback_mode

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        self._load_model()

        if self._model is not None:
            try:
                vectors = self._model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]
            except Exception as exc:
                raise EmbeddingGenerationFailedError(str(exc)) from exc

        return [self._fallback_embedding(text) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        embeddings = self.embed_texts([query])
        return embeddings[0] if embeddings else self._fallback_embedding(query)

    def _fallback_embedding(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            tokens = [text.lower() or "empty"]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 4):
                index = int.from_bytes(digest[offset : offset + 4], "big", signed=False) % self.dimension
                vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]


@lru_cache(maxsize=1)
def get_scheme_embedding_service() -> SchemeEmbeddingService:
    return SchemeEmbeddingService()


    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        self._load_model()

        if self._model is not None:
            try:
                vectors = self._model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]
            except Exception as exc:
                raise EmbeddingGenerationFailedError(str(exc)) from exc

        return [self._fallback_embedding(text) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        embeddings = self.embed_texts([query])
        return embeddings[0] if embeddings else self._fallback_embedding(query)

    def _fallback_embedding(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            tokens = [text.lower() or "empty"]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 4):
                index = int.from_bytes(digest[offset : offset + 4], "big", signed=False) % self.dimension
                vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]


@lru_cache(maxsize=1)
def get_scheme_embedding_service() -> SchemeEmbeddingService:
    return SchemeEmbeddingService()
