# Module 3: Government Scheme Knowledge Base

Module 3 provides an authenticated knowledge base for government schemes.

```text
Admin creates scheme -> uploads PDF -> process document -> extract text
-> chunk content -> embed/store in ChromaDB -> semantic scheme search
```

## APIs

- `POST /api/schemes`, `GET /api/schemes`, `GET|PUT|DELETE /api/schemes/{id}`
- `POST /api/schemes/{id}/documents/upload`
- `POST /api/documents/{id}/process`, `GET /api/documents/{id}/status`
- `POST /api/search/schemes`

All APIs require the existing citizen JWT. Scheme records, uploaded-document
metadata, and extracted chunks are stored in MySQL. Vectors and searchable
metadata are stored in persistent ChromaDB storage under `storage/chromadb`.

Run `alembic upgrade head` after installing `backend/requirements.txt`.
