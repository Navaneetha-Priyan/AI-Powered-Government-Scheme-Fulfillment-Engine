"""Unit Tests — PdfTextExtractor (Phase 1)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.exceptions.exceptions import DocumentTextExtractionError
from app.services.pdf_text_extractor import PdfTextExtractor, MIN_MEANINGFUL_TEXT_CHARS
from tests.test_document_helpers import (
    create_scanned_style_pdf,
    create_valid_text_pdf,
)


class TestPdfTextExtractor:
    def test_extracts_text_from_text_based_pdf(self, tmp_path: Path):
        pdf = create_valid_text_pdf(tmp_path / "text.pdf")
        extractor = PdfTextExtractor()
        text = extractor.extract(str(pdf))
        assert "Test Citizen" in text
        assert "--- Page 1 ---" in text

    def test_raises_when_file_missing(self):
        extractor = PdfTextExtractor()
        with pytest.raises(DocumentTextExtractionError):
            extractor.extract("nonexistent.pdf")

    def test_raises_when_pdf_has_no_text_layer(self, tmp_path: Path):
        pdf = create_scanned_style_pdf(tmp_path / "scanned.pdf")
        extractor = PdfTextExtractor()
        with pytest.raises(DocumentTextExtractionError) as exc:
            extractor.extract(str(pdf))
        assert "no selectable text" in exc.value.message.lower()

    def test_has_meaningful_text_threshold(self):
        extractor = PdfTextExtractor()
        assert extractor.has_meaningful_text("") is False
        assert extractor.has_meaningful_text(" \n\t ") is False
        assert (
            extractor.has_meaningful_text("x" * MIN_MEANINGFUL_TEXT_CHARS)
            is True
        )