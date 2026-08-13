import sys
sys.path.insert(0, '.')
from app.services.scheme_retrieval_service import get_scheme_retrieval_service

service = get_scheme_retrieval_service()
queries = [
    'I need government scheme related to PM Kisan',
    'government scheme for agriculture loans',
    'I need government schemes for agriculture',
    'Government assistance for farmers?',
    'I need a government scheme related to PM Gramin',
]
for q in queries:
    print(f'Query: {q}')
    results = service.retrieve(q, top_k=5)
    for i, r in enumerate(results, 1):
        print(f'  {i}. {r["scheme_name"]} (score={r["score"]:.4f})')
    print()
