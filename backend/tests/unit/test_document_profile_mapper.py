"""Unit Tests for DocumentProfileMapper (Step 3 - Document → Profile Mapping).

These tests verify that the mapper translates ``ExtractedDocumentData`` into
destination-aware ``MappedDocumentData`` update instructions using the existing
canonical domain field names — WITHOUT performing any database write, business
inference, or cross-document merging.

The mapper is intentionally READ-ONLY. A dedicated test constructs it with no
session and asserts it performs no writes.
"""
from __future__ import annotations

import pytest

from app.exceptions.exceptions import UnsupportedDocumentTypeError
from app.schemas.document_profile import (
    ExtractedDocumentData,
    MappedDocumentData,
)
from app.schemas.citizen_profile import DocumentTypeEnum
from app.services.document_profile_mapper import DocumentProfileMapper


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extracted(doc_type: DocumentTypeEnum, fields: dict, doc_id: str = None) -> ExtractedDocumentData:
    """Build an ExtractedDocumentData stand-in exactly as Step 2 would emit it."""
    return ExtractedDocumentData(
        document_type=doc_type,
        fields=fields,
        document_id=doc_id,
    )


def _mapper() -> DocumentProfileMapper:
    """A mapper with no DB session — it cannot write by construction."""
    return DocumentProfileMapper()


# ── Aadhaar ───────────────────────────────────────────────────────────────────

class TestAadhaarMapping:
    def test_aadhaar_maps_to_citizen_updates(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.AADHAAR,
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
        assert isinstance(result, MappedDocumentData)
        assert result.document_type == DocumentTypeEnum.AADHAAR
        assert result.citizen_updates["full_name"] == "Selvam Murugan"
        assert result.citizen_updates["date_of_birth"] == "1985-04-12"
        assert result.citizen_updates["gender"] == "male"
        assert result.citizen_updates["address_line1"] == "Main Road"
        assert result.citizen_updates["village"] == "Periyakulam"
        assert result.citizen_updates["taluk"] == "Villupuram"
        assert result.citizen_updates["district"] == "Villupuram"
        assert result.citizen_updates["state"] == "Tamil Nadu"
        assert result.citizen_updates["pincode"] == "605602"
        # Aadhaar must NOT leak into citizen_profiles.
        assert result.profile_updates == {}
        assert result.land_record_updates == []

    def test_aadhaar_drops_none_fields(self):
        result = _mapper().map(
            _extracted(DocumentTypeEnum.AADHAAR, {"full_name": "Selvam Murugan"})
        )
        assert result.citizen_updates == {"full_name": "Selvam Murugan"}
        assert "pincode" not in result.citizen_updates


# ── Land Record ───────────────────────────────────────────────────────────────

class TestLandRecordMapping:
    def test_land_record_maps_to_land_record_updates(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.LAND_RECORD,
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
        assert result.citizen_updates == {}
        assert result.profile_updates == {}
        assert len(result.land_record_updates) == 1
        land = result.land_record_updates[0]
        assert land.survey_number == "123/2A"
        assert land.land_area == 2.5
        # unit -> canonical land_area_unit
        assert land.land_area_unit == "acres"
        assert land.land_type == "agricultural"
        assert land.village == "Periyakulam"
        assert land.taluk == "Villupuram"
        assert land.district == "Villupuram"
        assert land.state == "Tamil Nadu"
        assert land.ownership_type == "owned"
        assert land.patta_number == "TN-VPM-2023-001"

    def test_land_record_does_not_infer_farmer_status(self):
        # land_area > 0 must NOT produce is_farmer. No business inference.
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.LAND_RECORD,
                {"survey_number": "1", "land_area": 2.5, "unit": "acres"},
            )
        )
        landed = result.land_record_updates[0]
        assert landed.land_area == 2.5
        assert result.profile_updates == {}
        # There is no profile/citizen is_farmer set from a land record.
        assert "is_farmer" not in result.profile_updates
        assert result.citizen_updates == {}

    def test_land_record_drops_owner_name_label(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.LAND_RECORD,
                {"owner_name": "Selvam Murugan", "survey_number": "123/2A"},
            )
        )
        land = result.land_record_updates[0]
        assert land.survey_number == "123/2A"
        assert not hasattr(land, "owner_name")


