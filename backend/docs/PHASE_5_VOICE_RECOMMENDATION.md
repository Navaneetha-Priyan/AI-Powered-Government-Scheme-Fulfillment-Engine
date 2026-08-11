# Phase 5: Voice → Personalized Government Scheme Recommendation

Phase 5 connects the Phase 4 **normalized voice query** to the existing
**Module 4 recommendation/eligibility system**. A citizen speaks, the voice is
transcribed and normalized to a structured query, then the existing eligibility
engine and RAG-based scheme search produce **personalized scheme
recommendations** for the authenticated citizen.

The existing eligibility engine, RAG / vector search, scheme database, and
citizen profile schema are **unchanged**. Phase 5 only adds a thin adapter
(`VoiceQueryService`) and a single new endpoint (`POST /voice/recommend`).

---

## Overview

```
Flutter microphone
  → POST /voice/transcribe  (unchanged)
  → raw transcript (e.g. "enakku kaasu romba kammi, farmer scheme irukka?")
  → POST /voice/normalize   (Phase 4, unchanged)
  → structured query (intent + entities)
  → POST /voice/recommend   (NEW - Phase 5)
  → authenticated citizen identity (JWT)
  → verified citizen profile            ← source of truth
  → existing eligibility engine          ← reused
  → existing RAG / scheme search         ← reused
  → personalized scheme recommendations (existing schema)
  → Flutter chat screen displays results
```

`VoiceQueryService` is the *smallest* bridge between normalization and the
existing recommendation engine. It does **not**:

- implement eligibility rules
- implement RAG / vector search
- duplicate the scheme database
- accept Aadhaar / ration card / citizen ID from the voice request
- let LLM-extracted entities overwrite the verified citizen profile

---

## Endpoint

### `POST /voice/recommend`

Protected by the existing **JWT authentication** (`Authorization: Bearer <token>`).
The authenticated citizen identity is resolved from the token; it is never
accepted from the request body.

**Request schema** (`VoiceRecommendationRequest`): two mutually-supported styles.

Style 1 - raw text (normalized server-side):

```json
{
  "text": "enakku kaasu romba kammi, farmer scheme irukka?",
  "limit": 5
}
```

Style 2 - pre-normalized structured query (output of `POST /voice/normalize`):

```json
{
  "normalization": {
    "language": "ta-en",
    "intent": "scheme_search",
    "normalized_text": "Looking for a farmer scheme with low income",
    "entities": {
      "occupation": "farmer",
      "income_status": "low"
    },
    "confidence": 0.9,
    "source": "llm"
  },
  "limit": 5
}
```

At least `text` or `normalization` must be provided (else HTTP 422). `limit`
is `1..20`, defaulting to `5`. `text` is capped at 2000 characters.

**Response schema** (`VoiceRecommendationResponse`):

```json
{
  "schemes": [
    {
      "id": "...",
      "citizen_id": "...",
      "history_id": "...",
      "scheme_id": "...",
      "scheme_name": "PM Kisan Support",
      "description": "...",
      "benefits": "...",
      "eligibility_status": "eligible",
      "eligibility_percentage": 90.0,
      "similarity_score": 96.0,
      "confidence_score": 85.0,
      "overall_score": 88.0,
      "ranking_position": 1,
      "recommendation_reason": "...",
      "message": null,
      "profile": null
    }
  ],
  "intent": "scheme_search",
  "language": "ta-en",
  "normalized_text": "Looking for a farmer scheme with low income",
  "confidence": 0.9,
  "source": "llm"
}
```

| Field            | Type     | Description                                                        |
|------------------|----------|--------------------------------------------------------------------|
| `schemes`        | array    | Personalized recommendations, each using the existing `RecommendationMatchResponse` schema. |
| `intent`         | string   | The intent that was handled.                                       |
| `language`       | string?  | Approximate language tag of the query.                            |
| `normalized_text`| string?  | Normalized representation of the query.                           |
| `confidence`     | float    | Confidence in the structured interpretation.                      |
| `source`         | string?  | `llm` or `heuristic`.                                             |
| `message`        | string?  | Human-friendly message for unsupported intents / no results.      |
| `profile`        | object?  | Verified profile returned only for `profile_query` intents.       |

Reusing the existing recommendation schema means the Flutter client renders
voice results exactly like text-based results.

---

## How the existing text-based flow works (reused, not duplicated)

The existing Module 4 recommendation flow is driven by `RecommendationService`
(`app/services/recommendation_service.py`):

1. **Build citizen context** · `CitizenContextService.build(citizen_id)` loads
   the verified citizen + profile + land records + documents into a
   `CitizenContext`.
2. **Build a query** · `generate_query()` builds a search string from the
   profile (or uses a `query_override`). This feeds the RAG search.
3. **Semantic search** · `GovernmentSchemeService.semantic_search()` queries the
   existing vector store (ChromaDB) for relevant scheme chunks.
4. **Fallback candidates** · If vector search is unavailable, it falls back to
   listing active schemes.
5. **Evaluate eligibility** · For each candidate, configured + dynamically
   inferred eligibility `EligibilityRule`s are evaluated against the *verified*
   `CitizenContext` by `RuleEvaluationService`.
