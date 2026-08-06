"""PDF extraction and chunking pipeline for Module 3."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence
from uuid import uuid4

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import InvalidPDFError, ProcessingFailedError

logger = get_logger(__name__)


@dataclass
class ProcessedChunk:
    scheme_id: str
    document_id: str
    chunk_text: str
    page_number: int
    section_name: str
    embedding_id: str
    token_count: int


class SchemeProcessingService:
    """Extract text, detect sections, and create meaningful scheme chunks."""

    def extract_pages(self, file_path: str) -> List[dict]:
        try:
            import fitz
        except Exception as exc:  # pragma: no cover - import guard
            raise ProcessingFailedError(f"PyMuPDF is unavailable: {exc}") from exc

        pdf_path = Path(file_path)
        if not pdf_path.exists():
            raise InvalidPDFError("Uploaded PDF file does not exist")

        try:
            document = fitz.open(str(pdf_path))
        except Exception as exc:
            raise InvalidPDFError(f"Unable to open PDF: {exc}") from exc

        pages: List[dict] = []
        for page_number, page in enumerate(document, start=1):
            raw_text = page.get_text("text") or ""
            cleaned_text = self.clean_text(raw_text)
            if cleaned_text:
                pages.append(
                    {
                        "page_number": page_number,
                        "text": cleaned_text,
                    }
                )

        return pages

    def clean_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines).strip()

    def build_chunks(self, scheme_id: str, document_id: str, pages: Sequence[dict]) -> List[ProcessedChunk]:
        if not pages:
            raise ProcessingFailedError("No extractable text found in PDF")

        chunks: List[ProcessedChunk] = []
        for page in pages:
            section_map = self._split_page_into_sections(page["text"])
            for section_name, section_text in section_map:
                for chunk_text in self._chunk_section(section_text):
                    chunks.append(
                        ProcessedChunk(
                            scheme_id=scheme_id,
                            document_id=document_id,
                            chunk_text=chunk_text,
                            page_number=page["page_number"],
                            section_name=section_name,
                            embedding_id=str(uuid4()),
                            token_count=self._count_tokens(chunk_text),
                        )
                    )

        if not chunks:
            raise ProcessingFailedError("No chunks could be generated from the document")

        return chunks

    def process_pdf(self, scheme_id: str, document_id: str, file_path: str) -> List[ProcessedChunk]:
        pages = self.extract_pages(file_path)
        return self.build_chunks(scheme_id, document_id, pages)

    def _split_page_into_sections(self, page_text: str) -> List[tuple[str, str]]:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        if not lines:
            return []

        sections: List[tuple[str, str]] = []
        current_section = "General"
        current_lines: List[str] = []

        for line in lines:
            if self._looks_like_section_heading(line):
                if current_lines:
                    sections.append((current_section, " ".join(current_lines).strip()))
                    current_lines = []
                current_section = self._normalize_section_name(line)
                continue
            current_lines.append(line)

        if current_lines:
            sections.append((current_section, " ".join(current_lines).strip()))

        return sections or [("General", page_text.strip())]

    def _looks_like_section_heading(self, line: str) -> bool:
        normalized = line.strip()
        if len(normalized) > 80:
            return False
        heading_patterns = (
            normalized.isupper(),
            normalized.endswith(":"),
            bool(re.match(r"^(eligibility|benefits|documents|required documents|application process|how to apply|overview|introduction|purpose|scope)\b", normalized.lower())),
        )
        return any(heading_patterns)

    def _normalize_section_name(self, line: str) -> str:
        section = line.strip().rstrip(":")
        section = re.sub(r"\s+", " ", section)
        return section[:150] or "General"

    def _chunk_section(self, text: str) -> List[str]:
        text = self.clean_text(text)
        if not text:
            return []

        max_size = max(200, settings.SCHEME_CHUNK_SIZE)
        overlap = max(0, min(settings.SCHEME_CHUNK_OVERLAP, max_size // 3))
        if len(text) <= max_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + max_size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)

        return chunks

    def _count_tokens(self, text: str) -> int:
        return len([token for token in re.split(r"\s+", text.strip()) if token])
