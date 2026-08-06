# Module 3 Database Schema

Module 3 extends the existing MySQL database with scheme knowledge-base tables.

## Tables

### government_schemes

Stores the canonical scheme master record.

Key fields:
- `id`
- `scheme_name`
- `description`
- `category`
- `department`
- `government_level`
- `state`
- `benefits`
- `eligibility_summary`
- `required_documents`
- `application_process`
- `official_link`
- `language`
- `status`
- `is_deleted`
- `created_at`
- `updated_at`

### scheme_documents

Stores uploaded PDF metadata and processing state.

Key fields:
- `id`
- `scheme_id`
- `file_name`
- `file_path`
- `file_size`
- `uploaded_by`
- `version`
- `processing_status`
- `processing_error`
- `created_at`
- `updated_at`

### scheme_chunks

Stores chunked sections and vector identifiers.

Key fields:
- `id`
- `scheme_id`
- `document_id`
- `chunk_text`
- `page_number`
- `section_name`
- `embedding_id`
- `token_count`
- `created_at`

## Relationships

- One scheme has many documents.
- One scheme has many chunks.
- One document has many chunks.
- Chunks are written to ChromaDB using the same `embedding_id` value.

## Indexing Strategy

- Unique index on `scheme_name`.
- Filter indexes on `category`, `department`, and `status`.
- Version index on `scheme_id + version` for documents.
- Lookup indexes on `scheme_id`, `document_id`, and `embedding_id` for chunk processing.
