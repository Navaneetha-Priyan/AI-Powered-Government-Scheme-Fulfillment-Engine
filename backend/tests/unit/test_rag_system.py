"""Unit tests for the Government Scheme RAG system.

Covers:
1. PDF discovery
2. PDF text extraction (via existing PdfTextExtractor)
3. Chunk generation
4. Metadata generation
5. Embedding generation
6. ChromaDB insertion
7. Retrieval
8. Empty query handling
9. No-result / low-relevance handling
10. RAG response generation
11. API request/response contract
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.schemas.rag import RagQueryRequest, RagQueryResponse, RagSource
from app.services.scheme_retrieval_service import (
    SchemeRetrievalService,
    _derive_scheme_name,
    _normalize_for_match,
)
from app.services.rag_response_service import RagResponseService
from scripts.ingest_schemes import discover_pdfs, chunk_text


# ── 1. PDF Discovery ────────────────────────────────────────────────────────

class TestPdfDiscovery:
    def test_discovers_pdfs_in_directory(self, tmp_path: Path):
        """discover_pdfs should find all .pdf files in a directory."""
        (tmp_path / "scheme_a.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "scheme_b.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "not_a_pdf.txt").write_text("hello")
        pdfs = discover_pdfs(str(tmp_path))
        assert len(pdfs) == 2
        assert all(p.suffix == ".pdf" for p in pdfs)

    def test_returns_empty_for_nonexistent_directory(self):
        pdfs = discover_pdfs("/nonexistent/path/that/does/not/exist")
        assert pdfs == []

    def test_returns_empty_for_empty_directory(self, tmp_path: Path):
        pdfs = discover_pdfs(str(tmp_path))
        assert pdfs == []

    def test_ignores_subdirectories(self, tmp_path: Path):
        """discover_pdfs should only find PDFs in the top-level directory."""
        (tmp_path / "top.pdf").write_bytes(b"%PDF-1.4")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.pdf").write_bytes(b"%PDF-1.4")
        pdfs = discover_pdfs(str(tmp_path))
        assert len(pdfs) == 1
        assert pdfs[0].name == "top.pdf"


# ── 2. PDF Text Extraction ──────────────────────────────────────────────────

class TestPdfTextExtraction:
    def test_extracts_text_from_text_based_pdf(self, tmp_path: Path):
        """PdfTextExtractor should extract text from a text-based PDF."""
        from tests.test_document_helpers import create_valid_text_pdf

        pdf = create_valid_text_pdf(tmp_path / "test.pdf")
        from app.services.pdf_text_extractor import PdfTextExtractor

        extractor = PdfTextExtractor()
        text = extractor.extract(str(pdf))
        assert "Test Citizen" in text
        assert "--- Page 1 ---" in text

    def test_raises_for_missing_file(self):
        from app.services.pdf_text_extractor import PdfTextExtractor
        from app.exceptions.exceptions import DocumentTextExtractionError

        extractor = PdfTextExtractor()
        with pytest.raises(DocumentTextExtractionError):
            extractor.extract("nonexistent.pdf")


# ── 3. Chunk Generation ─────────────────────────────────────────────────────

class TestChunkGeneration:
    def test_short_text_returns_single_chunk(self):
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_split(self):
        text = "A" * 500 + " " + "B" * 500
        chunks = chunk_text(text, chunk_size=300, chunk_overlap=50)
        assert len(chunks) >= 2

    def test_empty_text_returns_empty_list(self):
        chunks = chunk_text("", chunk_size=300, chunk_overlap=50)
        assert chunks == []

    def test_whitespace_only_text_returns_empty_list(self):
        chunks = chunk_text("   \n\t  ", chunk_size=300, chunk_overlap=50)
        assert chunks == []

    def test_overlap_is_respected(self):
        text = "Sentence one. " + "Sentence two. " * 50
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=30)
        assert len(chunks) >= 2
        # Each chunk should be non-empty.
        assert all(len(c) > 0 for c in chunks)

    def test_chunks_do_not_exceed_chunk_size_by_much(self):
        text = "Word " * 200
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        for chunk in chunks:
            # Allow some slack for boundary detection.
            assert len(chunk) <= 120


# ── 4. Metadata Generation ──────────────────────────────────────────────────

class TestMetadataGeneration:
    def test_derive_scheme_name_from_filename(self):
        name = _derive_scheme_name("PM_Kisan_Samman_Nidhi.pdf")
        assert name == "PM Kisan Samman Nidhi"

    def test_derive_scheme_name_with_hyphens(self):
        name = _derive_scheme_name("pm-kisan-samman-nidhi.pdf")
        assert name == "pm kisan samman nidhi"

    def test_derive_scheme_name_strips_version_suffix(self):
        name = _derive_scheme_name("some_scheme_v2.pdf")
        assert "v2" not in name

    def test_derive_scheme_name_fallback(self):
        name = _derive_scheme_name("document.pdf")
        assert name == "document"

    def test_chunk_metadata_contains_required_fields(self):
        """Chunks created by the ingestion pipeline should have all required metadata."""
        from uuid import uuid4

        chunk = {
            "chunk_id": str(uuid4()),
            "text": "Sample text",
            "scheme_name": "Test Scheme",
            "source_file": "test.pdf",
            "page_number": 1,
            "document_type": "government_scheme",
            "section_name": "",
        }
        assert chunk["document_type"] == "government_scheme"
        assert chunk["source_file"] == "test.pdf"
        assert chunk["page_number"] == 1
        assert chunk["scheme_name"] == "Test Scheme"


# ── 5. Embedding Generation ─────────────────────────────────────────────────

class TestEmbeddingGeneration:
    def test_embed_query_returns_vector(self):
        from app.services.scheme_embedding_service import SchemeEmbeddingService

        service = SchemeEmbeddingService()
        embedding = service.embed_query("What schemes are available for farmers?")
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(v, float) for v in embedding)

    def test_embed_texts_returns_list_of_vectors(self):
        from app.services.scheme_embedding_service import SchemeEmbeddingService

        service = SchemeEmbeddingService()
        texts = ["First text", "Second text", "Third text"]
        embeddings = service.embed_texts(texts)
        assert len(embeddings) == 3
        assert all(len(e) > 0 for e in embeddings)

    def test_embed_empty_texts_returns_empty(self):
        from app.services.scheme_embedding_service import SchemeEmbeddingService

        service = SchemeEmbeddingService()
        embeddings = service.embed_texts([])
        assert embeddings == []

    def test_fallback_embedding_is_deterministic(self):
        from app.services.scheme_embedding_service import SchemeEmbeddingService

        service = SchemeEmbeddingService()
        emb1 = service._fallback_embedding("test text")
        emb2 = service._fallback_embedding("test text")
        assert emb1 == emb2


# ── 6. ChromaDB Insertion ───────────────────────────────────────────────────

class TestChromaDbInsertion:
    def test_add_chunks_returns_count(self):
        """add_chunks should return the number of chunks added."""
        mock_collection = MagicMock()
        mock_collection.upsert.return_value = None

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService()
            chunks = [
                {
                    "chunk_id": "test-1",
                    "text": "Sample text 1",
                    "scheme_name": "Test Scheme",
                    "source_file": "test.pdf",
                    "page_number": 1,
                    "document_type": "government_scheme",
                    "section_name": "",
                },
                {
                    "chunk_id": "test-2",
                    "text": "Sample text 2",
                    "scheme_name": "Test Scheme",
                    "source_file": "test.pdf",
                    "page_number": 2,
                    "document_type": "government_scheme",
                    "section_name": "",
                },
            ]
            embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            count = service.add_chunks(chunks, embeddings)
            assert count == 2
            mock_collection.upsert.assert_called_once()

    def test_add_empty_chunks_returns_zero(self):
        mock_collection = MagicMock()
        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService()
            count = service.add_chunks([], [])
            assert count == 0
            mock_collection.upsert.assert_not_called()

    def test_delete_all_returns_count(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["a", "b", "c"]}
        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService()
            count = service.delete_all()
            assert count == 3
            mock_collection.delete.assert_called_once_with(ids=["a", "b", "c"])


# ── 7. Retrieval ────────────────────────────────────────────────────────────

class TestRetrieval:
    def test_retrieve_returns_structured_results(self):
        """retrieve should return results with all required fields."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["Relevant chunk text"]],
            "metadatas": [[{
                "scheme_name": "PM Kisan",
                "source_file": "pm_kisan.pdf",
                "page_number": 3,
                "document_type": "government_scheme",
                "section_name": "Eligibility",
                "chunk_id": "test-1",
            }]],
            "distances": [[0.15]],
        }

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("farmer schemes", top_k=5)

            assert len(results) == 1
            result = results[0]
            assert result["text"] == "Relevant chunk text"
            assert result["scheme_name"] == "PM Kisan"
            assert result["source_file"] == "pm_kisan.pdf"
            assert result["page_number"] == 3
            # Score includes semantic (0.85) + domain bonus (0.18 for agriculture) = 1.0 (capped)
            assert result["score"] == 1.0
            assert result["document_type"] == "government_scheme"

    def test_retrieve_returns_empty_for_empty_query(self):
        service = SchemeRetrievalService()
        results = service.retrieve("", top_k=5)
        assert results == []

    def test_retrieve_returns_empty_for_whitespace_query(self):
        service = SchemeRetrievalService()
        results = service.retrieve("   ", top_k=5)
        assert results == []

    def test_retrieve_filters_by_threshold(self):
        """Chunks below the similarity threshold should be filtered out."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["High score chunk", "Low score chunk"]],
            "metadatas": [[
                {"scheme_name": "A", "source_file": "a.pdf", "page_number": 1,
                 "document_type": "government_scheme", "section_name": "", "chunk_id": "1"},
                {"scheme_name": "B", "source_file": "b.pdf", "page_number": 2,
                 "document_type": "government_scheme", "section_name": "", "chunk_id": "2"},
            ]],
            "distances": [[0.1, 0.9]],  # scores: 0.9 and 0.1
        }

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("query", top_k=5, similarity_threshold=0.5)
            # Only the high-score chunk (0.9) should pass the threshold.
            assert len(results) == 1
            assert results[0]["score"] == 0.9

    def test_exact_scheme_name_match_prioritizes_metadata_candidate(self):
        """PM Kisan metadata match should outrank unrelated semantic chunks."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["Generic maternity benefit text"]],
            "metadatas": [[{
                "scheme_name": "Pradhan Mantri Matru Vandana Yojana PMMVY",
                "source_file": "pmmvy.pdf",
                "page_number": 1,
                "document_type": "government_scheme",
                "section_name": "",
                "chunk_id": "pmmvy-1",
            }]],
            "distances": [[0.05]],  # high semantic score for an irrelevant chunk
        }
        mock_collection.get.return_value = {
            "documents": [
                "Eligibility: Small and marginal farmers. Benefits: Income support."
            ],
            "metadatas": [{
                "scheme_name": "PM Kisan Samman Nidhi",
                "source_file": "PM_Kisan_Samman_Nidhi.pdf",
                "page_number": 1,
                "document_type": "government_scheme",
                "section_name": "Benefits",
                "chunk_id": "pm-kisan-1",
            }],
        }

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("PM Kisan scheme", top_k=3)
            assert results[0]["scheme_name"] == "PM Kisan Samman Nidhi"

    def test_farmer_domain_reranking_prioritizes_agriculture_schemes(self):
        """Farmer queries should lift agriculture/farmer metadata signals."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[
                "Maternity support for pregnant women.",
                "Irrigation and water use efficiency for farmers and crops.",
            ]],
            "metadatas": [[
                {"scheme_name": "PMMVY", "source_file": "pmmvy.pdf",
                 "page_number": 1, "document_type": "government_scheme",
                 "section_name": "", "chunk_id": "pmmvy-1"},
                {"scheme_name": "Pradhan Mantri Krishi Sinchayee Yojana PMKSY",
                 "source_file": "pmksy.pdf", "page_number": 1,
                 "document_type": "government_scheme", "section_name": "",
                 "chunk_id": "pmksy-1"},
            ]],
            "distances": [[0.12, 0.28]],  # PMMVY starts higher semantically
        }
        mock_collection.get.return_value = {"documents": [], "metadatas": []}

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("government schemes for farmers", top_k=2)
            assert results[0]["scheme_name"] == "Pradhan Mantri Krishi Sinchayee Yojana PMKSY"

    def test_retrieve_suppresses_duplicate_scheme_versions(self):
        """Multiple PDF versions of one scheme should not consume top-k."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[
                "National Agriculture Market for farmers.",
                "National Agriculture Market directory.",
                "National Agriculture Market trading portal.",
                "Micro irrigation support for farmers.",
            ]],
            "metadatas": [[
                {"scheme_name": "e NAM National Agriculture Market",
                 "source_file": "e-NAM_National_Agriculture_Market.pdf",
                 "page_number": 1, "document_type": "government_scheme",
                 "section_name": "", "chunk_id": "enam-1"},
                {"scheme_name": "e NAM National Agriculture Market 2",
                 "source_file": "e-NAM_National_Agriculture_Market_2.pdf",
                 "page_number": 1, "document_type": "government_scheme",
                 "section_name": "", "chunk_id": "enam-2"},
                {"scheme_name": "e NAM National Agriculture Market 3",
                 "source_file": "e-NAM_National_Agriculture_Market_3.pdf",
                 "page_number": 1, "document_type": "government_scheme",
                 "section_name": "", "chunk_id": "enam-3"},
                {"scheme_name": "Pradhan Mantri Krishi Sinchayee Yojana PMKSY",
                 "source_file": "pmksy.pdf", "page_number": 1,
                 "document_type": "government_scheme", "section_name": "",
                 "chunk_id": "pmksy-1"},
            ]],
            "distances": [[0.05, 0.06, 0.07, 0.18]],
        }
        mock_collection.get.return_value = {"documents": [], "metadatas": []}

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("agriculture schemes for farmers", top_k=3)
            schemes = [result["scheme_name"] for result in results]
            assert len([scheme for scheme in schemes if "National Agriculture Market" in scheme]) == 1
            assert "Pradhan Mantri Krishi Sinchayee Yojana PMKSY" in schemes

    def test_normalize_for_match_preserves_tamil_unicode(self):
        """_normalize_for_match must keep Tamil characters, not strip them."""
        result = _normalize_for_match("விவசாயிகளுக்கு அரசு திட்டம்")
        assert "விவசாயிகளுக்கு" in result
        assert "அரசு" in result
        assert "திட்டம்" in result

    def test_normalize_for_match_preserves_tanglish(self):
        """_normalize_for_match must keep Tanglish/Latin characters."""
        result = _normalize_for_match("Enakku farmer scheme edhavadhu irukka")
        assert "enakku" in result
        assert "farmer" in result
        assert "scheme" in result
        assert "irukka" in result

    def test_heuristic_weights_do_not_overwhelm_semantic_score(self):
        """Heuristic bonuses should not push low-semantic chunks above high-semantic ones."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["Low relevance text", "High relevance agriculture text"]],
            "metadatas": [[
                {"scheme_name": "Unrelated Scheme", "source_file": "unrelated.pdf",
                 "page_number": 1, "document_type": "government_scheme",
                 "section_name": "", "chunk_id": "unrelated-1"},
                {"scheme_name": "PM Kisan Samman Nidhi", "source_file": "pm_kisan.pdf",
                 "page_number": 1, "document_type": "government_scheme",
                 "section_name": "Benefits", "chunk_id": "pm-kisan-1"},
            ]],
            "distances": [[0.40, 0.05]],  # semantic: 0.60 and 0.95
        }
        mock_collection.get.return_value = {"documents": [], "metadatas": []}

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("farmer scheme benefits", top_k=2)
            assert results[0]["scheme_name"] == "PM Kisan Samman Nidhi"
            assert results[0]["score"] > results[1]["score"]


# ── 8. Empty Query Handling ─────────────────────────────────────────────────

class TestEmptyQueryHandling:
    def test_empty_query_returns_empty_results(self):
        service = SchemeRetrievalService()
        results = service.retrieve("", top_k=5)
        assert results == []

    def test_whitespace_query_returns_empty_results(self):
        service = SchemeRetrievalService()
        results = service.retrieve("   \n\t  ", top_k=5)
        assert results == []


# ── 9. No-Result / Low-Relevance Handling ───────────────────────────────────

class TestNoResultHandling:
    def test_no_results_returns_empty_list(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("unrelated query", top_k=5)
            assert results == []

    def test_all_results_below_threshold_returns_empty(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["chunk1", "chunk2"]],
            "metadatas": [[
                {"scheme_name": "A", "source_file": "a.pdf", "page_number": 1,
                 "document_type": "government_scheme", "section_name": "", "chunk_id": "1"},
                {"scheme_name": "B", "source_file": "b.pdf", "page_number": 2,
                 "document_type": "government_scheme", "section_name": "", "chunk_id": "2"},
            ]],
            "distances": [[0.95, 0.98]],  # scores: 0.05 and 0.02
        }

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

        with patch.object(
            SchemeRetrievalService, "_get_or_create_collection",
            return_value=mock_collection,
        ):
            service = SchemeRetrievalService(embedding_service=mock_embedding_service)
            results = service.retrieve("query", top_k=5, similarity_threshold=0.5)
            assert results == []


# ── 10. RAG Response Generation ─────────────────────────────────────────────

class TestRagResponseGeneration:
    def test_empty_query_returns_no_information(self):
        service = RagResponseService()
        response = service.answer("")
        assert response.is_grounded is False
        assert response.confidence == 0.0
        assert len(response.sources) == 0

    def test_no_results_returns_no_information_message(self):
        """When no chunks are retrieved, the response should state that."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = []

        mock_llm = MagicMock()
        mock_llm.chat.return_value = "Some answer"

        service = RagResponseService(
            retrieval_service=mock_retrieval,
            llm_client=mock_llm,
        )
        response = service.answer("unrelated query")
        assert response.is_grounded is False
        assert response.confidence == 0.0
        assert len(response.sources) == 0
        assert "do not contain enough information" in response.answer.lower()

    def test_grounded_response_includes_sources(self):
        """When chunks are retrieved, the response should include source info."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            {
                "text": "The PM Kisan scheme provides financial assistance to farmers.",
                "scheme_name": "PM Kisan",
                "source_file": "pm_kisan.pdf",
                "page_number": 3,
                "score": 0.87,
                "section_name": "Benefits",
                "document_type": "government_scheme",
                "metadata": {},
            },
        ]

        mock_llm = MagicMock()
        mock_llm.chat.return_value = "The PM Kisan scheme provides financial assistance to farmers."

        service = RagResponseService(
            retrieval_service=mock_retrieval,
            llm_client=mock_llm,
        )
        response = service.answer("What does PM Kisan provide?")
        assert response.is_grounded is True
        assert len(response.sources) == 1
        assert response.sources[0].scheme_name == "PM Kisan"
        assert response.sources[0].source_file == "pm_kisan.pdf"
        assert response.sources[0].page_number == 3
        assert response.sources[0].score == 0.87
        assert response.confidence > 0.0

    def test_llm_unavailable_falls_back_to_chunk_summary(self):
        """When the LLM is unavailable, the service should fall back gracefully."""
        from app.exceptions.exceptions import LLMUnavailableError

        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            {
                "text": "The scheme provides financial assistance.",
                "scheme_name": "PM Kisan",
                "source_file": "pm_kisan.pdf",
                "page_number": 3,
                "score": 0.87,
                "section_name": "",
                "document_type": "government_scheme",
                "metadata": {},
            },
        ]

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = LLMUnavailableError("Ollama not running")

        service = RagResponseService(
            retrieval_service=mock_retrieval,
            llm_client=mock_llm,
        )
        response = service.answer("What does PM Kisan provide?")
        assert response.is_grounded is True
        assert "PM Kisan" in response.answer
        assert "financial assistance" in response.answer

    def test_confidence_computed_from_scores(self):
        """Confidence should be the average of retrieval scores."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            {
                "text": "Chunk 1",
                "scheme_name": "Scheme A",
                "source_file": "a.pdf",
                "page_number": 1,
                "score": 0.9,
                "section_name": "",
                "document_type": "government_scheme",
                "metadata": {},
            },
            {
                "text": "Chunk 2",
                "scheme_name": "Scheme B",
                "source_file": "b.pdf",
                "page_number": 2,
                "score": 0.7,
                "section_name": "",
                "document_type": "government_scheme",
                "metadata": {},
            },
        ]

        mock_llm = MagicMock()
        mock_llm.chat.return_value = "Answer based on chunks."

        service = RagResponseService(
            retrieval_service=mock_retrieval,
            llm_client=mock_llm,
        )
        response = service.answer("query")
        assert response.confidence == 0.8  # (0.9 + 0.7) / 2


