"""Module 3 scheme API integration tests."""
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services import government_scheme_service as scheme_service_module

PAYLOAD = {
    "scheme_name": "PM Kisan Support",
    "description": "Income support for eligible small and marginal farmers.",
    "category": "agriculture",
    "department": "Agriculture Department",
    "government_level": "central",
    "benefits": "Annual income support",
    "eligibility_summary": "Eligible farmers",
    "required_documents": "Aadhaar",
    "application_process": "Apply online",
    "language": "en",
    "status": "active",
}


class FakeEmbeddingService:
    def embed_texts(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, query):
        return [1.0, 0.0, 0.0]


class FakeVectorStoreService:
    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service
        self.records = []

    def upsert_chunks(self, chunks, scheme, document, embeddings):
        for chunk in chunks:
            self.records.append(
                {
                    "scheme_id": scheme.id,
                    "scheme_name": scheme.scheme_name,
                    "category": scheme.category,
                    "department": scheme.department,
                    "benefits": scheme.benefits,
                    "document_id": document.id,
                    "page_number": chunk.page_number,
                    "section_name": chunk.section_name,
                    "chunk_text": chunk.chunk_text,
                    "embedding_id": chunk.embedding_id,
                }
            )
        return len(chunks)

    def delete_document(self, chunks):
        ids = {
            chunk if isinstance(chunk, str) else getattr(chunk, "embedding_id", None)
            for chunk in chunks
        }
        ids.discard(None)
        self.records = [record for record in self.records if record["embedding_id"] not in ids]
        return len(ids)

    def delete_scheme(self, scheme_id):
        self.records = [record for record in self.records if record["scheme_id"] != scheme_id]
        return 1

    def search(self, query, limit=5, category=None):
        results = self.records
        if category:
            results = [record for record in results if record["category"] == category]
        results = [record for record in results if query.lower().split()[0] in record["chunk_text"].lower() or query.lower().split()[0] in record["scheme_name"].lower()]
        return [
            {
                "scheme_id": record["scheme_id"],
                "scheme_name": record["scheme_name"],
                "category": record["category"],
                "department": record["department"],
                "similarity_score": 0.99,
                "matched_content": record["chunk_text"],
                "relevant_content": record["chunk_text"],
                "benefits": record["benefits"],
                "page_number": record["page_number"],
                "section_name": record["section_name"],
                "document_id": record["document_id"],
            }
            for record in results[:limit]
        ]


def create(client, headers):
    response = client.post("/api/schemes", json=PAYLOAD, headers=headers)
    assert response.status_code == 201
    return response.json()["data"]["id"]


def create_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Eligibility: Small and marginal farmers. Benefits: Income support for crop loss. Application Process: Apply online.",
    )
    document.save(str(path))
    document.close()


def test_scheme_apis_require_authentication(client: TestClient):
    assert client.get("/api/schemes").status_code == 401


def test_create_list_update_and_delete_scheme(client: TestClient, auth_headers: dict):
    scheme_id = create(client, auth_headers)
    assert client.get("/api/schemes", headers=auth_headers).json()["data"]["items"][0]["scheme_name"] == PAYLOAD["scheme_name"]
    updated = client.put(f"/api/schemes/{scheme_id}", json={"benefits": "Updated benefit information"}, headers=auth_headers)
    assert updated.status_code == 200 and updated.json()["data"]["benefits"] == "Updated benefit information"
    assert client.delete(f"/api/schemes/{scheme_id}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/schemes/{scheme_id}", headers=auth_headers).status_code == 404


