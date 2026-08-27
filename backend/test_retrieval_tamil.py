"""Quick retrieval test for Tamil/Tanglish/English queries.

Run after re-ingesting PDFs with BGE-M3:
    python -m test_retrieval_tamil
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.scheme_retrieval_service import get_scheme_retrieval_service

QUERIES = [
    "விவசாயிகளுக்கு என்ன அரசு திட்டங்கள் இருக்கிறது?",
    "Enakku farmer scheme edhavadhu irukka?",
    "What government schemes are available for farmers?",
]

service = get_scheme_retrieval_service()
print(f"Collection count: {service.count()}\n")

for query in QUERIES:
    print("=" * 70)
    print(f"Query: {query}")
    print("=" * 70)
    results = service.retrieve(query, top_k=5)
    if not results:
        print("  No results.\n")
        continue
    for rank, r in enumerate(results, 1):
        print(
            f"  {rank}. score={r['score']:.4f} | {r['scheme_name']} | {r['source_file']} | page {r['page_number']}"
        )
        if r.get("section_name"):
            print(f"     section: {r['section_name']}")
    print()
