import sys
sys.path.insert(0, '.')
from app.services.scheme_retrieval_service import get_scheme_retrieval_service

service = get_scheme_retrieval_service()
queries = [
    'I need a government scheme related to PM Gramin',
    'PM Gramin scheme',
]
for q in queries:
    print(f'Query: {q}')
    results = service.retrieve(q, top_k=10)
    for i, r in enumerate(results, 1):
        print(f'  {i}. {r["scheme_name"]} (score={r["score"]:.4f})')
    print()
