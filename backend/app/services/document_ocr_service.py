"""DocumentOcrService — Phase 2: Image/PDF → OCR → Raw Text.

Performs OCR using Tesseract (via ``pytesseract``). This is the *fallback*
extraction method used when a PDF has no selectable text layer, or the primary
method for image uploads (jpg/png).

OCR solution selected: **Tesseract OCR 5.x** (local, open-source, no cloud/paid
service). It is lightweight (no PyTorch), well-documented, and appropriate for a
college project/demo. The Python wrapper is ``pytesseract``.

Design rules:
- Never fabricate text.
- Accepts an image file path directly, or a PDF path (renders each page to an
  image via PyMuPDF before OCR).
- Resolves the Tesseract binary from PATH first, then falls back to the standard
  Windows install location (``C:\\Program Files\\Tesseract-OCR\\tesseract.exe``).
- Raises a controlled ``DocumentOcrError`` when OCR fails or produces no text.
"""
from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger
from app.exceptions.exceptions import DocumentOcrError

logger = get_logger(__name__)

# Standard Windows install location for the UB-Mannheim Tesseract build.
_TESSERACT_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# Image extensions that can be OCR'd directly.
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class DocumentOcrService:
    """Performs OCR on an image or PDF file."""

    def __init__(self) -> None:
        self._tesseract_cmd: str | None = None

    def ocr_file(self, file_path: str) -> str:
        """OCR the file at ``file_path`` and return the raw text.

        - Image files are OCR'd directly.
        - PDF files are rendered page-by-page to images, then OCR'd.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentOcrError(
                reason=f"File not found: {path.name}",
                filename=path.name,
            )

        suffix = path.suffix.lower()
        if suffix in _IMAGE_EXTENSIONS:
            return self._ocr_image(path)
        if suffix == ".pdf":
            return self._ocr_pdf(path)
        raise DocumentOcrError(
            reason=f"Unsupported file type for OCR: {suffix or 'unknown'}",
            filename=path.name,
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    def _ocr_image(self, path: Path) -> str:
        """OCR a single image file."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - environment check
            raise DocumentOcrError(
                reason="OCR dependencies (pytesseract/Pillow) are not installed",
                filename=path.name,
            ) from exc

        self._configure_tesseract(pytesseract)

        try:
            with Image.open(str(path)) as image:
                text = pytesseract.image_to_string(image)
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", path.name, exc)
            raise DocumentOcrError(
                reason="OCR could not read the image",
                filename=path.name,
            ) from exc

        return self._validate_ocr_text(text, path.name)

    def _ocr_pdf(self, path: Path) -> str:
        """Render each PDF page to an image and OCR it."""
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - environment check
            raise DocumentOcrError(
                reason="OCR dependencies (PyMuPDF/pytesseract/Pillow) are not installed",
                filename=path.name,
            ) from exc

        self._configure_tesseract(pytesseract)

        try:
            document = fitz.open(str(path))
        except Exception as exc:
            logger.warning("Failed to open PDF for OCR %s: %s", path.name, exc)
            raise DocumentOcrError(
                reason="The PDF file could not be opened for OCR",
                filename=path.name,
            ) from exc

        pages: list[str] = []
        try:
            for page_index, page in enumerate(document, start=1):
                try:
                    pix = page.get_pixmap(dpi=200)
                    image = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    text = pytesseract.image_to_string(image)
                except Exception as exc:
                    logger.warning(
                        "OCR failed on page %d of %s: %s",
                        page_index,
                        path.name,
                        exc,
                    )
                    text = ""
                pages.append(f"--- Page {page_index} ---\n{text}")
            document.close()
        except Exception as exc:
            document.close()
            logger.warning("Unexpected OCR error for %s: %s", path.name, exc)
            raise DocumentOcrError(
                reason="OCR could not read the PDF",
                filename=path.name,
            ) from exc

        return self._validate_ocr_text("\n\n".join(pages), path.name)

    def _configure_tesseract(self, pytesseract_module) -> None:
        """Point pytesseract at the Tesseract binary.

        Uses PATH first; falls back to the standard Windows install location.
        """
        if self._tesseract_cmd is not None:
            pytesseract_module.pytesseract.tesseract_cmd = self._tesseract_cmd
            return

        import shutil

        on_path = shutil.which("tesseract")
        if on_path:
            self._tesseract_cmd = on_path
            pytesseract_module.pytesseract.tesseract_cmd = on_path
            return

        for candidate in _TESSERACT_WINDOWS_PATHS:
            if Path(candidate).exists():
                self._tesseract_cmd = candidate
                pytesseract_module.pytesseract.tesseract_cmd = candidate
                return

        # Leave pytesseract's default (PATH) in place; the OCR call will fail
        # with a clear error if Tesseract is genuinely missing.
        self._tesseract_cmd = "tesseract"
        pytesseract_module.pytesseract.tesseract_cmd = "tesseract"

    @staticmethod
    def _validate_ocr_text(raw_text: str, filename: str) -> str:
        """Ensure OCR produced usable text; never fabricate."""
        stripped = (raw_text or "").strip()
        if not stripped:
            raise DocumentOcrError(
                reason="OCR produced no readable text",
                filename=filename,
            )
        logger.info("OCR extracted %d characters from %s", len(stripped), filename)
        return stripped