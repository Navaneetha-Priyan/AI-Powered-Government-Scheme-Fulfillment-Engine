#!/usr/bin/env python3
"""Sync the MySQL ``government_schemes`` catalog with the existing Chroma RAG corpus.

Offline data-integration utility. It does NOT re-chunk, re-embed, or delete
anything. It restores the coupling that ``RecommendationService.generate()``
relies on:

    semantic_search (Chroma) -> carries ``scheme_id`` in metadata
        -> GovernmentSchemeRepository.get(scheme_id) -> MySQL ``government_schemes``

Steps
-----
1. Reads the distinct schemes already indexed in the existing ChromaDB RAG
   collection ``government_scheme_documents`` (settings.RAG_*).
2. Creates one ``government_schemes`` catalog row per distinct canonical scheme
   using the existing service path ``GovernmentSchemeService.create_scheme``
   (the same code behind ``POST /api/schemes``). It is idempotent: scheme names
   that already exist are reused, never duplicated.
3. Back-links each indexed chunk to its catalog record by adding the matching
   ``scheme_id`` into the existing Chroma metadata. The Chroma embeddings,
   documents, and chunk ids are preserved untouched.

Usage:
    python -m scripts.sync_scheme_catalog --dry-run   # preview only
    python -m scripts.sync_scheme_catalog --apply     # write DB + Chroma metadata
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

# Ensure the backend directory is on the path when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.database.connection import SessionLocal  # noqa: E402
from app.exceptions.exceptions import DuplicateSchemeError  # noqa: E402
from app.repositories.government_scheme_repository import GovernmentSchemeRepository  # noqa: E402
from app.services.government_scheme_service import GovernmentSchemeService  # noqa: E402
from app.services.scheme_retrieval_service import _canonical_scheme_key  # noqa: E402

logger = get_logger(__name__)


# ── Lightweight catalog metadata derivation from the corpus ────────────────
# These fields are required by the GovernmentScheme model. They are derived
# deterministically from the source PDF/scheme names already present in the
# RAG corpus. They do not affect retrieval, ranking, or eligibility logic.

_CATEGORY_KEYWORDS = [
    ("Agriculture", ["agriculture", "agri", "kisan", "krishi", "kharif", "crop",
                     "horticulture", "mechanization", "midh", "smam", "rkvy", "pkvy"]),
    ("Food & Nutrition", ["food", "public distribution", "nutrition", "anganwadi", "poshan"]),
    ("Transport", ["bus", "transport"]),
    ("Housing", ["housing", "awas"]),
    ("Education", ["scholarship", "education", "post matric"]),
    ("Insurance", ["insurance", "bima", "pmfby"]),
    ("Energy & Water", ["energy", "solar", "sinchayee", "kum", "ujjwala", "jal jeevan"]),
    ("Women & Child", ["women", "woman", "matru", "vandana"]),
    ("Financial Inclusion", ["jan dhan", "bank"]),
    ("Sanitation", ["swachh", "sanitation", "gramin"]),
    ("Livelihood", ["vishwakarma", "street vendor", "svanidhi"]),
]


def _looks_like_state_scheme(text: str) -> bool:
    return "tamil nadu" in text or "tn government" in text


def derive_catalog_fields(scheme_name: str, source_files: set[str]) -> tuple[str, str, str]:
    """Return ``(category, department, government_level)`` for a scheme."""
    haystack = (scheme_name + " " + " ".join(sorted(source_files))).lower()
    if _looks_like_state_scheme(haystack):
        level = "state"
        department = "Government of Tamil Nadu"
    else:
        level = "central"
        department = "Government of India"

    category = "General Welfare"
    for cat, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            category = cat
            break
    return category, department, level


def load_rag_corpus():
    """Load ids/metadatas/documents from the existing RAG Chroma collection."""
    import chromadb

    client = chromadb.PersistentClient(path=settings.RAG_PERSIST_DIRECTORY)
    collection = client.get_collection(settings.RAG_COLLECTION_NAME)
    return collection, collection.get(include=["metadatas", "documents"])


def build_corpus_schemas(ids, metadatas, documents) -> list[dict]:
    """Group Chroma chunks into distinct canonical schemes.

    Returns a list of dicts (sorted by display name) with:
        canonical, scheme_name, source_files, chunk_count, description
    """
    grouped: dict[str, dict] = defaultdict(lambda: {
        "scheme_names": set(),
        "source_files": set(),
        "chunk_count": 0,
        "first_chunk": "",
    })
    for meta, doc in zip(metadatas, documents):
        scheme_name = meta.get("scheme_name", "") or ""
        canonical = (
            meta.get("normalized_scheme_name")
            or _canonical_scheme_key(scheme_name, meta.get("source_file", "") or "")
        )
        entry = grouped[canonical]
        if scheme_name:
            entry["scheme_names"].add(scheme_name)
        if meta.get("source_file"):
            entry["source_files"].add(meta["source_file"])
        entry["chunk_count"] += 1
        if not entry["first_chunk"] and doc and doc.strip():
            entry["first_chunk"] = doc.strip()

    schemas = []
    for canonical, entry in grouped.items():
        # Human-readable display name: shortest variant (e.g. drops the
        # trailing " 2"/" 3" version suffix used for the same PDF corpus).
        scheme_name = min(entry["scheme_names"] or {canonical}, key=lambda n: (len(n), n))
        description = entry["first_chunk"][:500] or f"Government scheme: {scheme_name}."
        schemas.append(
            {
                "canonical": canonical,
                "scheme_name": scheme_name,
                "source_files": entry["source_files"],
                "chunk_count": entry["chunk_count"],
                "description": description,
            }
        )
    schemas.sort(key=lambda s: s["scheme_name"].lower())
    return schemas


def create_or_reuse_catalog_row(db, service, repo, schema: dict) -> tuple[str, str]:
    """Create one catalog row via the existing service path (idempotent).

    Returns ``(scheme_id, action)`` where action is "created" or "existing".
    """
    existing = repo.get_by_name(schema["scheme_name"])
    if existing is not None:
        return existing.id, "existing"

    category, department, government_level = derive_catalog_fields(
        schema["scheme_name"], schema["source_files"]
    )
    payload = {
        "scheme_name": schema["scheme_name"],
        "description": schema["description"],
        "category": category,
        "department": department,
        "government_level": government_level,
        "state": "Tamil Nadu" if government_level == "state" else None,
        "benefits": None,
        "eligibility_summary": None,
        "required_documents": None,
        "application_process": None,
        "official_link": None,
        "language": "en",
        "status": "active",
    }
    try:
        scheme = service.create_scheme(payload)
        return scheme.id, "created"
    except DuplicateSchemeError:
        # Rare race: another process created it between the check and now.
        existing = repo.get_by_name(schema["scheme_name"])
        if existing is not None:
            return existing.id, "existing"
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync MySQL government_schemes catalog with the existing Chroma RAG corpus."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (create catalog rows + write scheme_id into Chroma metadata). "
             "Without this flag only a preview is printed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit preview mode (default when --apply is not given).",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Scheme Catalog <-> RAG Corpus Sync")
    print("=" * 70)
    print(f"Chroma collection : {settings.RAG_COLLECTION_NAME}")
    print(f"Chroma persist dir: {settings.RAG_PERSIST_DIRECTORY}")
    print(f"Mode              : {'APPLY' if args.apply else 'DRY RUN (no writes)'}")
    print("=" * 70)

    collection, data = load_rag_corpus()
    ids = data["ids"]
    metadatas = data["metadatas"]
    documents = data["documents"]
    print(f"Chunks indexed in RAG collection: {len(ids)}")
    if not ids:
        print("Nothing to sync — the RAG collection is empty.")
        return

    schemas = build_corpus_schemas(ids, metadatas, documents)
    print(f"Distinct canonical schemes in corpus: {len(schemas)}")

    db = SessionLocal()
    try:
        service = GovernmentSchemeService(db)
        repo = GovernmentSchemeRepository(db)

        scheme_id_by_canonical: dict[str, str] = {}
        created = 0
        existing = 0
        print("\n--- Catalog rows ---")
        for schema in schemas:
            if args.apply:
                scheme_id, action = create_or_reuse_catalog_row(db, service, repo, schema)
            else:
                # Preview: is it already present?
                row = repo.get_by_name(schema["scheme_name"])
                scheme_id = row.id if row else "(would-create)"
                action = "existing" if row else "would-create"
            scheme_id_by_canonical[schema["canonical"]] = scheme_id
            if action == "created":
                created += 1
            elif action == "existing":
                existing += 1
            print(
                f"  [{action:>12}] {schema['scheme_name']}  "
                f"(canonical='{schema['canonical']}', chunks={schema['chunk_count']}, "
                f"id={scheme_id})"
            )

        if args.apply:
            # Back-link Chroma metadata: add scheme_id, preserving everything else.
            print("\n--- Back-linking Chroma metadata (scheme_id) ---")
            new_metadatas = []
            for meta in metadatas:
                scheme_name = meta.get("scheme_name", "") or ""
                canonical = (
                    meta.get("normalized_scheme_name")
                    or _canonical_scheme_key(scheme_name, meta.get("source_file", "") or "")
                )
                updated = dict(meta)
                updated["scheme_id"] = scheme_id_by_canonical[canonical]
                new_metadatas.append(updated)
            collection.update(ids=ids, metadatas=new_metadatas)
            print(f"  Updated metadata for {len(new_metadatas)} chunks.")

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  Catalog rows created : {created}")
        print(f"  Catalog rows existing: {existing}")
        print(f"  Catalog total        : {existing + created}")
        if args.apply:
            print("  Chroma metadata back-link: applied (embeddings/documents preserved)")
        else:
            print("  Chroma metadata back-link: skipped (dry run)")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()