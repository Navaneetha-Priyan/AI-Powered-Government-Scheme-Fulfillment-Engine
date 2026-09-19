"""Regression tests for the canonical citizen evidence layer."""
from __future__ import annotations

from datetime import datetime

from app.models.citizen import Citizen
from app.models.citizen_document import (
    CitizenDocumentType,
    DocumentProcessStatus,
    UploadedDocument,
    VerificationStatus,
)
from app.models.digilocker import (
    DigiLockerRecord,
    DocumentType,
    DocumentVerificationStatus,
    GovernmentDocument,
)
from app.services.citizen_evidence_service import (
    CitizenEvidenceService,
    EvidenceState,
    canonical_evidence_type,
)


def _citizen(test_db) -> Citizen:
    citizen = Citizen(
        email="evidence@example.com",
        phone="9876543001",
        password_hash="placeholder",
        full_name="Evidence User",
        district="Villupuram",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
        date_of_birth=datetime(1990, 1, 1),
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    return citizen


def _upload(test_db, citizen_id: str, document_type: CitizenDocumentType):
    document = UploadedDocument(
        citizen_id=citizen_id,
        document_type=document_type,
        original_file_name=f"{document_type.value}.pdf",
        file_path=f"/tmp/{document_type.value}.pdf",
        file_size=10,
        mime_type="application/pdf",
        upload_status=DocumentProcessStatus.VERIFIED,
        verification_status=VerificationStatus.VERIFIED,
    )
    test_db.add(document)
    test_db.commit()
    return document


def _government_document(test_db, citizen_id: str, document_type: DocumentType):
    record = DigiLockerRecord(
        citizen_id=citizen_id,
        digilocker_id=f"DL-{citizen_id}",
        is_active=True,
    )
    test_db.add(record)
    test_db.flush()
    document = GovernmentDocument(
        citizen_id=citizen_id,
        digilocker_record_id=record.id,
        document_type=document_type,
        document_name=document_type.value,
        verification_status=DocumentVerificationStatus.VERIFIED,
    )
    test_db.add(document)
    test_db.commit()
    return document


def test_uploaded_build_profile_documents_satisfy_catalogue_evidence(test_db):
    citizen = _citizen(test_db)
    for document_type in (
        CitizenDocumentType.AADHAAR_CARD,
        CitizenDocumentType.LAND_DOCUMENT,
        CitizenDocumentType.FARMER_DOCUMENT,
        CitizenDocumentType.COMMUNITY_CERTIFICATE,
    ):
        _upload(test_db, citizen.id, document_type)

    evidence = CitizenEvidenceService(test_db).build(citizen.id)

    assert evidence.state_for_requirement("aadhaar") == EvidenceState.VERIFIED
    assert evidence.state_for_requirement("land_record") == EvidenceState.VERIFIED
    assert evidence.state_for_requirement("identity_proof") == EvidenceState.VERIFIED
    assert evidence.state_for_requirement("address_proof") == EvidenceState.VERIFIED
    assert evidence.state_for_requirement("farmer_registration") == EvidenceState.VERIFIED
    assert evidence.state_for_requirement("caste_certificate") == EvidenceState.VERIFIED
    assert evidence.missing_requirements(
        ["aadhaar", "land_record", "identity_proof", "farmer_registration", "caste_certificate"]
    ) == []


def test_uploaded_and_government_documents_use_same_canonical_path(test_db):
    citizen = _citizen(test_db)
    _upload(test_db, citizen.id, CitizenDocumentType.AADHAAR_CARD)
    _government_document(test_db, citizen.id, DocumentType.LAND_RECORD)

    evidence = CitizenEvidenceService(test_db).build(citizen.id)

    assert evidence.state_for_requirement("aadhaar") == EvidenceState.VERIFIED
    assert evidence.state_for_requirement("land_record") == EvidenceState.VERIFIED
    assert evidence.by_type["aadhaar"].source == "uploaded_document"
    assert evidence.by_type["land_record"].source == "government_document"


def test_unknown_uploaded_document_type_is_unmapped_not_land_record(test_db):
    citizen = _citizen(test_db)
    _upload(test_db, citizen.id, CitizenDocumentType.UNKNOWN)

    evidence = CitizenEvidenceService(test_db).build(citizen.id)

    assert canonical_evidence_type("unknown") is None
    assert "unknown" not in evidence.available_types
    assert "land_record" not in evidence.available_types
    assert evidence.state_for_requirement("land_record") == EvidenceState.MISSING