6. **Rank & score** · `RankingService` computes eligibility %, similarity,
   benefit, profile-match, and document scores into one overall score.
7. **Persist** · The `RecommendationHistory` + `CitizenSchemeMatch` rows are
   persisted, exactly as the text flow does.
8. **Return** · `RecommendationMatchResponse` objects are returned.

Phase 5 reuses **all** of steps 1–8. `VoiceQueryService` only supplies:

- the authenticated `citizen_id` (from JWT, not the request body)
- a `query_override` built from the voice `normalized_text` + safe entities
- `request_type="voice"` (tags the history row as a voice interaction)

The eligibility rules still read from the **verified citizen profile**, never
from the voice text.

---

## Intent handling

| Intent                 | Behaviour                                                                 |
|------------------------|----------------------------------------------------------------------------|
| `scheme_search`        | Routes through the existing recommendation/RAG pipeline.                   |
| `scheme_eligibility`   | Routes through the existing recommendation/RAG pipeline.                   |
| `document_requirement` | Routes through the existing recommendation/RAG pipeline (documents come from the scheme/candidate). |
| `profile_query`        | Returns the **verified** citizen profile (`VoiceRecommendationProfileView`). No eligibility logic. |
| `application_status`   | Returns a clear structured "not available" message (no schemes).           |
| `unknown`              | Returns a clear "could not understand" message (no schemes).               |

Any other intent value is rejected at the Pydantic schema layer (the intent is
a `Literal`), so `UnsupportedIntentError` in the service is defensive safety.

---

## Safety / data rules

The LLM is **not** the authority for citizen eligibility. Authoritative
sources are, in order:

1. **Authenticated citizen profile** (resolved from the JWT).
2. **Existing eligibility rules**.
3. **Existing government scheme data / RAG.**

The LLM output is only an interpretation of what the citizen said. It is used
as **search/query context** (e.g. to add a crop name or scheme name to the
search string), never to change the profile used for eligibility.

Example: if the profile says `occupation = "farmer"` but the LLM says
`occupation = "student"`, the verified profile remains authoritative. The voice
'topic' (`farmer`/`student`) can influence which schemes are *searched* but not
whether the citizen *qualifies*.

---

## Error handling

| Scenario                        | HTTP  | Error / response                                                     |
|---------------------------------|-------|----------------------------------------------------------------------|
| Missing/invalid token           | 401   | `MISSING_TOKEN` / `INVALID_TOKEN`                                     |
| Neither `text` nor `normalization` | 422 | Request validation failure                                           |
| Empty / oversized `text`        | 422   | `EMPTY_TEXT` / `TEXT_TOO_LONG`                                        |
| Citizen profile unavailable      | 404   | `PROFILE_NOT_FOUND` (for `profile_query` path)                        |
| Eligibility/RAG engine failure   | 500   | `ELIGIBILITY_ENGINE_ERROR` / `KNOWLEDGE_BASE_UNAVAILABLE` etc.        |
| No matching schemes              | 200   | Empty `schemes` with a `message` (not an error)                       |
| Unsupported intent               | 200   | Structured `message` response (validation rejects truly invalid intents) |

No stack traces or internal implementation details are exposed to the client.

---

## Files

- `backend/app/services/voice_query_service.py` - the voice → existing system adapter.
- `backend/app/api/voice_routes.py` - adds `POST /voice/recommend`.
- `backend/app/schemas/voice_recommendation.py` - request/response schemas (reuses `RecommendationMatchResponse`).
- `backend/app/exceptions/exceptions.py` - adds `UnsupportedIntentError`.
- `backend/tests/unit/test_voice_query_service.py` - unit tests (mocked engine/RAG/LLM).
- `backend/tests/integration/test_voice_recommend_api.py` - endpoint tests.
- `frontend/govt_scheme_app/lib/models/voice_recommendation.dart` - Flutter response model.
- `frontend/govt_scheme_app/lib/core/services/voice_api_service.dart` - Flutter `recommend()` method.
- `frontend/govt_scheme_app/lib/screens/chat/chat_screen.dart` - displays voice recommendations.

---

## Testing

Tests mock the external/expensive components (Ollama LLM, semantic search,
recommendation service, profile repositories). They never call a real LLM or
vector store.

```bash
cd backend
python -m pytest tests/unit/test_voice_query_service.py -v
python -m pytest tests/integration/test_voice_recommend_api.py -v
```

Covered scenarios:

- authenticated voice recommendation
- scheme search intent
- scheme eligibility intent
- document requirement intent
- profile retrieval (profile_query)
- voice entities do not overwrite verified profile data
- existing eligibility engine is called
- existing RAG/search service is called
- no matching schemes
- unsupported intent (application_status / unknown)
- authentication failure
- citizen profile unavailable
- existing recommendation behavior remains unchanged (no regressions)

---

## Out of Scope (Phase 5)

- Text-to-speech / voice output (a later phase).
- Rebuilding the eligibility engine, RAG, scheme DB, or citizen profile schema.
- Accepting Aadhaar / ration card / citizen ID from the voice request.
- Trusting LLM-inferred citizen attributes as eligibility facts.

