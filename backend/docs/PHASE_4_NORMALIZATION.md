# Phase 4: Multilingual, Dialect & Intent Normalization

Phase 4 adds a **normalization and intent-extraction layer** that converts raw
speech transcripts (from `POST /voice/transcribe`) into a structured
representation that later phases (eligibility engine, RAG) can consume.

The existing transcription pipeline is **unchanged**. Phase 4 only adds a new
endpoint and a new service on top of it.

---

## Overview

```
Flutter microphone
  → POST /voice/transcribe  (unchanged)
  → raw transcript (e.g. "enakku kaasu romba kammi, farmer scheme irukka?")
  → POST /voice/normalize  (NEW)
  → structured representation
  → eligibility / RAG (NOT in Phase 4)
```

`TextNormalizationService` is deliberately independent of:
- the database
- the eligibility engine
- RAG / vector store
- authentication
- the Flutter client

It ONLY converts a raw transcript into a structured query.

---

## Endpoint

### `POST /voice/normalize`

Protected by the existing **JWT authentication** (`Authorization: Bearer <token>`).

**Request schema** (`NormalizationRequest`):

```json
{
  "text": "raw transcript"
}
```

`text` must be non-empty and no longer than `NORMALIZE_MAX_TEXT_LENGTH`
(default 2000 characters). Oversized or empty inputs return HTTP 422.

**Response schema** (`NormalizationResponse`):

```json
{
  "language": "ta-en",
  "intent": "scheme_search",
  "normalized_text": "Looking for a farmer scheme with low income",
  "entities": {
    "occupation": "farmer",
    "income_status": "low"
  },
  "confidence": 0.92,
  "source": "llm"
}
```

| Field            | Type            | Description                                                                  |
|------------------|-----------------|------------------------------------------------------------------------------|
| `language`       | string          | `ta`, `en`, `ta-en`, or `unknown` (approximate classification).              |
| `intent`         | string          | One of `scheme_search`, `scheme_eligibility`, `application_status`, `document_requirement`, `profile_query`, `unknown`. |
| `normalized_text`| string          | Meaning-preserving normalized representation (no invented facts).            |
| `entities`       | object          | Extracted entities (see below). Only attributes present in the speech.       |
| `confidence`     | float (0..1)    | Confidence in the structured interpretation.                                 |
| `source`         | string          | `llm` (Ollama) or `heuristic` (deterministic fallback).                      |

---

## Pipeline

1. **Try the LLM (Ollama)** - a local, OpenAI-compatible `/v1/chat/completions`
   endpoint called via the already-installed `httpx` dependency. No API key or
   extra SDK is required.
2. **Parse & validate** the structured JSON response. If it is missing required
   fields, has invalid types, or is not valid JSON, it is treated as a failure.
3. **Heuristic fallback** - if Ollama is unavailable, times out, or returns an
   invalid response, a small deterministic rule-based analyzer produces a
   conservative structured result. The endpoint **never crashes** because the
   LLM is offline; it always returns a valid structured result.

---

## Language / Code-Switching Examples

The service understands standard Tamil, colloquial Tamil, regional slang,
English, Tanglish, and Tamil-English code-switching. It identifies the language
approximately as `ta`, `en`, `ta-en`, or `unknown`.

| Input                                                                 | Expected intent / entities                          |
|-----------------------------------------------------------------------|-----------------------------------------------------|
| `எனக்கு விவசாயத்திற்கு அரசு திட்டம் வேண்டும்`                            | `scheme_search`, occupation=farmer                   |
| `I need a government scheme for farming`                              | `scheme_search`, occupation=farmer                   |
| `எனக்கு farmer scheme ஏதாவது கிடைக்குமா?`                              | `scheme_search`, occupation=farmer                   |
| `enakku kaasu romba kammi, farmer scheme irukka?`                     | `scheme_search`, occupation=farmer, income=low       |
| `PM Kisan schemeக்கு நான் eligibleஆ?`                                 | `scheme_eligibility`, scheme_name=`PM Kisan`         |
| `எனக்கு துட்டு கம்மி, ஏதாவது உதவி கிடைக்குமா?`                          | `scheme_search`, income=low                          |

