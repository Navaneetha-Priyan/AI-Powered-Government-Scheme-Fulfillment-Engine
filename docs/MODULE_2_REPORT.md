# Module 2: Citizen Profile & Mock DigiLocker Integration

## Status

Complete. An authenticated citizen is synchronised with the local mock DigiLocker
on successful login. The sync creates or updates the extended profile, land
records, and linked government documents without changing the JWT flow.

## Delivered capabilities

- Normalized `citizen_profiles`, `land_records`, `digilocker_records`, and
  `government_documents` tables, linked to `citizens` by UUID foreign keys.
- Deterministic mock records resolved by Aadhaar number or Smart Ration Card,
  with a safe generic profile for other valid citizens.
- Linked Aadhaar, ration card, income, community, residence, farmer, land, and
  disability documents as applicable.
- Authenticated profile, income, caste, land-record, document, dashboard, sync,
  and status APIs.
- Alembic revision `002_citizen_profile_digilocker` and API/integration tests.

## API surface

All endpoints below require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/citizen/profile` | Extended DigiLocker-synced profile |
| GET | `/citizen/profile/details` | Core and extended profile details |
| PUT | `/citizen/profile` | Update extended profile fields |
| GET | `/citizen/income` | Income and farmer details |
| GET | `/citizen/caste` | Caste and community details |
| GET | `/citizen/land-records` | Land records and total area |
| GET | `/citizen/documents` | Linked government documents |
| GET | `/citizen/dashboard` | Profile, document and land summary |
| POST | `/digilocker/sync` | Sync; accepts `{ "force_refresh": false }` |
| GET | `/digilocker/status` | Sync status and document counts |
| GET | `/digilocker/documents` | DigiLocker documents |
| GET | `/digilocker/documents/{document_id}` | One owned document |

## Login to sync sequence

```text
Citizen -> POST /auth/login -> JWT issued
                         -> DigiLockerService.sync
                         -> mock record lookup (Aadhaar/Ration Card)
                         -> profile + land + document persistence
Citizen -> GET /citizen/dashboard -> populated profile data
```

## Profile retrieval sequence

```text
Citizen -> GET /citizen/profile -> JWT dependency -> CitizenProfileService
        -> CitizenProfileRepository -> citizen_profiles -> response
```

## Document retrieval sequence

```text
Citizen -> GET /digilocker/documents -> JWT dependency -> DigiLockerService
        -> GovernmentDocumentRepository -> government_documents -> response
```

## Database relationships

```text
citizens 1--1 citizen_profiles
citizens 1--* land_records
citizens 1--1 digilocker_records 1--* government_documents
citizens 1--* government_documents
```

Run `alembic upgrade head` from `backend/` before starting the API. The mock
repository is intentionally local only; its download URLs are demonstration URLs
and do not expose real government documents.
