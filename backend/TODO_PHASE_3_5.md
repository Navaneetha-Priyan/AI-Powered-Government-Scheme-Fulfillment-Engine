# STEP 5: Document Upload + DigiLocker Sync → Profile Enrichment Pipeline
## Canonical flow (reuses Steps 1–4)
```
GovernmentDocument
    ↓
DocumentProfileExtractor   (Step 2)
    ↓
ExtractedDocumentData
    ↓
DocumentProfileMapper     (Step 3)
    ↓
MappedDocumentData
    ↓
ProfileEnrichmentService  (Step 4)
    ↓
citizens / citizen_profiles / land_records
```

## Backend
- [ ] 1. `mock_digilocker_data.py`: emit one `land_record` document per parcel (123/2A + 456/1B) so enrichment yields 3.5 acres via aggregation
- [ ] 2. `mock_digilocker_data.py`: add `religion` to community/caste certificate structured metadata
- [ ] 3. `document_profile_extractor.py`: add `religion` to caste/community `_FIELD_SPECS`
- [ ] 4. `document_profile_mapper.py`: map `religion` → `religion` for caste/community
- [ ] 5. `digilocker_service.py`: remove direct `get_mock_profile()` → `profile_repo.upsert()`; run document extract→map→enrich as the only profile-builder; make land records flow through enrichment (idempotent, one per parcel)
- [ ] 6. `digilocker_service.py`: add single canonical `_process_documents()` helper + public `enrich_uploaded_document()`
- [ ] 7. `citizen_routes.py`: land upload passes structured `land_record` metadata to the document pipeline and enrichs via the canonical path
- [ ] 8. Add `backend/tests/integration/test_profile_pipeline_integration.py`
- [ ] 9. Run new integration tests + Step 1/2/3/4 tests + DigiLocker/auth/profile tests + full backend suite
- [ ] 10. Update TODO.md

