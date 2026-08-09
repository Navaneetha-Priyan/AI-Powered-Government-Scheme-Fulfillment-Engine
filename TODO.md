# STEP 1: Document-to-Citizen-Profile — Structured Mock Document Data
## Backend
- [x] 1. Inspect existing mock DigiLocker data layer + models + service
- [x] 2. Add structured document fields to `mock_digilocker_data.py` doc_metadata (JSON strings)
- [x] 3. Pass citizen demographic fields through `digilocker_service.sync()` → `get_mock_documents()`
- [x] 4. Add focused test `backend/tests/unit/test_mock_digilocker_data.py`
- [x] 5. Run backend pytest suite to confirm no regressions

---
# STEP 2: Document-to-Citizen-Profile — Document Profile Extraction
## Backend
- [x] 1. Add extraction exceptions to `backend/app/exceptions/exceptions.py`
- [x] 2. Create `backend/app/schemas/document_profile.py` (`ExtractedDocumentData` reusing `DocumentTypeEnum`)
- [x] 3. Create `backend/app/services/document_profile_extractor.py` (read-only extractor)
- [x] 4. Add focused unit test `backend/tests/unit/test_document_profile_extractor.py`
- [x] 5. Run new extractor tests + Step 1 tests + full backend pytest suite (229 passed; `test_scheme_api.py` excluded due to pre-existing missing `fitz` dependency)

---
# STEP 3: Document-to-Citizen-Profile — Document Profile Mapper
## Backend
- [x] 1. Add `LandRecordUpdateData` + `MappedDocumentData` schemas to `backend/app/schemas/document_profile.py`
- [x] 2. Create `backend/app/services/document_profile_mapper.py` (read-only DocumentProfileMapper)
- [x] 3. Add focused unit test `backend/tests/unit/test_document_profile_mapper.py`
- [x] 4. Run new mapper tests + Step 1 tests + Step 2 extractor tests + full backend pytest suite (251 passed; `test_scheme_api.py` excluded due to pre-existing missing `fitz` dependency)

---
# STEP 4: Document-to-Citizen-Profile — Profile Enrichment Service
## Backend
- [x] 1. Add `FieldConflict` + `EnrichmentResult` schemas to `backend/app/schemas/document_profile.py`
- [x] 2. Extract shared completion helper into `backend/app/services/citizen_profile_service.py`
- [x] 3. Add `LandRecordRepository.get_by_citizen_and_survey()` to `backend/app/repositories/citizen_profile_repository.py`
- [x] 4. Create `backend/app/services/profile_enrichment_service.py` (`ProfileEnrichmentService`)
- [x] 5. Add `backend/tests/unit/test_profile_enrichment_service.py`
- [x] 6. Run new enrichment tests + Step 1/2/3 tests + full backend pytest suite
- [x] 7. Update this TODO / report results

---
---
# STEP 5: Integrate Document Upload + DigiLocker Sync with Profile Enrichment
## Backend
- [x] 1. Audit existing DigiLocker sync, citizen upload, auth, and mock-data flows
- [x] 2. Route `DigiLockerService.sync()` through the canonical pipeline: GovernmentDocument → DocumentProfileExtractor → DocumentProfileMapper → ProfileEnrichmentService (per-parcel land records; no direct MOCK_PROFILES dump)
- [x] 3. Emit per-parcel `land_record` documents in `mock_digilocker_data.py` (both 123/2A and 456/1B) and add `religion` to community-cert metadata
- [x] 4. Extend extractor field spec + mapper to carry `religion` → `citizen_profiles.religion`
- [x] 5. Wire `citizen_routes.upload_land_record()` to run the created GovernmentDocument through `enrich_document()` (no-op when no structured metadata — real OCR is Step 8)
- [x] 6. Add integration suite `backend/tests/integration/test_document_enrichment_integration.py` (PART L: sync, per-doc enrichment, land aggregation, idempotency, sync contract, login-triggered sync, upload path)
- [x] 7. Run new integration tests + full backend pytest suite (286 passed; `test_scheme_api.py` excluded due to pre-existing missing `fitz` dependency)

---
# Phase 5: Voice → Personalized Government Scheme Recommendation

## Backend
- [x] 1. Add `UnsupportedIntentError` to `backend/app/exceptions/exceptions.py`
- [x] 2. Create `backend/app/schemas/voice_recommendation.py` (request/response schemas)
- [x] 3. Create `backend/app/services/voice_query_service.py` (adapter reusing RecommendationService + CitizenProfileService)
- [x] 4. Add `POST /voice/recommend` endpoint to `backend/app/api/voice_routes.py`
- [x] 5. Add integration tests `backend/tests/integration/test_voice_recommend_api.py`
- [x] 6. Add unit tests `backend/tests/unit/test_voice_query_service.py`
- [x] 7. Run backend pytest suite (integration + unit) to confirm no regressions

## Flutter (only after backend verified)
- [x] 8. Add `voiceRecommend` constant to `api_constants.dart`
- [x] 9. Add `VoiceRecommendationResult` model + `recommend()` in `voice_api_service.dart`
- [x] 10. Extend `ChatScreen` to display returned schemes (reuse existing recommendation components)
- [x] 11. Run `flutter analyze` and relevant Flutter tests

## Docs
- [x] 12. Add `backend/docs/PHASE_5_VOICE_RECOMMENDATION.md`
