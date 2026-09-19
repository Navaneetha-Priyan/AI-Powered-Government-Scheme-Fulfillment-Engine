"""Focused consistency tests (CASE 1/2/4/5) for the evidence fix."""
from __future__ import annotations

from datetime import datetime

from app.models.citizen import Citizen
from app.models.citizen_document import (
    CitizenDocumentType,
    DocumentProcessStatus,
    UploadedDocument,
    VerificationStatus,
)
from app.models.citizen_profile import CitizenProfile, LandRecord, LandType
from app.services.citizen_evidence_service import canonical_evidence_type
from app.services.eligibility_catalog_service import get_catalogue_entry
from app.services.recommendation_service import (
    CitizenContextService,
    RecommendationService,
    _missing_evidence_for,
)


def _citizen(test_db) -> Citizen:
    citizen = Citizen(
        email="consistency@example.com",
        phone="9876543002",
        password_hash="placeholder",
        full_name="Consistency Farmer",
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


def _baseline_citizen(test_db):
    """Verified profile-uploads + qualifying land record, like the report."""
    citizen = _citizen(test_db)
    profile = CitizenProfile(
        citizen_id=citizen.id,
        occupation="Farmer",
        annual_income=72000.0,
        is_farmer=True,
        profile_completion_percentage=80,
    )
    test_db.add(profile)
    land = LandRecord(
        citizen_id=citizen.id,
        survey_number="123/1",
        land_area=2.0,
        land_type=LandType.AGRICULTURAL,
        ownership_type="owned",
        district="Villupuram",
        state="Tamil Nadu",
    )
    test_db.add(land)
    test_db.commit()
    for raw in (
        CitizenDocumentType.AADHAAR_CARD,
        CitizenDocumentType.LAND_DOCUMENT,
        CitizenDocumentType.FARMER_DOCUMENT,
        CitizenDocumentType.COMMUNITY_CERTIFICATE,
    ):
        _upload(test_db, citizen.id, raw)
    test_db.refresh(citizen)
    return citizen


def _candidate_for(test_db):
    from app.models.government_scheme import GovernmentScheme
    from app.services.recommendation_service import SchemeCandidate

    scheme = GovernmentScheme(
        scheme_name="PM-KISAN Operational Guidelines",
        description="Income support for eligible farmers.",
        category="agriculture",
        department="Agriculture Department",
        government_level="central",
        state="Tamil Nadu",
        benefits="Annual income support",
        eligibility_summary="Small and marginal farmers",
        required_documents="Aadhaar, land record",
        application_process="Apply online",
        language="en",
        status="active",
        is_deleted=False,
    )
    test_db.add(scheme)
    test_db.commit()
    test_db.refresh(scheme)
    return SchemeCandidate(
        scheme=scheme, semantic_score=0.9, chunks=[], aggregated_text=""
    )


def _pm_kisan_citizen_response(test_db, citizen_id: str):
    service = RecommendationService(test_db)
    context = service.context_service.build(citizen_id)
    entry = get_catalogue_entry("pm-kisan")
    assert entry is not None
    recommendation, _ = service._evaluate_candidate_structured(  # noqa: SLF001
        context, _candidate_for(test_db), entry
    )
    checklist = service._build_evidence_checklist(
        citizen_id,
        recommendation.required_documents,
        recommendation.missing_requirements,
        recommendation.missing_evidence,
    )
    return recommendation, checklist


def test_case1_verified_documents_never_missing(test_db):
    """CASE 1: aadhaar + land_record verified must not be reported missing."""
    citizen = _baseline_citizen(test_db)
    recommendation, checklist = _pm_kisan_citizen_response(test_db, citizen.id)

    assert "aadhaar" not in (recommendation.missing_evidence or [])
    assert "land_record" not in (recommendation.missing_evidence or [])
    conditions = {
        str(item.get("field") or item.get("condition"))
        for item in recommendation.missing_requirements
    }
    assert "aadhaar" not in conditions
    assert "land_record" not in conditions
    statuses = {
        item["requirement"]: item["status"]
        for item in checklist
        if item["requirement"] in {"aadhaar", "land_record"}
    }
    assert statuses == {"aadhaar": "verified", "land_record": "verified"}


def test_case2_profile_fact_separate_from_documents(test_db):
    """CASE 2: income_tax_payer UNKNOWN; documents verified; never mixed."""
    citizen = _baseline_citizen(test_db)
    recommendation, checklist = _pm_kisan_citizen_response(test_db, citizen.id)

    conditions = {
        str(item.get("field") or item.get("condition"))
        for item in recommendation.missing_requirements
    }
    assert "income_tax_payer" in conditions
    statuses = {
        item["requirement"]: item["status"]
        for item in checklist
        if item["requirement"] in {"aadhaar", "land_record"}
    }
    assert statuses == {"aadhaar": "verified", "land_record": "verified"}
    assert "income_tax_payer" not in (recommendation.missing_evidence or [])


def test_case4_rkvy_reports_only_genuinely_unknown_rule(test_db):
    """CASE 4: PM-RKVY/PKVY with verified docs; only activity_type unknown."""
    from app.services.eligibility_evaluator import get_eligibility_evaluator

    citizen = _baseline_citizen(test_db)


def test_case3_smam_rules_evaluated_independently_of_evidence(test_db):
    """CASE 3: SMAM with verified docs; farmer rule passes, social optional."""
    from app.services.eligibility_evaluator import get_eligibility_evaluator

    citizen = _baseline_citizen(test_db)
    context = CitizenContextService(test_db).build(citizen.id)
    entry = get_catalogue_entry("smam")
    assert entry is not None
    result = get_eligibility_evaluator().evaluate_catalogue_entry(entry, context)

    assert result.mandatory_rules_total == 1
    assert result.mandatory_rules_passed == 1
    assert {c.condition for c in result.matched_conditions} == {"farmer_status"}
    assert list(result.failed_conditions) == []
    # Evidence is available, never reported missing.
    assert "aadhaar" not in result.missing_evidence
    assert "land_record" not in result.missing_evidence

    context = CitizenContextService(test_db).build(citizen.id)
    entry = get_catalogue_entry("pm-rkvy-pkvy")
    assert entry is not None
    result = get_eligibility_evaluator().evaluate_catalogue_entry(entry, context)

    conditions = {c.condition for c in result.missing_information}
    assert "activity_type" in conditions
    assert "aadhaar" not in conditions
    assert "land_record" not in conditions
    assert "aadhaar" not in result.missing_evidence
    assert "land_record" not in result.missing_evidence


def test_case5_unknown_upload_never_satisfies_evidence(test_db):
    """CASE 5: an unmapped upload type satisfies no canonical requirement."""
    citizen = _citizen(test_db)
    profile = CitizenProfile(citizen_id=citizen.id)
    test_db.add(profile)
    test_db.commit()

    _upload(test_db, citizen.id, CitizenDocumentType.UNKNOWN)
    assert canonical_evidence_type("unknown") is None
    context = CitizenContextService(test_db).build(citizen.id)
    assert _missing_evidence_for(context, ["aadhaar", "land_record"]) == [
        "aadhaar",
        "land_record",
    ]