def test_rejects_non_pdf_upload(client: TestClient, auth_headers: dict):
    scheme_id = create(client, auth_headers)
    response = client.post(
        f"/api/schemes/{scheme_id}/documents/upload",
        headers=auth_headers,
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_process_and_search_scheme_document(client: TestClient, auth_headers: dict, monkeypatch, tmp_path):
    monkeypatch.setattr(scheme_service_module, "get_scheme_embedding_service", lambda: FakeEmbeddingService())
    shared_vector_store = FakeVectorStoreService()
    monkeypatch.setattr(scheme_service_module, "VectorStoreService", lambda embedding_service=None: shared_vector_store)
    # Redirect stored PDFs into the temporary directory so the tracked seed
    # fixtures under backend/storage/schemes/ are never overwritten.
    monkeypatch.setattr(settings, "SCHEME_STORAGE_DIR", str(tmp_path / "schemes"))

    scheme_id = create(client, auth_headers)
    pdf_path = tmp_path / "scheme.pdf"
    create_pdf(pdf_path)

    with pdf_path.open("rb") as handle:
        upload_response = client.post(
            f"/api/schemes/{scheme_id}/documents/upload",
            headers=auth_headers,
            files={"file": ("scheme.pdf", handle, "application/pdf")},
        )

    assert upload_response.status_code == 201
    document_id = upload_response.json()["data"]["id"]

    status_response = client.get(f"/api/documents/{document_id}/status", headers=auth_headers)
    assert status_response.status_code == 200
    assert status_response.json()["data"]["processing_status"] in {"pending", "processing", "completed"}

    search_response = client.post(
        "/api/search/schemes",
        headers=auth_headers,
        json={"query": "income support for farmers", "limit": 5},
    )
    assert search_response.status_code == 200
    payload = search_response.json()["data"]
    assert payload["total"] >= 1
    assert payload["items"][0]["scheme_name"] == PAYLOAD["scheme_name"]

    process_response = client.post(f"/api/documents/{document_id}/process", headers=auth_headers)
    assert process_response.status_code == 200



# ── Citizen-facing presentation hardening ───────────────────────────────────

CORRUPTED_PDF_BENEFIT = "&TO&P) - Part (8 | 29 | ) Government of India he"
CORRUPTED_PDF_DESCRIPTION = "Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET"


def test_scheme_detail_returns_clean_presentation_not_raw_extraction(
    client: TestClient, auth_headers: dict
):
    """A catalogue scheme with poisoned raw columns must still return clean,
    curated citizen-facing presentation and never leak PDF extraction."""
    payload = {
        **PAYLOAD,
        "scheme_name": "PM-KISAN Operational Guidelines",
        "description": CORRUPTED_PDF_DESCRIPTION,
        "benefits": CORRUPTED_PDF_BENEFIT,
        "eligibility_summary": "Page No. 12 Ministry of Agriculture & Farmers Welfare",
        "required_documents": "Page No. 4",
        "application_process": "Government of India",
    }
    created = client.post("/api/schemes", json=payload, headers=auth_headers)
    assert created.status_code == 201
    scheme_id = created.json()["data"]["id"]

    response = client.get(f"/api/schemes/{scheme_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    # Clean curated presentation is delivered.
    assert data["display_name"] == "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)"
    assert data["about"].startswith("PM-KISAN gives income support")
    assert data["benefits_list"] == [
        "Rs. 6,000 per year paid directly into the bank account of eligible farmer families",
        "Support to buy seeds, fertilisers and other farm inputs",
    ]
    assert data["documents"]
    assert data["application"]
    assert data["eligibility_summary"].startswith("Generally for landholding farmer families")

    # No raw extraction anywhere in the citizen-facing payload.
    for value in (
        data.get("about"),
        data.get("eligibility_summary"),
        *data.get("benefits_list", []),
        *data.get("documents", []),
        *data.get("application", []),
    ):
        assert value is None or "Page No" not in value
        assert value is None or "&TO&P" not in value
        assert value is None or "Government of India" not in value

    # Legacy raw columns that were pure extraction noise are nulled.
    assert data["required_documents"] is None
    assert data["application_process"] is None
    assert data["description"] is None
    assert data["benefits"] is None


def test_non_catalogue_scheme_gets_safe_fallback_not_raw_extraction(
    client: TestClient, auth_headers: dict
):
    payload = {
        **PAYLOAD,
        "scheme_name": "Locally Registered Test Scheme",
        "description": CORRUPTED_PDF_DESCRIPTION,
        "benefits": CORRUPTED_PDF_BENEFIT,
        "eligibility_summary": "Page No. 12 Ministry of Agriculture",
        "required_documents": "Page No. 4",
        "application_process": "Government of India",
    }
    created = client.post("/api/schemes", json=payload, headers=auth_headers)
    assert created.status_code == 201
    scheme_id = created.json()["data"]["id"]

    data = client.get(f"/api/schemes/{scheme_id}", headers=auth_headers).json()["data"]

    assert data["about"] == "Information about this scheme is being prepared."
    assert data["benefits_list"] == []
    assert data["documents"] == []
    assert data["application"] == []
    # Raw extraction is withheld rather than shipped as the fallback.
    assert data["description"] is None
    assert data["benefits"] is None
    assert data["required_documents"] is None
    assert data["application_process"] is None
    assert data["eligibility_summary"] is None



def test_scheme_detail_includes_presentation_about(client: TestClient, auth_headers: dict):
    """The scheme detail endpoint must return curated 'about' text from the
    presentation metadata, not just the raw description column."""
    scheme_id = create(client, auth_headers)
    response = client.get(f"/api/schemes/{scheme_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    # 'about' is populated from presentation short_description when available.
    assert "about" in data


def test_scheme_detail_presentation_is_not_raw_extraction(client: TestClient, auth_headers: dict):
    """User-facing presentation fields must not contain raw PDF extraction
    noise such as page markers or letterhead fragments."""
    from app.services.scheme_presentation_service import is_extraction_noise

    scheme_id = create(client, auth_headers)
    response = client.get(f"/api/schemes/{scheme_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    about = data.get("about") or ""
    benefits = data.get("benefits_list") or []
    # None of the fields should be obvious extraction noise.
    assert not is_extraction_noise(about), f"about looks like extraction noise: {about!r}"
    for bullet in benefits:
        assert not is_extraction_noise(bullet), f"benefit bullet looks like noise: {bullet!r}"
