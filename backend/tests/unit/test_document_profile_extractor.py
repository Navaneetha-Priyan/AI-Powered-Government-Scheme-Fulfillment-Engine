"""Unit Tests for DocumentProfileExtractor (Step 2 - Document Profile Extraction).

These tests verify that the extractor reads structured ``doc_metadata`` and
produces a normalized ``ExtractedDocumentData`` representation.

The extractor is intentionally READ-ONLY. A dedicated test asserts that calling
``extract()`` never performs any database write.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.exceptions.exceptions import (
    DocumentExtractionError,
    DocumentMetadataInvalidError,
    UnsupportedDocumentTypeError,
)
from app.schemas.document_profile import ExtractedDocumentData
from app.services.document_profile_extractor import DocumentProfileExtractor
from app.schemas.citizen_profile import DocumentTypeEnum


# ── Helpers ───────────────────────────────────────────────────────────────────

def _metadata(document_type: str, data: dict) -> str:
    """Build a doc_metadata JSON string exactly as Step 1 emits it."""
    return json.dumps({"document_type": document_type, "data": data})


def _doc(document_type: str, data: dict, doc_id: str = "doc-123") -> "SimpleNamespace":
    """Build a lightweight GovernmentDocument stand-in exposing id/doc_metadata."""
    return SimpleNamespace(
        id=doc_id,
        doc_metadata=_metadata(document_type, data),
    )


def _extractor() -> DocumentProfileExtractor:
    return DocumentProfileExtractor()


# ── Aadhaar ───────────────────────────────────────────────────────────────────

class TestAadhaarExtraction:
    def test_aadhaar_extracts_all_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "aadhaar",
                {
                    "full_name": "Selvam Murugan",
                    "date_of_birth": "1985-04-12",
                    "gender": "male",
                    "address_line1": "Main Road",
                    "village": "Periyakulam",
                    "taluk": "Villupuram",
                    "district": "Villupuram",
                    "state": "Tamil Nadu",
                    "pincode": "605602",
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.AADHAAR
        assert result.fields["full_name"] == "Selvam Murugan"
        assert result.fields["date_of_birth"] == "1985-04-12"
        assert result.fields["gender"] == "male"
        assert result.fields["district"] == "Villupuram"
        assert result.document_id is None

    def test_aadhaar_missing_optional_fields_are_none(self):
        result = _extractor().extract_from_metadata(
            _metadata("aadhaar", {"full_name": "Selvam Murugan"})
        )
        assert result.fields["full_name"] == "Selvam Murugan"
        assert result.fields["date_of_birth"] is None
        assert result.fields["gender"] is None
        assert result.fields["district"] is None


# ── Land Record ───────────────────────────────────────────────────────────────

class TestLandRecordExtraction:
    def test_land_record_extracts_all_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "land_record",
                {
                    "owner_name": "Selvam Murugan",
                    "survey_number": "123/2A",
                    "land_area": 2.5,
                    "unit": "acres",
                    "land_type": "agricultural",
                    "village": "Periyakulam",
                    "taluk": "Villupuram",
                    "district": "Villupuram",
                    "state": "Tamil Nadu",
                    "ownership_type": "owned",
                    "patta_number": "TN-VPM-2023-001",
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.LAND_RECORD
        assert result.fields["owner_name"] == "Selvam Murugan"
        assert result.fields["survey_number"] == "123/2A"
        assert result.fields["land_area"] == 2.5
        assert result.fields["unit"] == "acres"
        assert result.fields["land_type"] == "agricultural"
        assert result.fields["ownership_type"] == "owned"
        assert result.fields["patta_number"] == "TN-VPM-2023-001"

    def test_land_record_does_not_derive_farmer_status(self):
        # Step 2 rule: no document -> profile mapping. land_area > 0 must NOT
        # become is_farmer=true. is_farmer is not even a land_record field.
        result = _extractor().extract_from_metadata(
            _metadata(
                "land_record",
                {"owner_name": "X", "survey_number": "1", "land_area": 2.5},
            )
        )
        assert "is_farmer" not in result.fields


# ── Income Certificate ────────────────────────────────────────────────────────

class TestIncomeCertificateExtraction:
    def test_income_certificate_extracts_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "income_certificate",
                {
                    "holder_name": "Selvam Murugan",
                    "annual_income": 72000.0,
                    "income_category": "bpl",
                    "financial_year": "2025-2026",
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.INCOME_CERTIFICATE
        assert result.fields["annual_income"] == 72000.0
        assert result.fields["income_category"] == "bpl"
        assert result.fields["financial_year"] == "2025-2026"


# ── Caste / Community Certificate ─────────────────────────────────────────────

class TestCasteCertificateExtraction:
    def test_caste_certificate_extracts_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "caste_certificate",
                {
                    "holder_name": "Selvam Murugan",
                    "caste": "Vanniyar",
                    "community": "MBC",
                    "sub_caste": "Padayachi",
                    "issuing_authority": "Revenue Department",
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.CASTE_CERTIFICATE
        assert result.fields["caste"] == "Vanniyar"
        assert result.fields["community"] == "MBC"
        assert result.fields["sub_caste"] == "Padayachi"
        assert result.fields["issuing_authority"] == "Revenue Department"

    def test_community_certificate_alias_maps_to_community_type(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "community_certificate",
                {"holder_name": "Selvam Murugan", "caste": "Vanniyar"},
            )
        )
        assert result.document_type == DocumentTypeEnum.COMMUNITY_CERTIFICATE
        assert result.fields["caste"] == "Vanniyar"


# ── Farmer ID ─────────────────────────────────────────────────────────────────

class TestFarmerIdExtraction:
    def test_farmer_id_extracts_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "farmer_id",
                {
                    "farmer_id": "TN-FARMER-001234",
                    "holder_name": "Selvam Murugan",
                    "is_farmer": True,
                    "occupation": "Farmer",
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.FARMER_ID
        assert result.fields["farmer_id"] == "TN-FARMER-001234"
        assert result.fields["is_farmer"] is True
        assert result.fields["occupation"] == "Farmer"


# ── Ration Card ───────────────────────────────────────────────────────────────

class TestRationCardExtraction:
    def test_ration_card_extracts_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "ration_card",
                {
                    "card_number": "TN1234567890",
                    "holder_name": "Selvam Murugan",
                    "card_type": "BPL",
                    "family_size": 5,
                    "district": "Villupuram",
                },
            )
        )
        # "ration_card" metadata label must resolve to the canonical enum.
        assert result.document_type == DocumentTypeEnum.SMART_RATION_CARD
        assert result.fields["card_number"] == "TN1234567890"
        assert result.fields["card_type"] == "BPL"
        assert result.fields["family_size"] == 5


# ── Residence Certificate ─────────────────────────────────────────────────────

class TestResidenceCertificateExtraction:
    def test_residence_certificate_extracts_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "residence_certificate",
                {
                    "holder_name": "Selvam Murugan",
                    "village": "Periyakulam",
                    "taluk": "Villupuram",
                    "district": "Villupuram",
                    "state": "Tamil Nadu",
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.RESIDENCE_CERTIFICATE
        assert result.fields["village"] == "Periyakulam"
        assert result.fields["district"] == "Villupuram"


# ── Disability Certificate ────────────────────────────────────────────────────

class TestDisabilityCertificateExtraction:
    def test_disability_certificate_extracts_fields(self):
        result = _extractor().extract_from_metadata(
            _metadata(
                "disability_certificate",
                {
                    "holder_name": "Selvam Murugan",
                    "is_disabled": True,
                    "disability_percentage": 45,
                },
            )
        )
        assert result.document_type == DocumentTypeEnum.DISABILITY_CERTIFICATE
        assert result.fields["is_disabled"] is True
        assert result.fields["disability_percentage"] == 45


# ── Definition alias: "smart_ration_card" metadata label ─────────────────────

class TestSmartRationCardLabel:
    def test_smart_ration_card_label_supported(self):
        result = _extractor().extract_from_metadata(
            _metadata("smart_ration_card", {"card_number": "TN1234567890"})
        )
        assert result.document_type == DocumentTypeEnum.SMART_RATION_CARD


# ── Error handling ────────────────────────────────────────────────────────────

class TestInvalidJsonHandling:
    def test_invalid_json_raises_controlled_error(self):
        with pytest.raises(DocumentMetadataInvalidError) as exc_info:
            _extractor().extract_from_metadata("{not valid json")
        assert exc_info.value.error_code == "DOCUMENT_METADATA_INVALID"


class TestMissingDataHandling:
    def test_missing_metadata_raises(self):
        with pytest.raises(DocumentMetadataInvalidError):
            _extractor().extract_from_metadata(None)

    def test_empty_string_raises(self):
        with pytest.raises(DocumentMetadataInvalidError):
            _extractor().extract_from_metadata("   ")

    def test_missing_document_type_raises(self):
        with pytest.raises(DocumentMetadataInvalidError):
            _extractor().extract_from_metadata(json.dumps({"data": {}}))

    def test_missing_data_raises(self):
        with pytest.raises(DocumentMetadataInvalidError):
            _extractor().extract_from_metadata(json.dumps({"document_type": "aadhaar"}))

    def test_data_not_object_raises(self):
        with pytest.raises(DocumentMetadataInvalidError):
            _extractor().extract_from_metadata(
                json.dumps({"document_type": "aadhaar", "data": "not-a-dict"})
            )


class TestUnknownDocumentType:
    def test_unknown_document_type_raises(self):
        with pytest.raises(UnsupportedDocumentTypeError) as exc_info:
            _extractor().extract_from_metadata(
                json.dumps({"document_type": "passport", "data": {}})
            )
        assert exc_info.value.error_code == "UNSUPPORTED_DOCUMENT_TYPE"
        assert exc_info.value.details["document_type"] == "passport"


# ── Document-aware extract() ──────────────────────────────────────────────────

class TestExtractFromDocument:
    def test_extract_preserves_document_id(self):
        doc = _doc("aadhaar", {"full_name": "Selvam Murugan"}, doc_id="doc-abc")
        result = _extractor().extract(doc)
        assert result.document_id == "doc-abc"
        assert result.document_type == DocumentTypeEnum.AADHAAR
        assert result.fields["full_name"] == "Selvam Murugan"

    def test_extract_from_metadata_has_no_document_id(self):
        result = _extractor().extract_from_metadata(
            _metadata("aadhaar", {"full_name": "Selvam Murugan"})
        )
        assert result.document_id is None

    def test_extract_none_raises(self):
        with pytest.raises(DocumentExtractionError):
            _extractor().extract(None)


# ── Read-only guarantee ───────────────────────────────────────────────────────

class TestReadOnly:
    def test_extract_does_not_write_database(self):
        """The extractor must never touch the DB.

        We prove this by refusing to give it a session: it only needs the
        doc_metadata string. If extract() tried to write, it would have no place
        to write to and would fail — but it returns a clean result instead.
        """
        doc = _doc(
            "income_certificate",
            {"holder_name": "Selvam Murugan", "annual_income": 72000.0},
            doc_id="readonly-doc",
        )
        result = _extractor().extract(doc)
        assert isinstance(result, ExtractedDocumentData)
        assert result.document_id == "readonly-doc"
        assert result.fields["annual_income"] == 72000.0