# ── Income Certificate ────────────────────────────────────────────────────────

class TestIncomeCertificateMapping:
    def test_income_certificate_maps_to_profile_updates(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                {"holder_name": "Selvam Murugan", "annual_income": 72000.0, "income_category": "bpl"},
            )
        )
        assert result.document_type == DocumentTypeEnum.INCOME_CERTIFICATE
        assert result.profile_updates["annual_income"] == 72000.0
        assert result.profile_updates["income_category"] == "bpl"
        assert result.citizen_updates == {}
        assert result.land_record_updates == []


# ── Caste / Community Certificate ─────────────────────────────────────────────

class TestCasteCertificateMapping:
    def test_caste_certificate_maps_caste_community(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.CASTE_CERTIFICATE,
                {"caste": "Vanniyar", "community": "MBC", "sub_caste": "Padayachi"},
            )
        )
        assert result.profile_updates["caste"] == "Vanniyar"
        assert result.profile_updates["community"] == "MBC"
        assert result.profile_updates["sub_caste"] == "Padayachi"


class TestCommunityCertificateAliasMapping:
    def test_community_certificate_maps_under_same_categories(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.COMMUNITY_CERTIFICATE,
                {"caste": "Nadar", "community": "BC"},
            )
        )
        assert result.document_type == DocumentTypeEnum.COMMUNITY_CERTIFICATE
        assert result.profile_updates["caste"] == "Nadar"
        assert result.profile_updates["community"] == "BC"


# ── Farmer ID ─────────────────────────────────────────────────────────────────

class TestFarmerIdMapping:
    def test_farmer_id_maps_to_profile_updates(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.FARMER_ID,
                {"farmer_id": "TN-FARMER-001234", "is_farmer": True, "occupation": "Farmer"},
            )
        )
        assert result.profile_updates["farmer_id"] == "TN-FARMER-001234"
        assert result.profile_updates["is_farmer"] is True
        assert result.profile_updates["occupation"] == "Farmer"
        assert result.citizen_updates == {}


# ── Ration Card ───────────────────────────────────────────────────────────────

class TestRationCardMapping:
    def test_ration_card_maps_card_number_and_family_size(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.SMART_RATION_CARD,
                {
                    "card_number": "TN1234567890",
                    "card_type": "BPL",
                    "family_size": 5,
                    "district": "Villupuram",
                },
            )
        )
        # card_number -> citizens.smart_ration_card
        assert result.citizen_updates["smart_ration_card"] == "TN1234567890"
        # family_size -> citizen_profiles.family_member_count
        assert result.profile_updates["family_member_count"] == 5
        # card_type has no canonical destination; must NOT be mapped.
        assert "card_type" not in result.citizen_updates
        assert "card_type" not in result.profile_updates

    def test_ration_card_ignores_unrelated_district(self):
        # district here is a ration-card issuing region, NOT the canonical
        # citizen address. The mapper does not fabricate citizen address from it.
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.SMART_RATION_CARD,
                {"card_number": "TN1234567890", "district": "Villupuram"},
            )
        )
        assert result.citizen_updates == {"smart_ration_card": "TN1234567890"}
        assert result.profile_updates == {}


# ── Residence Certificate ─────────────────────────────────────────────────────

class TestResidenceCertificateMapping:
    def test_residence_certificate_maps_to_citizen_updates(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.RESIDENCE_CERTIFICATE,
                {
                    "village": "Periyakulam",
                    "taluk": "Villupuram",
                    "district": "Villupuram",
                    "state": "Tamil Nadu",
                },
            )
        )
        assert result.citizen_updates["village"] == "Periyakulam"
        assert result.citizen_updates["taluk"] == "Villupuram"
        assert result.citizen_updates["district"] == "Villupuram"
        assert result.citizen_updates["state"] == "Tamil Nadu"
        # Address info belongs to citizens (canonical), not the profile.
        assert result.profile_updates == {}


# ── Disability Certificate ────────────────────────────────────────────────────

