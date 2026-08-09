"""Unit Tests for Mock DigiLocker Structured Document Metadata (Step 1)

Verifies that ``get_mock_documents()`` returns documents whose ``doc_metadata``
(a JSON string) contains usable, structured document data that a future
document-extraction / profile-enrichment pipeline can consume.

This test intentionally does NOT test profile enrichment — that is Step 2+.
"""
import json

from app.utils.mock_digilocker_data import get_mock_documents


def _docs_for_farmer():
    """Build mock documents for the known mock BPL farmer profile."""
    return get_mock_documents(
        citizen_id="citizen-farmer-0001",
        digilocker_record_id="rec-farmer-0001",
        aadhaar="234123456789",
        ration_card="TN1234567890",
        full_name="Selvam Murugan",
        gender="male",
        date_of_birth="1985-04-12",
        address_line1="Main Road",
        village="Periyakulam",
        taluk="Villupuram",
        district="Villupuram",
        state="Tamil Nadu",
        pincode="605602",
    )


def _find_doc(docs, doc_type):
    """Find the first document of the given type."""
    for d in docs:
        if d["document_type"] == doc_type:
            return d
    return None


def _parse_metadata(doc):
    """Parse a document's doc_metadata JSON string."""
    return json.loads(doc["doc_metadata"])


class TestStructuredAadhaarMetadata:
    """Aadhaar document exposes full_name and date_of_birth"""

    def test_aadhaar_metadata_is_usable(self):
        docs = _docs_for_farmer()
        doc = _find_doc(docs, "aadhaar")
        assert doc is not None

        meta = _parse_metadata(doc)
        assert meta["document_type"] == "aadhaar"
        data = meta["data"]
        assert data["full_name"] == "Selvam Murugan"
        assert data["date_of_birth"] == "1985-04-12"
        assert data["gender"] == "male"
        assert data["district"] == "Villupuram"


class TestStructuredLandRecordMetadata:
    """Land record exposes land_area and survey_number"""

    def test_land_record_metadata_is_usable(self):
        docs = _docs_for_farmer()
        doc = _find_doc(docs, "land_record")
        assert doc is not None

        meta = _parse_metadata(doc)
        assert meta["document_type"] == "land_record"
        data = meta["data"]
        assert data["survey_number"] == "123/2A"
        assert data["land_area"] == 2.5
        assert data["ownership_type"] == "owned"
        assert data["district"] == "Villupuram"


class TestStructuredIncomeCertificateMetadata:
    """Income certificate exposes annual_income"""

    def test_income_certificate_metadata_is_usable(self):
        docs = _docs_for_farmer()
        doc = _find_doc(docs, "income_certificate")
        assert doc is not None

        meta = _parse_metadata(doc)
        assert meta["document_type"] == "income_certificate"
        data = meta["data"]
        assert data["annual_income"] == 72000.0
        assert data["income_category"] == "bpl"
        assert data["financial_year"] == "2025-2026"


class TestStructuredMetadataInternalConsistency:
    """Metadata values stay consistent with the citizen profile / land records"""

    def test_documents_are_json_serializable(self):
        docs = _docs_for_farmer()
        for doc in docs:
            # doc_metadata must be a valid JSON string
            meta = _parse_metadata(doc)
            assert "document_type" in meta
            assert isinstance(meta["data"], dict)

    def test_farmer_id_metadata_matches_profile(self):
        docs = _docs_for_farmer()
        doc = _find_doc(docs, "farmer_id")
        assert doc is not None
        data = _parse_metadata(doc)["data"]
        assert data["farmer_id"] == "TN-FARMER-001234"
        assert data["is_farmer"] is True
        assert data["occupation"] == "Farmer"

    def test_ration_card_metadata_matches_profile(self):
        docs = _docs_for_farmer()
        doc = _find_doc(docs, "smart_ration_card")
        assert doc is not None
        data = _parse_metadata(doc)["data"]
        assert data["card_number"] == "TN1234567890"
        assert data["family_size"] == 5
        assert data["card_type"] == "BPL"
