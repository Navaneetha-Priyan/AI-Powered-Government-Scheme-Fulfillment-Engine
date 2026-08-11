"""Integration Tests — Real Document Processing → Profile Enrichment.

These tests prove the CRITICAL end-to-end pipeline for REAL uploaded documents:

    REAL PDF/IMAGE
        -> DocumentProcessingService
        -> PdfTextExtractor / DocumentOcrService
        -> DocumentFieldExtractor
        -> ExtractedDocumentData
        -> DocumentProfileMapper          # existing Step 3
        -> ProfileEnrichmentService       # existing Step 4
        -> citizens / citizen_profiles / land_records

The values asserted here MUST originate from the PDF text/OCR — NOT from
MOCK_PROFILES or any hardcoded fixture values injected elsewhere.

All test PDFs use the ``Label:\\nValue`` format (label on one line, value on
the next) that matches real government certificate layouts.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from app.repositories.citizen_profile_repository import (
    CitizenProfileRepository,
    LandRecordRepository,
)
from app.repositories.citizen_repository import CitizenRepository
from app.services.document_processing_service import DocumentProcessingService
from tests.test_document_helpers import (
    TEST_CITIZEN_NAME,
    TEST_LAND_SURVEY,
    TEST_LAND_AREA,
    TEST_LAND_TYPE,
    TEST_LAND_OWNERSHIP,
    TEST_LAND_PATTA,
    TEST_INCOME_AMOUNT,
    TEST_INCOME_CATEGORY,
    TEST_FARMER_ID,
    TEST_CASTE,
    TEST_COMMUNITY,
    TEST_SUB_CASTE,
    TEST_RELIGION,
    TEST_ISSUING_AUTHORITY,
    TEST_RATION_CARD_NUMBER,
    TEST_RATION_CARD_TYPE,
    TEST_RATION_FAMILY_SIZE,
    TEST_DISABILITY_PERCENTAGE,
    TEST_CITIZEN_VILLAGE,
    TEST_CITIZEN_TALUK,
    TEST_CITIZEN_DISTRICT,
    TEST_CITIZEN_STATE,
    TEST_CITIZEN_PINCODE,
    TEST_CITIZEN_DOB,
    TEST_CITIZEN_GENDER,
    create_aadhaar_pdf,
    create_income_certificate_pdf,
    create_land_record_pdf,
    create_farmer_id_pdf,
    create_caste_certificate_pdf,
    create_community_certificate_pdf,
    create_ration_card_pdf,
    create_residence_certificate_pdf,
    create_disability_certificate_pdf,
)


def _register_minimal_citizen(client: TestClient, email: str, phone: str) -> dict:
    """Register a citizen with NO pre-filled document data so enrichment must
    come entirely from the uploaded PDF."""
    register_data = {
        "email": email,
        "phone": phone,
        "full_name": "Unknown Initial Name",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "district": "Chennai",
        "state": "Tamil Nadu",
    }
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 201
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAadhaarPdfEnrichesCitizen:
    def test_aadhaar_pdf_enriches_citizen_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional Aadhaar PDF populates the citizen profile.

        Name = Test Citizen, DOB = 01/01/1985, Gender = Male, Village = Test Village.
        These values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-aadhaar@example.com", "9000000001"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "aadhaar.pdf"
        create_aadhaar_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="aadhaar",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.document_type.value == "aadhaar"
        # Extracted fields come from the PDF text.
        assert result.extracted_fields["full_name"] == TEST_CITIZEN_NAME
        assert result.extracted_fields["date_of_birth"] == "1985-01-01"
        assert result.extracted_fields["gender"] == "male"
        assert result.extracted_fields["village"] == TEST_CITIZEN_VILLAGE

        # Enrichment persisted to the citizens table.
        citizen = CitizenRepository(test_db).get_by_id(citizen_id)
        assert citizen.full_name == TEST_CITIZEN_NAME
        assert citizen.gender == "male"
        assert citizen.village == TEST_CITIZEN_VILLAGE
        assert citizen.date_of_birth is not None


class TestLandRecordPdfEnrichesLandRecords:
    def test_land_record_pdf_creates_land_record(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional land-record PDF creates a land record.

        Survey = TEST/001, Area = 1.5 acres, Type = Agricultural, Ownership = Owned.
        Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-land@example.com", "9000000002"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "land.pdf"
        create_land_record_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="land_record",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["survey_number"] == TEST_LAND_SURVEY
        assert result.extracted_fields["land_area"] == 1.5
        assert result.extracted_fields["unit"] == "acres"
        assert result.extracted_fields["land_type"] == "agricultural"
        assert result.extracted_fields["ownership_type"] == "owned"

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen_id)
        assert len(records) == 1
        assert records[0].survey_number == TEST_LAND_SURVEY
        assert records[0].land_area == 1.5
        assert records[0].land_area_unit == "acres"


class TestIncomeCertificatePdfEnrichesProfile:
    def test_income_certificate_pdf_enriches_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional income-certificate PDF updates citizen_profiles.

        Annual Income = Rs. 85,000, Category = BPL.
        Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-income@example.com", "9000000003"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "income.pdf"
        create_income_certificate_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="income_certificate",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["annual_income"] == 85000.0
        assert result.extracted_fields["income_category"] == "bpl"

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile.annual_income == 85000.0
        assert profile.income_category.value == "bpl"


class TestFarmerIdPdfEnrichesProfile:
    def test_farmer_id_pdf_enriches_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """A fictional Farmer ID PDF sets is_farmer + farmer_id in profile."""
        headers = _register_minimal_citizen(
            client, "doc-farmer@example.com", "9000000004"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "farmer.pdf"
        create_farmer_id_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="farmer_id",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["farmer_id"] == TEST_FARMER_ID
        assert result.extracted_fields["is_farmer"] is True

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile.is_farmer is True
        assert profile.farmer_id == TEST_FARMER_ID


class TestCasteCertificatePdfEnrichesProfile:
    def test_caste_certificate_pdf_enriches_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional Caste Certificate PDF updates citizen_profiles.

        Caste = Vanniyar, Community = MBC, Sub Caste = Padayachi, Religion = Hindu.
        Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-caste@example.com", "9000000005"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "caste.pdf"
        create_caste_certificate_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="caste_certificate",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["caste"] == TEST_CASTE
        assert result.extracted_fields["community"] == TEST_COMMUNITY
        assert result.extracted_fields["sub_caste"] == TEST_SUB_CASTE
        assert result.extracted_fields["religion"] == TEST_RELIGION

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile.caste == TEST_CASTE
        assert profile.community == TEST_COMMUNITY
        assert profile.sub_caste == TEST_SUB_CASTE
        assert profile.religion == TEST_RELIGION


class TestCommunityCertificatePdfEnrichesProfile:
    def test_community_certificate_pdf_enriches_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional Community Certificate PDF updates citizen_profiles.

        Uses the community_certificate alias which maps to the same extractor.
        Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-community@example.com", "9000000006"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "community.pdf"
        create_community_certificate_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="community_certificate",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["caste"] == TEST_CASTE
        assert result.extracted_fields["community"] == TEST_COMMUNITY
        assert result.extracted_fields["sub_caste"] == TEST_SUB_CASTE
        assert result.extracted_fields["religion"] == TEST_RELIGION

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile.caste == TEST_CASTE
        assert profile.community == TEST_COMMUNITY
        assert profile.sub_caste == TEST_SUB_CASTE
        assert profile.religion == TEST_RELIGION


class TestRationCardPdfEnrichesProfile:
    def test_ration_card_pdf_enriches_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional Smart Ration Card PDF updates citizen + profile.

        Card Number = TN1234567890, Family Size = 5.
        Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-ration@example.com", "9000000007"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "ration.pdf"
        create_ration_card_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="smart_ration_card",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["card_number"] == TEST_RATION_CARD_NUMBER
        assert result.extracted_fields["family_size"] == 5

        citizen = CitizenRepository(test_db).get_by_id(citizen_id)
        assert citizen.smart_ration_card == TEST_RATION_CARD_NUMBER

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile.family_member_count == 5


class TestResidenceCertificatePdfEnrichesCitizen:
    def test_residence_certificate_pdf_enriches_citizen(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional Residence Certificate PDF updates citizen address.

        Village = Test Village, Taluk = Test Taluk, District = Test District,
        State = Test State. Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-residence@example.com", "9000000008"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "residence.pdf"
        create_residence_certificate_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="residence_certificate",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["village"] == TEST_CITIZEN_VILLAGE
        assert result.extracted_fields["taluk"] == TEST_CITIZEN_TALUK
        assert result.extracted_fields["district"] == TEST_CITIZEN_DISTRICT
        assert result.extracted_fields["state"] == TEST_CITIZEN_STATE

        citizen = CitizenRepository(test_db).get_by_id(citizen_id)
        assert citizen.village == TEST_CITIZEN_VILLAGE
        assert citizen.taluk == TEST_CITIZEN_TALUK
        assert citizen.district == TEST_CITIZEN_DISTRICT
        assert citizen.state == TEST_CITIZEN_STATE


class TestDisabilityCertificatePdfEnrichesProfile:
    def test_disability_certificate_pdf_enriches_profile(
        self, client: TestClient, test_db, tmp_path: Path
    ):
        """CRITICAL: A fictional Disability Certificate PDF updates citizen_profiles.

        is_disabled = True, disability_percentage = 45.
        Values MUST originate from the PDF text.
        """
        headers = _register_minimal_citizen(
            client, "doc-disability@example.com", "9000000009"
        )
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        pdf_path = tmp_path / "disability.pdf"
        create_disability_certificate_pdf(pdf_path)

        service = DocumentProcessingService(test_db)
        result = service.process_file(
            file_path=str(pdf_path),
            document_type="disability_certificate",
            citizen_id=citizen_id,
            document_id=None,
        )

        assert result.extraction_method == "pdf_text"
        assert result.extracted_fields["is_disabled"] is True
        assert result.extracted_fields["disability_percentage"] == 45

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile.is_disabled is True
        assert profile.disability_percentage == 45
