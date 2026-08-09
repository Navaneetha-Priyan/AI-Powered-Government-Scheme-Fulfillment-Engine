"""Unit Tests — DocumentFieldExtractor (Phases 5-8).

Tests both the ``Label: Value`` (same-line) and ``Label:\\nValue`` (next-line)
document formats to ensure the extractor handles real-world government
certificate layouts where the label and value appear on separate lines.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.exceptions.exceptions import (
    DocumentProcessingError,
    UnsupportedDocumentTypeError,
)
from app.schemas.citizen_profile import DocumentTypeEnum
from app.services.document_field_extractor import DocumentFieldExtractor


class TestAadhaarExtraction:
    def test_extracts_aadhaar_fields_same_line(self):
        text = (
            "Government of India - Aadhaar (Test Document)\n"
            "Name: Test Citizen\n"
            "DOB: 01/01/1985\n"
            "Gender: Male\n"
            "Village: Test Village\n"
            "District: Test District\n"
            "State: Test State\n"
            "Pincode: 605001\n"
        )
        result = DocumentFieldExtractor().extract("aadhaar", text)
        assert result.document_type == DocumentTypeEnum.AADHAAR
        assert result.fields["full_name"] == "Test Citizen"
        assert result.fields["date_of_birth"] == "1985-01-01"
        assert result.fields["gender"] == "male"
        assert result.fields["village"] == "Test Village"
        assert result.fields["district"] == "Test District"
        assert result.fields["state"] == "Test State"
        assert result.fields["pincode"] == "605001"

    def test_extracts_aadhaar_fields_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Government of India - Aadhaar (Test Document)\n"
            "Name:\n"
            "Test Citizen\n"
            "DOB:\n"
            "01/01/1985\n"
            "Gender:\n"
            "Male\n"
            "Village:\n"
            "Test Village\n"
            "Taluk:\n"
            "Test Taluk\n"
            "District:\n"
            "Test District\n"
            "State:\n"
            "Test State\n"
            "Pincode:\n"
            "605001\n"
            "Address:\n"
            "Test Village, Test District, Test State - 605001\n"
        )
        result = DocumentFieldExtractor().extract("aadhaar", text)
        assert result.fields["full_name"] == "Test Citizen"
        assert result.fields["date_of_birth"] == "1985-01-01"
        assert result.fields["gender"] == "male"
        assert result.fields["village"] == "Test Village"
        assert result.fields["taluk"] == "Test Taluk"
        assert result.fields["district"] == "Test District"
        assert result.fields["state"] == "Test State"
        assert result.fields["pincode"] == "605001"
        assert result.fields["address_line1"] == "Test Village, Test District, Test State - 605001"

    def test_missing_optional_fields_remain_none(self):
        text = "Name: Test Citizen\nDOB: 01/01/1985\n"
        result = DocumentFieldExtractor().extract("aadhaar", text)
        assert result.fields["full_name"] == "Test Citizen"
        assert result.fields["village"] is None
        assert result.fields["state"] is None


class TestIncomeCertificateExtraction:
    def test_extracts_income_same_line(self):
        text = (
            "Name: Test Citizen\n"
            "Annual Income: Rs. 85,000\n"
            "Income Category: BPL\n"
        )
        result = DocumentFieldExtractor().extract("income_certificate", text)
        assert result.fields["annual_income"] == 85000.0
        assert result.fields["income_category"] == "bpl"

    def test_extracts_income_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Name:\n"
            "Test Citizen\n"
            "Annual Income:\n"
            "Rs. 85,000\n"
            "Income Category:\n"
            "BPL\n"
            "Financial Year:\n"
            "2025-2026\n"
        )
        result = DocumentFieldExtractor().extract("income_certificate", text)
        assert result.fields["holder_name"] == "Test Citizen"
        assert result.fields["annual_income"] == 85000.0
        assert result.fields["income_category"] == "bpl"
        assert result.fields["financial_year"] == "2025-2026"

    def test_missing_income_remains_none(self):
        result = DocumentFieldExtractor().extract("income_certificate", "Name: X\n")
        assert result.fields["annual_income"] is None


class TestLandRecordExtraction:
    def test_extracts_land_record_same_line(self):
        text = (
            "Owner Name: Test Citizen\n"
            "Survey Number: TEST/001\n"
            "Land Area: 1.5 acres\n"
            "Land Type: Agricultural\n"
            "Village: Test Village\n"
            "Ownership: Owned\n"
        )
        result = DocumentFieldExtractor().extract("land_record", text)
        assert result.fields["survey_number"] == "TEST/001"
        assert result.fields["land_area"] == 1.5
        assert result.fields["unit"] == "acres"
        assert result.fields["land_type"] == "agricultural"
        assert result.fields["ownership_type"] == "owned"

    def test_extracts_land_record_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Owner Name:\n"
            "Test Citizen\n"
            "Survey Number:\n"
            "TEST/001\n"
            "Land Area:\n"
            "1.5 acres\n"
            "Land Type:\n"
            "Agricultural\n"
            "Village:\n"
            "Test Village\n"
            "Taluk:\n"
            "Test Taluk\n"
            "District:\n"
            "Test District\n"
            "State:\n"
            "Test State\n"
            "Ownership:\n"
            "Owned\n"
            "Patta Number:\n"
            "TN-VPM-2023-001\n"
        )
        result = DocumentFieldExtractor().extract("land_record", text)
        assert result.fields["survey_number"] == "TEST/001"
        assert result.fields["land_area"] == 1.5
        assert result.fields["unit"] == "acres"
        assert result.fields["land_type"] == "agricultural"
        assert result.fields["ownership_type"] == "owned"
        assert result.fields["patta_number"] == "TN-VPM-2023-001"

    def test_area_without_unit(self):
        text = "Survey Number: TEST/001\nLand Area: 2.5\n"
        result = DocumentFieldExtractor().extract("land_record", text)
        assert result.fields["land_area"] == 2.5
        assert result.fields["unit"] is None


class TestFarmerIdExtraction:
    def test_extracts_farmer_same_line(self):
        text = (
            "Farmer ID: TN-FARMER-000001\n"
            "Name: Test Citizen\n"
            "Occupation: Farmer\n"
            "Status: Farmer\n"
        )
        result = DocumentFieldExtractor().extract("farmer_id", text)
        assert result.fields["farmer_id"] == "TN-FARMER-000001"
        assert result.fields["is_farmer"] is True
        assert result.fields["occupation"] == "Farmer"

    def test_extracts_farmer_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Farmer ID:\n"
            "TN-FARMER-000001\n"
            "Name:\n"
            "Test Citizen\n"
            "Occupation:\n"
            "Farmer\n"
            "Status:\n"
            "Farmer\n"
        )
        result = DocumentFieldExtractor().extract("farmer_id", text)
        assert result.fields["farmer_id"] == "TN-FARMER-000001"
        assert result.fields["is_farmer"] is True
        assert result.fields["occupation"] == "Farmer"

    def test_non_farmer_status(self):
        text = "Farmer ID: TN-FARMER-000002\nName: X\nStatus: No\n"
        result = DocumentFieldExtractor().extract("farmer_id", text)
        assert result.fields["is_farmer"] is False


class TestCasteCertificateExtraction:
    def test_extracts_caste_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Government of Test State - Caste Certificate (Test Document)\n"
            "Name:\n"
            "Test Citizen\n"
            "Caste:\n"
            "Vanniyar\n"
            "Community:\n"
            "MBC\n"
            "Sub Caste:\n"
            "Padayachi\n"
            "Religion:\n"
            "Hindu\n"
            "Issuing Authority:\n"
            "Sample Revenue Authority\n"
        )
        result = DocumentFieldExtractor().extract("caste_certificate", text)
        assert result.document_type == DocumentTypeEnum.CASTE_CERTIFICATE
        assert result.fields["caste"] == "Vanniyar"
        assert result.fields["community"] == "MBC"
        assert result.fields["sub_caste"] == "Padayachi"
        assert result.fields["religion"] == "Hindu"
        assert result.fields["issuing_authority"] == "Sample Revenue Authority"

    def test_community_certificate_alias(self):
        """community_certificate should resolve to the same extractor."""
        text = (
            "Name:\n"
            "Test Citizen\n"
            "Caste:\n"
            "Vanniyar\n"
            "Community:\n"
            "MBC\n"
            "Sub Caste:\n"
            "Padayachi\n"
            "Religion:\n"
            "Hindu\n"
        )
        result = DocumentFieldExtractor().extract("community_certificate", text)
        assert result.document_type == DocumentTypeEnum.COMMUNITY_CERTIFICATE
        assert result.fields["caste"] == "Vanniyar"
        assert result.fields["community"] == "MBC"
        assert result.fields["sub_caste"] == "Padayachi"
        assert result.fields["religion"] == "Hindu"


class TestRationCardExtraction:
    def test_extracts_ration_card_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Government of Test State - Smart Ration Card (Test Document)\n"
            "Card Number:\n"
            "TN1234567890\n"
            "Name:\n"
            "Test Citizen\n"
            "Card Type:\n"
            "BPL\n"
            "Family Size:\n"
            "5\n"
            "District:\n"
            "Test District\n"
        )
        result = DocumentFieldExtractor().extract("smart_ration_card", text)
        assert result.document_type == DocumentTypeEnum.SMART_RATION_CARD
        assert result.fields["card_number"] == "TN1234567890"
        assert result.fields["card_type"] == "bpl"
        assert result.fields["family_size"] == 5


class TestResidenceCertificateExtraction:
    def test_extracts_residence_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Government of Test State - Residence Certificate (Test Document)\n"
            "Name:\n"
            "Test Citizen\n"
            "Village:\n"
            "Test Village\n"
            "Taluk:\n"
            "Test Taluk\n"
            "District:\n"
            "Test District\n"
            "State:\n"
            "Test State\n"
        )
        result = DocumentFieldExtractor().extract("residence_certificate", text)
        assert result.document_type == DocumentTypeEnum.RESIDENCE_CERTIFICATE
        assert result.fields["village"] == "Test Village"
        assert result.fields["taluk"] == "Test Taluk"
        assert result.fields["district"] == "Test District"
        assert result.fields["state"] == "Test State"


class TestDisabilityCertificateExtraction:
    def test_extracts_disability_next_line(self):
        """Label and value on separate lines (real certificate format)."""
        text = (
            "Government of Test State - Disability Certificate (Test Document)\n"
            "Name:\n"
            "Test Citizen\n"
            "Disability:\n"
            "Yes\n"
            "Disability Percentage:\n"
            "45\n"
        )
        result = DocumentFieldExtractor().extract("disability_certificate", text)
        assert result.document_type == DocumentTypeEnum.DISABILITY_CERTIFICATE
        assert result.fields["is_disabled"] is True
        assert result.fields["disability_percentage"] == 45


class TestValidation:
    def test_raises_on_unsupported_type(self):
        with pytest.raises(UnsupportedDocumentTypeError):
            DocumentFieldExtractor().extract("passport", "Name: X\n")

    def test_raises_on_empty_text(self):
        with pytest.raises(DocumentProcessingError):
            DocumentFieldExtractor().extract("aadhaar", "  \n  ")

    def test_preserves_document_id(self):
        result = DocumentFieldExtractor().extract(
            "aadhaar", "Name: X\nDOB: 01/01/1985\n", document_id="doc-1"
        )
        assert result.document_id == "doc-1"


class TestLabelValueFormats:
    """Verify the extractor handles both same-line and next-line formats."""

    def test_same_line_format(self):
        text = "Caste: Vanniyar\nCommunity: MBC\n"
        result = DocumentFieldExtractor().extract("caste_certificate", text)
        assert result.fields["caste"] == "Vanniyar"
        assert result.fields["community"] == "MBC"

    def test_next_line_format(self):
        text = "Caste:\nVanniyar\nCommunity:\nMBC\n"
        result = DocumentFieldExtractor().extract("caste_certificate", text)
        assert result.fields["caste"] == "Vanniyar"
        assert result.fields["community"] == "MBC"

    def test_mixed_format(self):
        text = "Caste: Vanniyar\nCommunity:\nMBC\n"
        result = DocumentFieldExtractor().extract("caste_certificate", text)
        assert result.fields["caste"] == "Vanniyar"
        assert result.fields["community"] == "MBC"

    def test_label_only_does_not_consume_next_label(self):
        """When a label is followed by another label, don't take the next label as value."""
        text = "Caste:\nCommunity:\nMBC\n"
        result = DocumentFieldExtractor().extract("caste_certificate", text)
        # "Caste:" is followed by "Community:" which is another label, so caste should be None
        assert result.fields["caste"] is None
        assert result.fields["community"] == "MBC"
