"""Test Document Helpers — fictional government-document-style PDFs.

All documents are clearly fictional/test documents. No real Aadhaar numbers or
real personal documents are used.

The generated PDFs use text layers where possible (so ``PdfTextExtractor`` can
read them without OCR). One helper also creates an image-only (scanned-style)
PDF that requires OCR fallback.

Document format: labels and values are on SEPARATE lines (Label: on one line,
Value on the next), matching the format of real government certificates.
"""
from __future__ import annotations

from pathlib import Path

# Fictional test values shared by the tests/document PDFs.
TEST_CITIZEN_NAME = "Test Citizen"
TEST_CITIZEN_DOB = "01/01/1985"
TEST_CITIZEN_GENDER = "Male"
TEST_CITIZEN_VILLAGE = "Test Village"
TEST_CITIZEN_TALUK = "Test Taluk"
TEST_CITIZEN_DISTRICT = "Test District"
TEST_CITIZEN_STATE = "Test State"
TEST_CITIZEN_PINCODE = "605001"

TEST_LAND_SURVEY = "TEST/001"
TEST_LAND_AREA = "1.5 acres"
TEST_LAND_TYPE = "Agricultural"
TEST_LAND_OWNERSHIP = "Owned"
TEST_LAND_PATTA = "TN-VPM-2023-001"

TEST_INCOME_AMOUNT = "Rs. 85,000"
TEST_INCOME_CATEGORY = "BPL"
TEST_INCOME_FY = "2025-2026"

TEST_FARMER_ID = "TN-FARMER-000001"

TEST_CASTE = "Vanniyar"
TEST_COMMUNITY = "MBC"
TEST_SUB_CASTE = "Padayachi"
TEST_RELIGION = "Hindu"
TEST_ISSUING_AUTHORITY = "Sample Revenue Authority"

TEST_RATION_CARD_NUMBER = "TN1234567890"
TEST_RATION_CARD_TYPE = "BPL"
TEST_RATION_FAMILY_SIZE = "5"

TEST_DISABILITY_PERCENTAGE = "45"


def create_aadhaar_pdf(path: Path) -> Path:
    """Create a fictional text-based Aadhaar-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of India - Aadhaar (Test Document)",
            "Name:",
            TEST_CITIZEN_NAME,
            "DOB:",
            TEST_CITIZEN_DOB,
            "Gender:",
            TEST_CITIZEN_GENDER,
            "Village:",
            TEST_CITIZEN_VILLAGE,
            "Taluk:",
            TEST_CITIZEN_TALUK,
            "District:",
            TEST_CITIZEN_DISTRICT,
            "State:",
            TEST_CITIZEN_STATE,
            "Pincode:",
            TEST_CITIZEN_PINCODE,
            "Address:",
            "Test Village, Test District, Test State - 605001",
            "This is a fictional test document.",
        ],
    )


def create_income_certificate_pdf(path: Path) -> Path:
    """Create a fictional text-based Income Certificate-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Income Certificate (Test Document)",
            "Name:",
            TEST_CITIZEN_NAME,
            "Annual Income:",
            TEST_INCOME_AMOUNT,
            "Income Category:",
            TEST_INCOME_CATEGORY,
            "Financial Year:",
            TEST_INCOME_FY,
            "This is a fictional test document.",
        ],
    )


def create_land_record_pdf(path: Path) -> Path:
    """Create a fictional text-based Land Record-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Land Record (Test Document)",
            "Owner Name:",
            TEST_CITIZEN_NAME,
            "Survey Number:",
            TEST_LAND_SURVEY,
            "Land Area:",
            TEST_LAND_AREA,
            "Land Type:",
            TEST_LAND_TYPE,
            "Village:",
            TEST_CITIZEN_VILLAGE,
            "Taluk:",
            TEST_CITIZEN_TALUK,
            "District:",
            TEST_CITIZEN_DISTRICT,
            "State:",
            TEST_CITIZEN_STATE,
            "Ownership:",
            TEST_LAND_OWNERSHIP,
            "Patta Number:",
            TEST_LAND_PATTA,
            "This is a fictional test document.",
        ],
    )


def create_farmer_id_pdf(path: Path) -> Path:
    """Create a fictional text-based Farmer ID-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Farmer ID (Test Document)",
            "Farmer ID:",
            TEST_FARMER_ID,
            "Name:",
            TEST_CITIZEN_NAME,
            "Occupation:",
            "Farmer",
            "Status:",
            "Farmer",
            "This is a fictional test document.",
        ],
    )


