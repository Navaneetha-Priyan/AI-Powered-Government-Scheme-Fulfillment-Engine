from unittest.mock import MagicMock, patch
from app.services.scheme_retrieval_service import SchemeRetrievalService

mock_collection = MagicMock()
mock_collection.query.return_value = {
    'documents': [[
        'National Agriculture Market for farmers.',
        'National Agriculture Market directory.',
        'National Agriculture Market trading portal.',
        'Micro irrigation support for farmers.',
    ]],
    'metadatas': [[
        {'scheme_name': 'e NAM National Agriculture Market', 'source_file': 'e-NAM_National_Agriculture_Market.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'enam-1'},
        {'scheme_name': 'e NAM National Agriculture Market 2', 'source_file': 'e-NAM_National_Agriculture_Market_2.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'enam-2'},
        {'scheme_name': 'e NAM National Agriculture Market 3', 'source_file': 'e-NAM_National_Agriculture_Market_3.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'enam-3'},
        {'scheme_name': 'Pradhan Mantri Krishi Sinchayee Yojana PMKSY', 'source_file': 'pmksy.pdf', 'page_number': 1, 'document_type': 'government_scheme', 'section_name': '', 'chunk_id': 'pmksy-1'},
    ]],
    'distances': [[0.05, 0.06, 0.07, 0.18]],
}
mock_collection.get.return_value = {'documents': [], 'metadatas': []}
mock_embedding_service = MagicMock()
mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

with patch.object(SchemeRetrievalService, '_get_or_create_collection', return_value=mock_collection):
    service = SchemeRetrievalService(embedding_service=mock_embedding_service)
    results = service.retrieve('agriculture schemes for farmers', top_k=3)
    for r in results:
        print(r['scheme_name'], '->', r['score'], 'key=', r.get('_scheme_key', 'N/A'))
