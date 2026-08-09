"""Debug script: trace the complete document processing pipeline.

Traces the caste certificate, income certificate, and land record pipelines
through every layer to verify that extracted fields flow correctly from
PDF text -> field extraction -> mapping -> enrichment -> database.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import fitz
from pathlib import Path

from app.services.pdf_text_extractor import PdfTextExtractor
from app.services.document_field_extractor import DocumentFieldExtractor
from app.services.document_profile_mapper import DocumentProfileMapper


def create_pdf(path: Path, lines: list[str]) -> Path:
    """Create a text-based PDF with Label:\nValue format."""
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


def trace_document(name: str, lines: list[str], document_type: str,
                   expected_fields: dict):
    """Trace a single document through the pipeline."""
    print("=" * 60)
    print(f"TRACE: {name}")
    print("=" * 60)

    pdf_path = Path(f"debug_{document_type}.pdf")
    create_pdf(pdf_path, lines)

    # Step 1: PDF Text Extraction
    print("\n--- Step 1: PDF Text Extraction ---")
    extractor = PdfTextExtractor()
    try:
        raw_text = extractor.extract(str(pdf_path))
        print(f"Pages: {raw_text.count('--- Page')}")
        print(f"Text length: {len(raw_text)}")
        print(f"Has meaningful text: {extractor.has_meaningful_text(raw_text)}")
    except Exception as e:
        print(f"ERROR: {e}")
        raw_text = ""

    # Step 2: DocumentFieldExtractor
    print("\n--- Step 2: DocumentFieldExtractor ---")
    field_extractor = DocumentFieldExtractor()
    try:
        extracted = field_extractor.extract(
            document_type=document_type,
            raw_text=raw_text,
            document_id=f"debug-{document_type}",
        )
        print(f"Document type: {extracted.document_type}")
        print(f"Fields: {extracted.fields}")
        print("\nExpected fields:")
        for key, expected in expected_fields.items():
            actual = extracted.fields.get(key)
            status = "✓" if actual == expected else "✗"
            print(f"  {status} {key} = {expected} (got: {actual})")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return

    # Step 3: DocumentProfileMapper
    print("\n--- Step 3: DocumentProfileMapper ---")
    mapper = DocumentProfileMapper()
    try:
        mapped = mapper.map(extracted)
        print(f"Citizen updates: {mapped.citizen_updates}")
        print(f"Profile updates: {mapped.profile_updates}")
        print(f"Land record updates: {mapped.land_record_updates}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

    pdf_path.unlink(missing_ok=True)
    print()


# ─── Caste Certificate ────────────────────────────────────────────────────────
trace_document(
    "Caste / Community Certificate",
    [
        "Government of Test State - Caste Certificate (Test Document)",
        "Name:",
        "Test Citizen",
        "Caste:",
        "Vanniyar",
        "Community:",
        "MBC",
        "Sub Caste:",
        "Padayachi",
        "Religion:",
        "Hindu",
        "Issuing Authority:",
        "Sample Revenue Authority",
        "This is a fictional test document.",
    ],
    "caste_certificate",
    {
        "caste": "Vanniyar",
        "community": "MBC",
        "sub_caste": "Padayachi",
        "religion": "Hindu",
    },
)

# ─── Income Certificate (CRITICAL: must NOT read from MOCK_PROFILES) ───────────
trace_document(
    "Income Certificate (CRITICAL)",
    [
        "Government of Test State - Income Certificate (Test Document)",
        "Name:",
        "Test Citizen",
        "Annual Income:",
        "Rs. 85,000",
        "Income Category:",
        "BPL",
        "Financial Year:",
        "2025-2026",
        "This is a fictional test document.",
    ],
    "income_certificate",
    {
        "annual_income": 85000.0,
        "income_category": "bpl",
    },
)

# ─── Land Record (CRITICAL: must originate from uploaded document) ────────────
trace_document(
    "Land Record (CRITICAL)",
    [
        "Government of Test State - Land Record (Test Document)",
        "Owner Name:",
        "Test Citizen",
        "Survey Number:",
        "TEST/001",
        "Land Area:",
        "1.5 acres",
        "Land Type:",
        "Agricultural",
        "Village:",
        "Test Village",
        "Taluk:",
        "Test Taluk",
        "District:",
        "Test District",
        "State:",
        "Test State",
        "Ownership:",
        "Owned",
        "Patta Number:",
        "TN-VPM-2023-001",
        "This is a fictional test document.",
    ],
    "land_record",
    {
        "survey_number": "TEST/001",
        "land_area": 1.5,
        "unit": "acres",
        "land_type": "agricultural",
        "ownership_type": "owned",
    },
)

print("=" * 60)
print("ALL TRACES COMPLETE")
print("=" * 60)
