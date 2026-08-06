"""Unit tests for the Module 3 scheme knowledge base pipeline."""
from types import SimpleNamespace

from app.services.scheme_processing_service import SchemeProcessingService
from app.services.vector_store_service import VectorStoreService


class FakeEmbeddingService:
    def embed_query(self, query):
        return [1.0, 0.0, 0.0]


class FakeCollection:
    def __init__(self):
        self.rows = {}

    def upsert(self, ids, embeddings, documents, metadatas):
        for chunk_id, document, metadata in zip(ids, documents, metadatas):
            self.rows[chunk_id] = {"document": document, "metadata": metadata}

    def delete(self, ids=None, where=None):
        if ids:
            for chunk_id in ids:
                self.rows.pop(chunk_id, None)
        elif where:
            for chunk_id, row in list(self.rows.items()):
                if all(row["metadata"].get(key) == value for key, value in where.items()):
                    self.rows.pop(chunk_id, None)

    def query(self, query_embeddings=None, n_results=5, where=None, include=None):
        documents = []
        metadatas = []
        distances = []
        for row in self.rows.values():
            if where and any(row["metadata"].get(key) != value for key, value in where.items()):
                continue
            documents.append(row["document"])
            metadatas.append(row["metadata"])
            distances.append(0.02)
        return {
            "documents": [documents[:n_results]],
            "metadatas": [metadatas[:n_results]],
            "distances": [distances[:n_results]],
        }


def test_scheme_processing_service_chunks_sections():
    service = SchemeProcessingService()
    chunks = service.build_chunks(
        "scheme-1",
        "document-1",
        [
            {
                "page_number": 1,
                "text": "ELIGIBILITY\nSmall and marginal farmers are eligible.\n\nBENEFITS:\nCash support for crop loss.",
            }
        ],
    )

    assert len(chunks) >= 2
    assert chunks[0].section_name == "ELIGIBILITY"
    assert chunks[0].token_count > 0
    assert all(chunk.scheme_id == "scheme-1" for chunk in chunks)


def test_vector_store_service_search_returns_structured_results(monkeypatch):
    fake_collection = FakeCollection()
    monkeypatch.setattr(VectorStoreService, "_get_collection", staticmethod(lambda: fake_collection))

    service = VectorStoreService(embedding_service=FakeEmbeddingService())
    fake_collection.upsert(
        ids=["chunk-1"],
        embeddings=[[1.0, 0.0, 0.0]],
        documents=["Income support for farmers affected by flood"],
        metadatas=[
            {
                "scheme_id": "scheme-1",
                "scheme_name": "PM Kisan Support",
                "category": "agriculture",
                "department": "Agriculture Department",
                "benefits": "Annual income support",
                "document_id": "document-1",
                "page_number": 1,
                "section": "Benefits",
                "is_deleted": False,
            }
        ],
    )

    results = service.search("support for farmers", limit=5)

    assert len(results) == 1
    assert results[0]["scheme_name"] == "PM Kisan Support"
    assert results[0]["similarity_score"] > 0
    assert results[0]["matched_content"] == "Income support for farmers affected by flood"
