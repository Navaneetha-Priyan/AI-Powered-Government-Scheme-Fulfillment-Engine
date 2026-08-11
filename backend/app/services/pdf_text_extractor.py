"""PdfTextExtractor — Phase 1: PDF → Raw Text.

Extracts the selectable text layer from a PDF using PyMuPDF (``fitz``). This is
the *first* extraction attempt in the real-document pipeline. OCR is only used
as a fallback when a PDF has no meaningful text layer (see
``DocumentProcessingService``).

Design rules:
- Never fabricate text.
- Preserve page boundaries with a ``\n\n--- Page N ---\n\n`` separator so
  downstream field extraction can reason about layout when needed.
- Raise a controlled ``DocumentTextExtractionError`` for malformed/encrypted
  PDFs or when the text layer is empty (the caller decides whether to fall back
  to OCR).
"""
from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger
from app.exceptions.exceptions import DocumentTextExtractionError

logger = get_logger(__name__)

# A page is considered to have "meaningful" text when it contains at least this
# many non-whitespace characters. This is a deliberately conservative threshold:
# a real government document page will contain far more than 20 characters, while
# a scanned/image-only page will contain ~0. This prevents unnecessary OCR for
# text-based PDFs while still catching genuinely empty pages.
MIN_MEANINGFUL_TEXT_CHARS = 20


class PdfTextExtractor:
    """Extracts normalized raw text from a PDF file."""

    def extract(self, file_path: str) -> str:
        """Extract text from the PDF at ``file_path``.

        Returns the concatenated page text (page boundaries preserved). Raises
        ``DocumentTextExtractionError`` when the PDF cannot be read or contains
        no meaningful text.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentTextExtractionError(
                reason=f"PDF file not found: {path.name}",
                filename=path.name,
            )

        try:
            import fitz  # PyMuPDF
        except ImportError as exc:  # pragma: no cover - environment check
            raise DocumentTextExtractionError(
                reason="PyMuPDF is not installed; cannot extract PDF text",
                filename=path.name,
            ) from exc

        try:
            document = fitz.open(str(path))
        except Exception as exc:
            logger.warning("Failed to open PDF %s: %s", path.name, exc)
            raise DocumentTextExtractionError(
                reason="The PDF file could not be opened",
                filename=path.name,
            ) from exc

        try:
            if document.needs_pass:
                raise DocumentTextExtractionError(
                    reason="The PDF is password-protected",
                    filename=path.name,
                )

            pages: list[str] = []
            for page_index, page in enumerate(document, start=1):
                try:
                    text = page.get_text("text")
                except Exception as exc:
                    logger.warning(
                        "Failed to extract text from page %d of %s: %s",
                        page_index,
                        path.name,
                        exc,
                    )
                    text = ""
                pages.append(f"--- Page {page_index} ---\n{text}")

            document.close()
        except DocumentTextExtractionError:
            document.close()
            raise
        except Exception as exc:
            document.close()
            logger.warning("Unexpected PDF text extraction error: %s", exc)
            raise DocumentTextExtractionError(
                reason="Could not extract text from the PDF",
                filename=path.name,
            ) from exc

        raw_text = "\n\n".join(pages).strip()
        if not self.has_meaningful_text(raw_text):
            raise DocumentTextExtractionError(
                reason="The PDF has no selectable text layer (OCR required)",
                filename=path.name,
            )

        logger.info(
            "Extracted %d characters of text from %s",
            len(raw_text),
            path.name,
        )
        return raw_text

    @staticmethod
    def has_meaningful_text(raw_text: str) -> bool:
        """Return True when ``raw_text`` contains enough non-whitespace
        characters to be considered meaningful.

        Threshold: :data:`MIN_MEANINGFUL_TEXT_CHARS` non-whitespace characters.
        This is documented in the module docstring.
        """
        if not raw_text:
            return False
        non_whitespace = sum(1 for ch in raw_text if not ch.isspace())
        return non_whitespace >= MIN_MEANINGFUL_TEXT_CHARS