def create_caste_certificate_pdf(path: Path) -> Path:
    """Create a fictional text-based Caste/Community Certificate-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Caste Certificate (Test Document)",
            "Name:",
            TEST_CITIZEN_NAME,
            "Caste:",
            TEST_CASTE,
            "Community:",
            TEST_COMMUNITY,
            "Sub Caste:",
            TEST_SUB_CASTE,
            "Religion:",
            TEST_RELIGION,
            "Issuing Authority:",
            TEST_ISSUING_AUTHORITY,
            "This is a fictional test document.",
        ],
    )


def create_community_certificate_pdf(path: Path) -> Path:
    """Create a fictional text-based Community Certificate-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Community Certificate (Test Document)",
            "Name:",
            TEST_CITIZEN_NAME,
            "Caste:",
            TEST_CASTE,
            "Community:",
            TEST_COMMUNITY,
            "Sub Caste:",
            TEST_SUB_CASTE,
            "Religion:",
            TEST_RELIGION,
            "Issuing Authority:",
            TEST_ISSUING_AUTHORITY,
            "This is a fictional test document.",
        ],
    )


def create_ration_card_pdf(path: Path) -> Path:
    """Create a fictional text-based Smart Ration Card-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Smart Ration Card (Test Document)",
            "Card Number:",
            TEST_RATION_CARD_NUMBER,
            "Name:",
            TEST_CITIZEN_NAME,
            "Card Type:",
            TEST_RATION_CARD_TYPE,
            "Family Size:",
            TEST_RATION_FAMILY_SIZE,
            "District:",
            TEST_CITIZEN_DISTRICT,
            "This is a fictional test document.",
        ],
    )


def create_residence_certificate_pdf(path: Path) -> Path:
    """Create a fictional text-based Residence Certificate-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Residence Certificate (Test Document)",
            "Name:",
            TEST_CITIZEN_NAME,
            "Village:",
            TEST_CITIZEN_VILLAGE,
            "Taluk:",
            TEST_CITIZEN_TALUK,
            "District:",
            TEST_CITIZEN_DISTRICT,
            "State:",
            TEST_CITIZEN_STATE,
            "This is a fictional test document.",
        ],
    )


def create_disability_certificate_pdf(path: Path) -> Path:
    """Create a fictional text-based Disability Certificate-like PDF."""
    return _write_text_pdf(
        path,
        [
            "Government of Test State - Disability Certificate (Test Document)",
            "Name:",
            TEST_CITIZEN_NAME,
            "Disability:",
            "Yes",
            "Disability Percentage:",
            TEST_DISABILITY_PERCENTAGE,
            "This is a fictional test document.",
        ],
    )


def create_scanned_style_pdf(path: Path) -> Path:
    """Create a PDF with NO text layer (image-only), forcing OCR fallback.

    Renders a simple image with no readable text so the deterministic field
    extraction produces missing fields; the PDF itself exercises the
    PDF -> OCR fallback path.
    """
    import fitz

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    # Blank white page — no text layer, no content. OCR will return empty text,
    # which is the intended test for the OCR-fallback failure path.
    page.draw_rect(fitz.Rect(0, 0, 595, 842), color=(1, 1, 1), fill=(1, 1, 1))
    document.save(str(path))
    document.close()
    return path


def create_valid_text_pdf(path: Path) -> Path:
    """Create a generic text PDF used for PdfTextExtractor unit tests."""
    return _write_text_pdf(
        path,
        [
            "Test Document",
            "Name:",
            "Test Citizen",
            "This document has a selectable text layer.",
        ],
    )


def _write_text_pdf(path: Path, lines: list[str]) -> Path:
    """Write a text-based PDF using PyMuPDF with a selectable text layer."""
    import fitz

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = 72
    for line in lines:
        page.insert_text(
            fitz.Point(72, y),
            line,
            fontsize=11,
            fontname="helv",
        )
        y += 18
    document.save(str(path))
    document.close()
    return path
