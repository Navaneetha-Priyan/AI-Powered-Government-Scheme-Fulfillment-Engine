# Module 3 API

All Module 3 routes are protected by the existing JWT authentication layer.

## Scheme APIs

### Create Scheme

`POST /api/schemes`

### List Schemes

`GET /api/schemes`

Optional query parameters:
- `skip`
- `limit`
- `category`
- `status`
- `query`

### Get Scheme Details

`GET /api/schemes/{id}`

### Update Scheme

`PUT /api/schemes/{id}`

### Delete Scheme

`DELETE /api/schemes/{id}`

## Document APIs

### Upload PDF

`POST /api/schemes/{id}/documents/upload`

Returns the stored document metadata and starts background processing.

### Start Processing

`POST /api/documents/{id}/process`

### Get Processing Status

`GET /api/documents/{id}/status`

## Search API

### Semantic Search

`POST /api/search/schemes`

Request:

```json
{
  "query": "financial support for farmers affected by flood",
  "limit": 5,
  "category": "agriculture"
}
```

Response data includes:
- `scheme_id`
- `scheme_name`
- `category`
- `department`
- `similarity_score`
- `matched_content`
- `relevant_content`
- `benefits`
- `page_number`
- `section_name`
- `document_id`

## Example Flow

1. Create a scheme.
2. Upload a PDF.
3. Wait for processing to finish.
4. Search by a user query.
5. Return ranked semantic matches.