class TestDisabilityCertificateMapping:
    def test_disability_certificate_maps_to_profile_updates(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.DISABILITY_CERTIFICATE,
                {"is_disabled": True, "disability_percentage": 45},
            )
        )
        assert result.profile_updates["is_disabled"] is True
        assert result.profile_updates["disability_percentage"] == 45


# ── Multiple documents ────────────────────────────────────────────────────────

class TestMultipleDocumentMapping:
    def test_map_many_maps_each_independently(self):
        docs = [
            _extracted(
                DocumentTypeEnum.AADHAAR,
                {"full_name": "Selvam Murugan", "district": "Villupuram"},
                doc_id="doc-aadhaar",
            ),
            _extracted(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                {"annual_income": 72000.0},
                doc_id="doc-income",
            ),
            _extracted(
                DocumentTypeEnum.LAND_RECORD,
                {"survey_number": "123/2A", "land_area": 2.5, "unit": "acres"},
                doc_id="doc-land",
            ),
        ]
        results = _mapper().map_many(docs)
        assert len(results) == 3
        assert results[0].document_type == DocumentTypeEnum.AADHAAR
        assert results[0].citizen_updates["full_name"] == "Selvam Murugan"
        assert results[1].profile_updates["annual_income"] == 72000.0
        assert results[2].land_record_updates[0].survey_number == "123/2A"
        # Each is independent — no cross-document merging/precedence.
        assert results[0].profile_updates == {}
        assert results[1].citizen_updates == {}

    def test_map_many_empty_returns_empty_list(self):
        assert _mapper().map_many([]) == []


# ── document_id preservation ──────────────────────────────────────────────────

class TestDocumentIdPreservation:
    def test_map_preserves_document_id(self):
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                {"annual_income": 72000.0},
                doc_id="doc-income-123",
            )
        )
        assert result.document_id == "doc-income-123"

    def test_map_preserves_none_document_id(self):
        result = _mapper().map(
            _extracted(DocumentTypeEnum.INCOME_CERTIFICATE, {"annual_income": 72000.0})
        )
        assert result.document_id is None


# ── Unknown / unsupported document type ──────────────────────────────────────

class TestUnknownDocumentType:
    def test_unknown_type_raises_unsupported_error(self):
        # birth_certificate has no defined mapping at this stage.
        doc = _extracted(DocumentTypeEnum.BIRTH_CERTIFICATE, {})
        with pytest.raises(UnsupportedDocumentTypeError) as exc_info:
            _mapper().map(doc)
        assert exc_info.value.error_code == "UNSUPPORTED_DOCUMENT_TYPE"
        assert exc_info.value.details["document_type"] == "birth_certificate"

    def test_none_raises_unsupported_error(self):
        with pytest.raises(UnsupportedDocumentTypeError):
            _mapper().map(None)


# ── Missing fields ────────────────────────────────────────────────────────────

class TestMissingFields:
    def test_empty_fields_yields_empty_updates(self):
        result = _mapper().map(
            _extracted(DocumentTypeEnum.INCOME_CERTIFICATE, {})
        )
        assert result.citizen_updates == {}
        assert result.profile_updates == {}
        assert result.land_record_updates == []

    def test_missing_fields_never_overwrite_with_none(self):
        # None values are preserved as "skip" — not emitted as updates.
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.AADHAAR,
                {"full_name": None, "district": "Villupuram"},
            )
        )
        assert result.citizen_updates == {"district": "Villupuram"}
        assert "full_name" not in result.citizen_updates


# ── Read-only guarantee (no DB writes) ───────────────────────────────────────

class TestReadOnly:
    def test_mapper_performs_no_database_writes(self):
        """The mapper must never touch the DB.

        It is constructed with no session and only receives plain
        ExtractedDocumentData objects. If it tried to write, it would have no
        place to write to and would fail — but it returns clean results instead.
        """
        result = _mapper().map(
            _extracted(
                DocumentTypeEnum.INCOME_CERTIFICATE,
                {"annual_income": 72000.0, "income_category": "bpl"},
                doc_id="readonly-doc",
            )
        )
        assert isinstance(result, MappedDocumentData)
        assert result.document_id == "readonly-doc"
        assert result.profile_updates["annual_income"] == 72000.0

