from unittest.mock import MagicMock, patch
from app.services.scheme_retrieval_service import SchemeRetrievalService

mock_collection = MagicMock()
mock_collection.query.return_value = {
    'documents': [[
        'PM Vishwakarma Yojana text here',
        'Pradhan Mantri Matru Vandana Yojana PMMVY text',
        'Pradhan Mantri Awas Yojana Urban PMAY U text',
        'Jal Jeevan Mission 2 text',
        'Pradhan Mantri Jan Dhan Yojana PMJDY text',
    ]],
    'metadatas': [[
        {'scheme_name': 'PM Vishwakarma Yojana', 'source_file': 'PM_Vishwakarma_Yojana.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'vw-1'},
        {'scheme_name': 'Pradhan Mantri Matru Vandana Yojana PMMVY', 'source_file': 'Pradhan_Mantri_Matru_Vandana_Yojana_PMMVY.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'pmmvy-1'},
        {'scheme_name': 'Pradhan Mantri Awas Yojana Urban PMAY U', 'source_file': 'Pradhan_Mantri_Awas_Yojana_-_Urban_PMAY-U.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'pmay-1'},
        {'scheme_name': 'Jal Jeevan Mission 2', 'source_file': 'Jal_Jeevan_Mission_2.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'jjm-1'},
        {'scheme_name': 'Pradhan Mantri Jan Dhan Yojana PMJDY', 'source_file': 'Pradhan_Mantri_Jan_Dhan_Yojana_PMJDY.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'pmjdy-1'},
    ]],
    'distances': [[0.36, 0.38, 0.40, 0.42, 0.45]],
}
mock_collection.get.return_value = {'documents': [], 'metadatas': []}
mock_embedding_service = MagicMock()
mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

with patch.object(SchemeRetrievalService, '_get_or_create_collection', return_value=mock_collection):
    service = SchemeRetrievalService(embedding_service=mock_embedding_service)
    
    # Patch _rerank_and_diversify to inspect
    original = service._rerank_and_diversify
    def patched(query, items, top_k, similarity_threshold):
        from app.services.scheme_retrieval_service import _canonical_scheme_key
        for item in items:
            scheme_key = item.get('_scheme_key') or _canonical_scheme_key(
                item.get('scheme_name', ''), item.get('source_file', '')
            )
            cs = service._combined_score(query, item)
            print(f'  Item: {item.get("scheme_name")} semantic={item.get("score")} combined={cs} key={scheme_key}')
        return original(query, items, top_k, similarity_threshold)
    
    service._rerank_and_diversify = patched
    results = service.retrieve('I need a government scheme related to PM Gramin', top_k=5)
    print('---RESULTS---')
    for r in results:
        print(r['scheme_name'], '->', r['score'])
