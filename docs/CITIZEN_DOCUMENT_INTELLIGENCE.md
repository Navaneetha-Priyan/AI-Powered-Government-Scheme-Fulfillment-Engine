# Citizen Document Intelligence

This workflow builds a citizen profile from documents without replacing the existing Module 1 authentication, Module 2 DigiLocker profile, or Module 4 recommendation interfaces.

## Workflow

1. Authenticate and upload one PDF, PNG, JPG, or JPEG for each selected document type.
2. Call `POST /api/documents/process-all`. PDFs are read with PyMuPDF; images are sent to local Tesseract OCR.
3. Call `GET /api/profile/preview` and correct any extracted value with `POST /api/profile/correct`.
4. If two sources disagree, `GET /api/profile/conflicts` lists both values. Confirmation is blocked until the citizen corrects the field.
5. Call `POST /api/profile/confirm`. Confirmed fields populate `citizen_profiles`; verified land values populate `land_records`, which Module 4 already consumes.

## Supported document types

`aadhaar_card`, `smart_ration_card`, `income_certificate`, `community_certificate`, `land_document`, `farmer_document`, `disability_certificate`, `bank_passbook`, and `education_certificate`.

The current deterministic extractor recognises labelled fields such as Name, DOB, Gender, Address, Annual Income, Caste, Community, Survey Number, Land Area, Farmer ID, Disability Percentage, Bank/IFSC, and Qualification. Bank-account values are saved only as masked last-four digits. OCR/extraction output is reviewable rather than treated as authoritative.

## API summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/documents/{document_type}/upload` | Store one citizen-owned document of that type |
| GET | `/api/documents` | List document status |
| POST | `/api/documents/process-all` | Extract all pending uploads |
| GET | `/api/documents/extracted/{document_id}` | Inspect raw extracted fields |
| GET | `/api/profile/preview` | Inspect selected values and conflicts |
| POST | `/api/profile/correct` | Correct and verify a selected field |
| GET | `/api/profile/completeness` | Get identity/financial/social/etc. completion |
| POST | `/api/profile/confirm` | Finalise a conflict-free profile |

All endpoints require the citizen JWT. Files are stored under `DOCUMENT_STORAGE_DIR`, defaulting to `storage/citizen_documents`; production deployments should place this path in protected object storage or an encrypted volume. `TESSERACT_CMD` configures the local Windows Tesseract executable for image uploads.
