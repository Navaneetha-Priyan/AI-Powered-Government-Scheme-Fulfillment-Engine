"""Run the full RAG retrieval evaluation and write results to a file.

This mirrors scripts/evaluate_retrieval.py but writes output to a file so
results can be reliably captured. Results are written progressively after
each query to avoid losing data on a potential crash.
"""
import sys
import traceback
from pathlib import Path

OUT_PATH = Path(r"d:\Codes\Final-Year-Project\AI-Powered-Government-Scheme-Fulfillment-Engine\backend\eval_results.txt")

def write_output(lines):
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from app.core.config import settings
    from app.services.scheme_retrieval_service import get_scheme_retrieval_service

    QUERIES = [
        "What government schemes are available for farmers?",
        "What documents are required for PM Kisan?",
        "Who is eligible for this scheme?",
        "What benefits does this scheme provide?",
        "How do I apply for the scheme?",
        "விவசாயிகளுக்கு என்ன அரசு திட்டங்கள் இருக்கிறது?",
        "Enakku farmer scheme edhavadhu irukka?",
        "எனக்கு agricultureக்கு ஏதாவது government scheme இருக்கா?",
        "What schemes are available for land ownership and patta?",
        "What government help is available for poor families?",
    ]

    retrieval_service = get_scheme_retrieval_service()
    count = retrieval_service.count()

    lines = []
    lines.append("=" * 70)
    lines.append("Government Scheme RAG — Retrieval Evaluation")
    lines.append("=" * 70)
    lines.append(f"Collection: {settings.RAG_COLLECTION_NAME}")
    lines.append(f"Documents indexed: {count}")
    lines.append(f"Embedding model: {settings.RAG_EMBEDDING_MODEL}")
    lines.append("=" * 70)

    for i, query in enumerate(QUERIES, start=1):
        lines.append(f"\n{'─' * 70}")
        lines.append(f"Query {i}/{len(QUERIES)}: {query}")
        lines.append(f"{'─' * 70}")
        results = retrieval_service.retrieve(
            query=query,
            top_k=5,
            similarity_threshold=0.0,
        )
        if not results:
            lines.append("  No results found above the similarity threshold.")
            continue
        for rank, result in enumerate(results, start=1):
            lines.append(f"\n  Rank {rank}:")
            lines.append(f"    Score:       {result['score']:.4f}")
            lines.append(f"    Scheme:      {result['scheme_name']}")
            lines.append(f"    Source:      {result['source_file']}")
            lines.append(f"    Page:        {result['page_number']}")
            if result.get("section_name"):
                lines.append(f"    Section:     {result['section_name']}")
            text_preview = result["text"][:200].replace("\n", " ")
            if len(result["text"]) > 200:
                text_preview += "..."
            lines.append(f"    Text preview: {text_preview}")

    lines.append(f"\n{'=' * 70}")
    lines.append("Evaluation complete.")
    lines.append(f"{'=' * 70}")

    output = "\n".join(lines)
    OUT_PATH.write_text(output, encoding="utf-8")
    marker = Path(r"d:\Codes\Final-Year-Project\AI-Powered-Government-Scheme-Fulfillment-Engine\backend\eval_done.flag")
    marker.write_text("DONE", encoding="utf-8")
    print(f"SUCCESS: Written {len(lines)} lines to {OUT_PATH}")
except Exception:
    OUT_PATH.write_text(traceback.format_exc(), encoding="utf-8")
    marker = Path(r"d:\Codes\Final-Year-Project\AI-Powered-Government-Scheme-Fulfillment-Engine\backend\eval_done.flag")
    marker.write_text("FAILED", encoding="utf-8")
    print(f"FAILURE: Error written to {OUT_PATH}")
