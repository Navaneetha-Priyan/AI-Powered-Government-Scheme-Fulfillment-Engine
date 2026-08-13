"""RagResponseService — Government Scheme RAG answer generation.

This service takes a user query, retrieves relevant chunks via
``SchemeRetrievalService``, constructs a grounded context, and generates a
response using the existing ``LLMClient`` (Ollama).

Safety rules (Phase 13):
- The LLM is instructed to use ONLY the retrieved document context.
- The LLM must NOT invent eligibility criteria, benefits, required documents,
  or application procedures.
- If the answer cannot be found in the retrieved documents, the service
  clearly states that the available documents do not contain enough information.
- RAG provides policy information only — citizen-specific eligibility remains
  with the existing eligibility/recommendation engine.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import LLMUnavailableError
from app.schemas.rag import RagQueryResponse, RagSource
from app.services.llm_client import LLMClient, get_llm_client
from app.services.scheme_retrieval_service import (
    SchemeRetrievalService,
    get_scheme_retrieval_service,
)

logger = get_logger(__name__)


class RagResponseService:
    """Generate grounded RAG responses from government-scheme PDFs.

    Flow:
        User Query
        → SchemeRetrievalService.retrieve()
        → Construct grounded context from retrieved chunks
        → LLMClient.chat() with safety-focused system prompt
        → Grounded response with source attribution
    """

    def __init__(
        self,
        retrieval_service: Optional[SchemeRetrievalService] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.retrieval_service = retrieval_service or get_scheme_retrieval_service()
        self.llm_client = llm_client or get_llm_client()

    # ── Public API ──────────────────────────────────────────────────────────

    def answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        language: Optional[str] = None,
    ) -> RagQueryResponse:
        """Generate a grounded RAG response for a government-scheme query.

        :param query: The user's natural-language question.
        :param top_k: Number of chunks to retrieve (defaults to RAG_TOP_K).
        :param language: Preferred response language (e.g. 'en', 'ta').
        :return: A ``RagQueryResponse`` with answer, sources, and metadata.
        """
        if not query or not query.strip():
            return RagQueryResponse(
                query=query or "",
                answer="",
                sources=[],
                language=language,
                confidence=0.0,
                is_grounded=False,
                message="Query is empty.",
            )

        k = top_k or settings.RAG_TOP_K
        threshold = settings.RAG_SIMILARITY_THRESHOLD

        # 1) Retrieve relevant chunks.
        chunks = self.retrieval_service.retrieve(
            query=query,
            top_k=k,
            similarity_threshold=threshold,
        )

        if not chunks:
            return RagQueryResponse(
                query=query,
                answer=self._no_information_answer(language),
                sources=[],
                language=language,
                confidence=0.0,
                is_grounded=False,
                message=(
                    "The available government scheme documents do not contain "
                    "enough information to answer this question."
                ),
            )

        # 2) Construct grounded context.
        context = self._build_context(chunks)

        # 3) Generate response via the existing LLM client.
        try:
            answer_text = self._generate_answer(query, context, language)
        except LLMUnavailableError as exc:
            logger.warning("LLM unavailable for RAG response: %s", exc)
            # Fall back to a summary of the retrieved chunks.
            answer_text = self._fallback_answer(chunks, language)

        # 4) Build sources list.
        sources = [
            RagSource(
                scheme_name=chunk.get("scheme_name", ""),
                source_file=chunk.get("source_file", ""),
                page_number=chunk.get("page_number"),
                score=chunk.get("score", 0.0),
                section_name=chunk.get("section_name", ""),
                document_type=chunk.get("document_type", "government_scheme"),
            )
            for chunk in chunks
        ]

        # 5) Compute confidence from retrieval scores.
        confidence = self._compute_confidence(chunks)

        return RagQueryResponse(
            query=query,
            answer=answer_text,
            sources=sources,
            language=language,
            confidence=confidence,
            is_grounded=True,
        )

    # ── Context construction ────────────────────────────────────────────────

    def _build_context(self, chunks: List[dict[str, Any]]) -> str:
        """Build a grounded context string from retrieved chunks."""
        parts: List[str] = []
        for i, chunk in enumerate(chunks, start=1):
            scheme_name = chunk.get("scheme_name", "Unknown Scheme")
            source_file = chunk.get("source_file", "unknown.pdf")
            page_number = chunk.get("page_number", "?")
            text = chunk.get("text", "").strip()
            parts.append(
                f"[Source {i}] Scheme: {scheme_name}\n"
                f"Document: {source_file}\n"
                f"Page: {page_number}\n"
                f"Content: {text}"
            )
        return "\n\n---\n\n".join(parts)

    # ── LLM prompt ──────────────────────────────────────────────────────────

    def _system_prompt(self, language: Optional[str]) -> str:
        """Build the system prompt with strict grounding instructions."""
        lang_instruction = ""
        if language and language != "unknown":
            lang_instruction = (
                f"Respond in the language requested by the user "
                f"(language code: {language}). "
            )
        else:
            lang_instruction = (
                "Respond in the same language as the user's query. "
            )

        return (
            "You are a helpful government scheme assistant. Your job is to "
            "answer the user's question using ONLY the information provided in "
            "the retrieved government document context below.\n\n"
            "CRITICAL RULES:\n"
            "1. Use ONLY the retrieved document context. Do not use any other "
            "knowledge.\n"
            "2. Do NOT invent eligibility criteria.\n"
            "3. Do NOT invent benefits.\n"
            "4. Do NOT invent required documents.\n"
            "5. Do NOT invent application procedures.\n"
            "6. If the answer cannot be found in the retrieved documents, "
            "clearly state that the available documents do not contain enough "
            "information.\n"
            "7. Do not pretend that missing information is known.\n"
            "8. If the user's question names a specific scheme, answer only "
            "from retrieved context for that same or clearly matching scheme. "
            "Do not present unrelated retrieved schemes as substitutes.\n"
            "9. Prefer simple language suitable for rural citizens.\n"
            f"{lang_instruction}"
            "10. Always cite which document and page number the information "
            "comes from.\n\n"
            "Retrieved context:\n"
            "{context}"
        )

    def _generate_answer(
        self,
        query: str,
        context: str,
        language: Optional[str],
    ) -> str:
        """Generate an answer using the existing LLM client."""
        system_prompt = self._system_prompt(language).replace(
            "{context}", context
        )
        user_message = (
            f"Answer the following question using ONLY the retrieved "
            f"government document context above.\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )

        raw = self.llm_client.chat(system_prompt, user_message)
        return raw.strip()

    # ── Fallbacks ───────────────────────────────────────────────────────────

    def _no_information_answer(self, language: Optional[str]) -> str:
        """Return a safe answer when no relevant chunks are found."""
        if language and language.startswith("ta"):
            return (
                "முறையான  authorities ஆவணங்கள் இருந்திருக்கின், இந்த "
                "கேள்விக்கு பதில் காணப்படவில்லை. தயவுக்கு மற்றொரு "
                "விஷயத்தைக் கேளுங்கள்."
            )
        return (
            "The available government scheme documents do not contain enough "
            "information to answer this question. Please try asking about a "
            "different topic or consult the official scheme website."
        )

    def _fallback_answer(
        self, chunks: List[dict[str, Any]], language: Optional[str]
    ) -> str:
        """Generate a simple answer from chunks when the LLM is unavailable."""
        parts: List[str] = []
        for chunk in chunks:
            scheme = chunk.get("scheme_name", "Unknown Scheme")
            page = chunk.get("page_number", "?")
            text = chunk.get("text", "").strip()
            parts.append(f"From {scheme} (page {page}): {text}")
        return (
            "Based on the retrieved government scheme documents:\n\n"
            + "\n\n".join(parts)
        )

    # ── Confidence ──────────────────────────────────────────────────────────

    @staticmethod
    def _compute_confidence(chunks: List[dict[str, Any]]) -> float:
        """Compute a confidence score from retrieval similarity scores."""
        if not chunks:
            return 0.0
        scores = [chunk.get("score", 0.0) for chunk in chunks]
        avg_score = sum(scores) / len(scores)
        # Scale: average similarity → confidence (0.0 to 1.0).
        return round(max(0.0, min(1.0, avg_score)), 4)


@lru_cache(maxsize=1)
def get_rag_response_service() -> RagResponseService:
    """Return the shared singleton RagResponseService instance."""
    return RagResponseService()