---

## Intents

- `scheme_search` - looking for a scheme.
- `scheme_eligibility` - asking whether they are eligible for a scheme.
- `application_status` - checking application/status.
- `document_requirement` - asking what documents are needed.
- `profile_query` - asking about their own profile.
- `unknown` - cannot confidently map the request.

---

## Entities

Possible entity keys (only those present in the speech are populated):

- `scheme_name`
- `occupation`
- `income_status`
- `land_ownership`
- `land_area`
- `crop`
- `location`
- `caste`
- `age`
- `gender`
- `document_type`

> **Important**: The service does **not** infer citizen attributes that are not
> present in the user's speech or existing profile. It never invents facts.

---

## System Prompt Behaviour

The LLM system prompt instructs the model to:
- preserve the user's actual meaning
- recognize colloquial Tamil and common Tamil slang
- normalize slang into standard semantic concepts (e.g. `thuttu`/`kaasu` → low income)
- understand English words embedded in Tamil sentences and Tanglish/code-switching
- never invent facts
- never change or assume citizen profile information
- set low confidence and use `unknown` when unsure
- return **only** valid JSON matching the expected schema

The model is told **not** to answer the user's question or recommend schemes; it
only interprets the query.

---

## Configuration

See `ENVIRONMENT_VARIABLES.md` for the full reference. Relevant variables:

| Variable                              | Default                | Description                                            |
|---------------------------------------|------------------------|--------------------------------------------------------|
| `OLLAMA_BASE_URL`                     | `http://localhost:11434` | Local Ollama server base URL.                        |
| `OLLAMA_MODEL`                        | `qwen2.5:7b`           | Ollama model used for normalization.                   |
| `OLLAMA_TIMEOUT`                      | `15.0`                 | HTTP request timeout (seconds).                        |
| `NORMALIZE_MAX_TEXT_LENGTH`           | `2000`                 | Max accepted input length (characters).                |
| `NORMALIZE_ENABLE_HEURISTIC_FALLBACK` | `True`                 | Enable the deterministic heuristic fallback.           |

---

## Security

- No logging of Aadhaar numbers, JWTs, or sensitive citizen profile information.
- Only safe technical information is logged (e.g. the LLM base URL, model,
  timeout, and generic failure reasons).
- Raw user speech is not logged unnecessarily.
- Input length is validated to prevent oversized requests.

---

## Files

- `backend/app/services/llm_client.py` - thin Ollama HTTP client.
- `backend/app/services/text_normalization_service.py` - normalization + heuristic fallback.
- `backend/app/schemas/normalization.py` - Pydantic request/response models.
- `backend/app/api/voice_routes.py` - adds `POST /voice/normalize` (unchanged `/transcribe`).
- `backend/app/core/config.py` - new `OLLAMA_*` / `NORMALIZE_*` settings.
- `backend/app/exceptions/exceptions.py` - new normalization exceptions.
- `backend/tests/unit/test_text_normalization_service.py` - unit tests (mocked LLM).
- `backend/tests/integration/test_voice_normalize_api.py` - endpoint tests.

---

## Testing

Tests never call a real external LLM; the Ollama HTTP request is mocked.

```bash
cd backend
python -m pytest tests/unit/test_text_normalization_service.py -v
python -m pytest tests/integration/test_voice_normalize_api.py -v
```

Covered scenarios include: standard Tamil, English, Tamil-English, Tanglish,
colloquial Tamil, scheme-eligibility and scheme-search intents, document
requirement, unknown/ambiguous input, LLM unavailable/timeout/invalid JSON,
malformed structured response, heuristic fallback, confidence clamping, and
authentication failure.

---

## Out of Scope (Phase 4)

Phase 4 does **not** connect the structured query to the eligibility engine,
RAG, scheme database, or citizen profile database. That is Phase 5.
