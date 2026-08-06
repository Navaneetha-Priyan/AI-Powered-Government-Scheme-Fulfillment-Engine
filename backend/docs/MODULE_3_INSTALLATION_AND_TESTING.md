# Module 3 Installation and Testing

## Install

From the backend folder:

```bash
pip install -r requirements.txt
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

The schema knowledge base uses:
- MySQL for relational data
- PyMuPDF for PDF extraction
- Sentence Transformers for embeddings
- ChromaDB for vector search

## Tests

Run the full backend suite:

```bash
pytest
```

Run only the Module 3 tests:

```bash
pytest tests/unit/test_scheme_knowledge_base.py tests/integration/test_scheme_api.py
```

## Notes

- Background processing uses FastAPI background tasks.
- If the transformer model cannot be loaded, the embedding layer falls back to a deterministic local encoder so tests and offline development still work.
