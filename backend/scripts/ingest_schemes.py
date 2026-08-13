"""Bulk ingestion script for Government Scheme RAG.

Discovers all PDF files in the configured RAG PDF directory, extracts text,
chunks documents, generates embeddings, and stores them in ChromaDB.

Usage:
    python -m scripts.ingest_schemes
    python -m scripts.ingest_schemes --pdf-dir data/schemes
    python -m scripts.ingest_schemes --clear  # rebuild the index from scratch
    python -m scripts.ingest_schemes --dry-run  # show what would be ingested

This script reuses the existing:
- PdfTextExtractor (PyMuPDF text extraction)
- SchemeProcessingService (text cleaning, section detection, chunking)
- SchemeEmbeddingService (Sentence Transformers embeddings)
- SchemeRetrievalService (ChromaDB vector store)
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import List
from uuid import uuid4

# Ensure the backend directory is on the path when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import DocumentTextExtractionError
from app.services.pdf_text_extractor import PdfTextExtractor
from app.services.scheme_embedding_service import SchemeEmbeddingService
from app.services.scheme_processing_service import SchemeProcessingService
from app.services.scheme_retrieval_service import (
    SchemeRetrievalService,
    _derive_scheme_name,
)

logger = get_logger(__name__)


def discover_pdfs(pdf_dir: str) -> List[Path]:
    """Discover all .pdf files in the given directory (non-recursive).

    If the configured directory does not exist or contains no PDFs, this
    function falls back to the parent ``data/`` directory so that PDFs
    placed directly in ``backend/data/`` are still discovered.
    """
    directory = Path(pdf_dir)
    if directory.exists():
        pdfs = sorted(directory.glob("*.pdf"))
        if pdfs:
            return pdfs

    # Fallback: check the parent directory (e.g. data/ if data/schemes/ is empty).
    fallback_dir = directory.parent
    if fallback_dir.exists() and fallback_dir != directory:
        logger.info(
            "No PDFs in %s; falling back to %s", directory, fallback_dir
        )
        pdfs = sorted(fallback_dir.glob("*.pdf"))
        if pdfs:
            return pdfs

    if not directory.exists():
        logger.warning("PDF directory does not exist: %s", directory)
    return []


def extract_text_with_fallback(
    extractor: PdfTextExtractor, file_path: str
) -> str:
    """Extract text from a PDF, falling back to OCR if needed."""
    try:
        return extractor.extract(file_path)
    except DocumentTextExtractionError as exc:
        logger.info(
            "PDF text extraction failed for %s (%s); trying OCR fallback",
            Path(file_path).name,
            exc.message,
        )
        try:
            from app.services.document_ocr_service import DocumentOcrService

            ocr_service = DocumentOcrService()
            return ocr_service.ocr_file(file_path)
        except Exception as ocr_exc:
            logger.warning(
                "OCR fallback also failed for %s: %s",
                Path(file_path).name,
                ocr_exc,
            )
            raise


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    """Split text into chunks of approximately ``chunk_size`` characters.

    Uses a simple sliding-window approach with overlap. Splits on paragraph
    boundaries when possible to avoid breaking mid-sentence.
    """
    if not text or not text.strip():
        return []

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        # Try to find a paragraph boundary near the end.
        if end < len(text):
            # Look for a newline or sentence boundary in the overlap region.
            search_start = max(start, end - chunk_overlap)
            boundary = -1
            for i in range(end, search_start, -1):
                if text[i - 1] in ".!?\n":
                    boundary = i
                    break
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def process_pdf(
    pdf_path: Path,
    extractor: PdfTextExtractor,
    processing_service: SchemeProcessingService,
    embedding_service: SchemeEmbeddingService,
    retrieval_service: SchemeRetrievalService,
    chunk_size: int,
    chunk_overlap: int,
) -> dict:
    """Process a single PDF: extract, chunk, embed, store.

    Returns a summary dict with processing statistics.
    """
    filename = pdf_path.name
    scheme_name = _derive_scheme_name(filename)
    result = {
        "filename": filename,
        "scheme_name": scheme_name,
        "status": "pending",
        "pages": 0,
        "chunks": 0,
        "error": None,
    }

    try:
        # 1) Extract text (with OCR fallback).
        raw_text = extract_text_with_fallback(extractor, str(pdf_path))

        # 2) Parse page boundaries from the extracted text.
        # PdfTextExtractor uses "--- Page N ---" separators.
        page_pattern = re.compile(r"--- Page (\d+) ---\s*\n")
        page_matches = list(page_pattern.finditer(raw_text))

        if page_matches:
            pages = []
            for i, match in enumerate(page_matches):
                page_num = int(match.group(1))
                start = match.end()
                end = page_matches[i + 1].start() if i + 1 < len(page_matches) else len(raw_text)
                page_text = raw_text[start:end].strip()
                if page_text:
                    pages.append({"page_number": page_num, "text": page_text})
            result["pages"] = len(pages)
        else:
            # No page markers — treat the whole text as one page.
            pages = [{"page_number": 1, "text": raw_text.strip()}]
            result["pages"] = 1

        if not pages:
            result["status"] = "failed"
            result["error"] = "No extractable text found"
            return result

        # 3) Chunk each page.
        chunk_payloads = []
        for page in pages:
            page_chunks = chunk_text(
                page["text"], chunk_size, chunk_overlap
            )
            for chunk_text_value in page_chunks:
                chunk_payloads.append(
                    {
                        "chunk_id": str(uuid4()),
                        "text": chunk_text_value,
                        "scheme_name": scheme_name,
                        "source_file": filename,
                        "page_number": page["page_number"],
                        "document_type": "government_scheme",
                        "section_name": "",
                    }
                )

        result["chunks"] = len(chunk_payloads)

        if not chunk_payloads:
            result["status"] = "failed"
            result["error"] = "No chunks could be generated"
            return result

        # 4) Generate embeddings.
        embeddings = embedding_service.embed_texts(
            [
                retrieval_service._embedding_document_text(chunk)
                for chunk in chunk_payloads
            ]
        )

        if len(embeddings) != len(chunk_payloads):
            result["status"] = "failed"
            result["error"] = (
                f"Embedding count mismatch: {len(embeddings)} vs "
                f"{len(chunk_payloads)} chunks"
            )
            return result

        # 5) Store in ChromaDB.
        stored = retrieval_service.add_chunks(chunk_payloads, embeddings)
        result["chunks_stored"] = stored
        result["status"] = "success"

    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        logger.exception("Failed to process %s: %s", filename, exc)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Ingest government scheme PDFs into the RAG vector store."
    )
    parser.add_argument(
        "--pdf-dir",
        default=None,
        help="Directory containing scheme PDFs (default: RAG_PDF_DIRECTORY from config).",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the existing RAG collection before ingesting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without actually processing.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Override RAG_CHUNK_SIZE.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Override RAG_CHUNK_OVERLAP.",
    )
    args = parser.parse_args()

    pdf_dir = args.pdf_dir or settings.RAG_PDF_DIRECTORY
    chunk_size = args.chunk_size or settings.RAG_CHUNK_SIZE
    chunk_overlap = args.chunk_overlap or settings.RAG_CHUNK_OVERLAP

    print("=" * 60)
    print("Government Scheme RAG Ingestion")
    print("=" * 60)
    print(f"PDF directory: {pdf_dir}")
    print(f"Chunk size: {chunk_size} chars")
    print(f"Chunk overlap: {chunk_overlap} chars")
    print(f"Embedding model: {settings.RAG_EMBEDDING_MODEL}")
    print(f"ChromaDB collection: {settings.RAG_COLLECTION_NAME}")
    print(f"Persist directory: {settings.RAG_PERSIST_DIRECTORY}")
    print("=" * 60)

    # Discover PDFs.
    pdfs = discover_pdfs(pdf_dir)
    if not pdfs:
        print(f"\nNo PDF files found in {pdf_dir}")
        print("Please ensure government scheme PDFs are placed in the configured directory.")
        return

    print(f"\nPDF files found: {len(pdfs)}")

    if args.dry_run:
        print("\n--- Dry Run (no processing) ---")
        for pdf in pdfs:
            scheme_name = _derive_scheme_name(pdf.name)
            print(f"  {pdf.name} -> {scheme_name}")
        print(f"\nTotal: {len(pdfs)} PDFs would be ingested.")
        return

    # Initialize services.
    extractor = PdfTextExtractor()
    processing_service = SchemeProcessingService()
    embedding_service = SchemeEmbeddingService(
        model_name=settings.RAG_EMBEDDING_MODEL
    )
    retrieval_service = SchemeRetrievalService(embedding_service)

    # Optionally clear the collection.
    if args.clear:
        print("\nClearing existing RAG collection...")
        deleted = retrieval_service.delete_all()
        print(f"Deleted {deleted} existing chunks.")

    # Process each PDF.
    print(f"\nProcessing {len(pdfs)} PDFs...")
    start_time = time.time()
    results = []
    for i, pdf in enumerate(pdfs, start=1):
        print(f"  [{i}/{len(pdfs)}] Processing {pdf.name}...", end=" ", flush=True)
        result = process_pdf(
            pdf,
            extractor,
            processing_service,
            embedding_service,
            retrieval_service,
            chunk_size,
            chunk_overlap,
        )
        results.append(result)
        if result["status"] == "success":
            print(
                f"OK ({result['pages']} pages, {result['chunks']} chunks)"
            )
        else:
            print(f"FAILED ({result.get('error', 'unknown error')})")

    elapsed = time.time() - start_time

    # Summary.
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    total_pages = sum(r.get("pages", 0) for r in successful)
    total_chunks = sum(r.get("chunks", 0) for r in successful)
    total_stored = sum(r.get("chunks_stored", 0) for r in successful)

    print("\n" + "=" * 60)
    print("Ingestion Summary")
    print("=" * 60)
    print(f"PDF files found: {len(pdfs)}")
    print(f"Successfully processed: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total pages: {total_pages}")
    print(f"Total chunks: {total_chunks}")
    print(f"Embeddings generated: {total_stored}")
    print(f"Vector store: ChromaDB ({settings.RAG_COLLECTION_NAME})")
    print(f"Time elapsed: {elapsed:.1f}s")

    if failed:
        print("\nFailed files:")
        for r in failed:
            print(f"  * {r['filename']}: {r.get('error', 'unknown')}")

    print("\nIngestion completed.")
    if failed:
        print(f"WARNING: {len(failed)} file(s) failed to process.")
        sys.exit(1)


if __name__ == "__main__":
    main()
