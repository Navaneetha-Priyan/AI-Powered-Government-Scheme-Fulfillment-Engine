"""Retrieval evaluation script for the Government Scheme RAG system.

Runs a set of representative queries against the indexed government-scheme
PDFs and prints the top retrieval results for each query.

Usage:
    python -m scripts.evaluate_retrieval
    python -m scripts.evaluate_retrieval --top-k 10
    python -m scripts.evaluate_retrieval --queries queries.txt

This script requires that the RAG ingestion has already been run:
    python -m scripts.ingest_schemes
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the backend directory is on the path when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging import get_logger
from app.services.scheme_retrieval_service import get_scheme_retrieval_service

logger = get_logger(__name__)

DEFAULT_QUERIES = [
    # English queries
    "What government schemes are available for farmers?",
    "What documents are required for PM Kisan?",
    "Who is eligible for this scheme?",
    "What benefits does this scheme provide?",
    "How do I apply for the scheme?",
    # Tamil queries
    "விவசாயிகளுக்கு என்ன அரசு திட்டங்கள் இருக்கிறது?",
    # Tanglish queries
    "Enakku farmer scheme edhavadhu irukka?",
    # Tamil-English code-mixed queries
    "எனக்கு agricultureக்கு ஏதாவது government scheme இருக்கா?",
    # Land-related assistance
    "What schemes are available for land ownership and patta?",
    # Low-income citizen assistance
    "What government help is available for poor families?",
]


def run_evaluation(
    queries: list[str],
    top_k: int,
    similarity_threshold: float,
) -> None:
    """Run retrieval evaluation for a list of queries."""
    retrieval_service = get_scheme_retrieval_service()

    collection_count = retrieval_service.count()
    print("=" * 70)
    print("Government Scheme RAG — Retrieval Evaluation")
    print("=" * 70)
    print(f"Collection: {settings.RAG_COLLECTION_NAME}")
    print(f"Documents indexed: {collection_count}")
    print(f"Top-K: {top_k}")
    print(f"Similarity threshold: {similarity_threshold}")
    print("=" * 70)

    if collection_count == 0:
        print("\nWARNING: No documents are indexed in the RAG collection.")
        print("Please run ingestion first:")
        print("  python -m scripts.ingest_schemes")
        return

    for i, query in enumerate(queries, start=1):
        print(f"\n{'─' * 70}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'─' * 70}")

        results = retrieval_service.retrieve(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if not results:
            print("  No results found above the similarity threshold.")
            continue

        for rank, result in enumerate(results, start=1):
            print(f"\n  Rank {rank}:")
            print(f"    Score:       {result['score']:.4f}")
            print(f"    Scheme:      {result['scheme_name']}")
            print(f"    Source:      {result['source_file']}")
            print(f"    Page:        {result['page_number']}")
            if result.get("section_name"):
                print(f"    Section:     {result['section_name']}")
            # Print a preview of the chunk text (first 200 chars).
            text_preview = result["text"][:200].replace("\n", " ")
            if len(result["text"]) > 200:
                text_preview += "..."
            print(f"    Text preview: {text_preview}")

    print(f"\n{'=' * 70}")
    print("Evaluation complete.")
    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate RAG retrieval quality for government scheme queries."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top results to retrieve per query (default: 5).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum similarity score threshold (default: 0.0).",
    )
    parser.add_argument(
        "--queries",
        type=str,
        default=None,
        help="Path to a text file with one query per line.",
    )
    args = parser.parse_args()

    if args.queries:
        queries_path = Path(args.queries)
        if not queries_path.exists():
            print(f"Queries file not found: {queries_path}")
            sys.exit(1)
        queries = [
            line.strip()
            for line in queries_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        queries = DEFAULT_QUERIES

    run_evaluation(
        queries=queries,
        top_k=args.top_k,
        similarity_threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
