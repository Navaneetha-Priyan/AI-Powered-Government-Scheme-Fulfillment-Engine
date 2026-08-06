# Module 4 Installation and Testing

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

The eligibility and recommendation engine uses:
- FastAPI for authenticated APIs
- SQLAlchemy and Alembic for persistence
- Existing citizen, profile, DigiLocker, and scheme repositories
- Optional semantic search via the Module 3 vector store

## Tests

Run the full backend suite:

```bash
pytest
```

Run only the Module 4 tests:

```bash
pytest tests/unit/test_recommendation_engine.py tests/integration/test_recommendation_api.py
```

## Notes

- The recommendation service falls back to relational scheme lookups when ChromaDB is unavailable.
- Authenticated requests are required for all Module 4 endpoints.
- The recommendation history endpoint is order-sensitive in FastAPI, so static routes must be registered before the dynamic recommendation detail route.