# ── 11. API Request/Response Contract ───────────────────────────────────────

class TestRagApiContract:
    def test_rag_query_request_schema_validates(self):
        request = RagQueryRequest(query="What schemes are for farmers?")
        assert request.query == "What schemes are for farmers?"
        assert request.top_k is None
        assert request.language is None

    def test_rag_query_request_rejects_empty_query(self):
        with pytest.raises(Exception):
            RagQueryRequest(query="")

    def test_rag_query_request_accepts_top_k(self):
        request = RagQueryRequest(query="test", top_k=10)
        assert request.top_k == 10

    def test_rag_source_schema(self):
        source = RagSource(
            scheme_name="PM Kisan",
            source_file="pm_kisan.pdf",
            page_number=3,
            score=0.87,
        )
        assert source.scheme_name == "PM Kisan"
        assert source.source_file == "pm_kisan.pdf"
        assert source.page_number == 3
        assert source.score == 0.87
        assert source.document_type == "government_scheme"

    def test_rag_query_response_schema(self):
        response = RagQueryResponse(
            query="test",
            answer="test answer",
            sources=[],
            confidence=0.9,
            is_grounded=True,
        )
        assert response.query == "test"
        assert response.answer == "test answer"
        assert response.is_grounded is True
        assert response.confidence == 0.9

    def test_rag_query_response_serializes_to_dict(self):
        response = RagQueryResponse(
            query="test",
            answer="test answer",
            sources=[
                RagSource(
                    scheme_name="PM Kisan",
                    source_file="pm_kisan.pdf",
                    page_number=3,
                    score=0.87,
                )
            ],
            confidence=0.9,
            is_grounded=True,
        )
        data = response.model_dump(mode="json")
        assert data["query"] == "test"
        assert data["answer"] == "test answer"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["scheme_name"] == "PM Kisan"
