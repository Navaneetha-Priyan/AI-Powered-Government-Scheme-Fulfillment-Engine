"""Integration tests for Module 4 recommendation APIs."""
from types import SimpleNamespace

from app.core.jwt import create_access_token
from app.models.citizen import Citizen
from app.models.citizen_document import (
    CitizenDocumentType,
    DocumentProcessStatus,
    UploadedDocument,
    VerificationStatus,
)
from app.models.citizen_profile import CitizenProfile, LandRecord, LandType
from app.models.government_scheme import GovernmentScheme
from app.services import government_scheme_service as scheme_service_module


class FakeSearchService:
    def __init__(self, scheme_id: str):
        self.scheme_id = scheme_id

    def semantic_search(self, query, limit=5, category=None):
        del query, limit, category
        return [
            {
                "scheme_id": self.scheme_id,
                "scheme_name": "PM Kisan Support",
                "category": "agriculture",
                "department": "Agriculture Department",
                "similarity_score": 0.96,
                "matched_content": "Small and marginal farmers receive annual support.",
                "relevant_content": "Small and marginal farmers receive annual support.",
                "benefits": "Annual income support",
                "page_number": 1,
                "section_name": "Eligibility",
                "document_id": "document-1",
            }
        ]


def create_profile(test_db, citizen_id: str):
    profile = CitizenProfile(
        citizen_id=citizen_id,
        father_name="Ravi Kumar",
        mother_name="Lakshmi Devi",
        occupation="Farmer",
        annual_income=85000,
        income_category="bpl",
        caste="Vanniyar",
        community="MBC",
        is_disabled=False,
        is_farmer=True,
        education_level="10th",
        family_member_count=4,
        profile_completion_percentage=90,
        sync_status="synced",
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


def create_land_record(test_db, citizen_id: str):
    land = LandRecord(
        citizen_id=citizen_id,
        survey_number="123/45",
        land_area=3.2,
        land_area_unit="acres",
        land_type=LandType.AGRICULTURAL,
        village="Periyakulam",
        taluk="Villupuram",
        district="Villupuram",
        state="Tamil Nadu",
        ownership_type="owned",
        patta_number="PATTA-12345",
    )
    test_db.add(land)
    test_db.commit()
    test_db.refresh(land)
    return land


def create_scheme(test_db, scheme_name: str = "PM Kisan Support"):
    scheme = GovernmentScheme(
        scheme_name=scheme_name,
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
    return scheme


def create_citizen(test_db):
    from datetime import datetime
    citizen = Citizen(
        email="test.rec@example.com",
        phone="9876543999",
        password_hash="placeholder-hash",
        full_name="Recommendation User",
        district="Chennai",
        state="Tamil Nadu",
        account_active=True,
        status="active",
        is_deleted=False,
        date_of_birth=datetime(1990, 1, 1),  # ~34 years old
    )
    test_db.add(citizen)
    test_db.commit()
    test_db.refresh(citizen)
    token = create_access_token({"sub": citizen.id, "email": citizen.email, "role": "citizen"})
    return citizen, {"Authorization": f"Bearer {token}"}


def create_uploaded_document(test_db, citizen_id: str, document_type: CitizenDocumentType):
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
    test_db.refresh(document)
    return document


def test_recommendation_apis_require_authentication(client):
    assert client.get("/api/recommendations").status_code == 401


def test_generate_and_fetch_recommendations(client, test_db, monkeypatch):
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    scheme = create_scheme(test_db)

    monkeypatch.setattr(scheme_service_module.GovernmentSchemeService, "semantic_search", lambda self, query, limit=5, category=None: FakeSearchService(scheme.id).semantic_search(query, limit, category))

    generate_response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert generate_response.status_code == 201, generate_response.json()
    payload = generate_response.json()["data"]
    assert payload["eligible_count"] >= 1
    assert payload["recommendations"][0]["scheme_name"] == "PM Kisan Support"
    assert payload["recommendations"][0]["eligibility_status"] == "eligible"

    latest_response = client.get("/api/recommendations", headers=auth_headers)
    assert latest_response.status_code == 200
    assert latest_response.json()["data"]["recommendations"][0]["scheme_name"] == "PM Kisan Support"

    recommendation_id = latest_response.json()["data"]["recommendations"][0]["id"]
    detail_response = client.get(f"/api/recommendations/{recommendation_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["scheme_name"] == "PM Kisan Support"

    history_response = client.get("/api/recommendations/history", headers=auth_headers)
    assert history_response.status_code == 200
    assert len(history_response.json()["data"]) >= 1

    eligibility_response = client.get(
        "/api/eligibility/check",
        headers=auth_headers,
        params={"scheme_id": scheme.id},
    )
    assert eligibility_response.status_code == 200
    assert eligibility_response.json()["data"]["eligible"] is True

    rules_response = client.get("/api/eligibility/rules", headers=auth_headers)
    assert rules_response.status_code == 200
    assert len(rules_response.json()["data"]) >= 1


def test_recommendation_detail_refreshes_stale_missing_evidence(
    client, test_db, monkeypatch
):
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    generate_response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert generate_response.status_code == 201, generate_response.json()
    recommendation_id = generate_response.json()["data"]["recommendations"][0]["id"]

    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.LAND_DOCUMENT)

    refreshed_response = client.get(
        f"/api/recommendations/{recommendation_id}", headers=auth_headers
    )
    assert refreshed_response.status_code == 200
    refreshed = refreshed_response.json()["data"]
    checklist = {
        item["requirement"]: item for item in refreshed["evidence_checklist"]
    }

    assert checklist["aadhaar"]["status"] == "verified"
    assert checklist["land_record"]["status"] == "verified"
    assert checklist["aadhaar"]["matched_document_type"] == "aadhaar_card"
    assert checklist["land_record"]["matched_document_type"] == "land_document"

    needed = {
        item["requirement"]
        for item in refreshed["evidence_checklist"]
        if item["status"] == "needed"
    }
    assert "aadhaar" not in needed
    assert "land_record" not in needed


def test_recommendation_and_live_eligibility_share_current_evidence(
    client, test_db, monkeypatch
):
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.LAND_DOCUMENT)
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    generate_response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert generate_response.status_code == 201, generate_response.json()
    recommendation = generate_response.json()["data"]["recommendations"][0]

    eligibility_response = client.get(
        "/api/eligibility/check",
        headers=auth_headers,
        params={"scheme_id": scheme.id},
    )
    assert eligibility_response.status_code == 200
    live = eligibility_response.json()["data"]

    def statuses(payload):
        return {
            item["requirement"]: item["status"]
            for item in payload["evidence_checklist"]
            if item["requirement"] in {"aadhaar", "land_record"}
        }

    assert statuses(recommendation) == {
        "aadhaar": "verified",
        "land_record": "verified",
    }
    assert statuses(live) == statuses(recommendation)
    assert live["mandatory_rules_total"] == recommendation["mandatory_rules_total"]
    assert live["mandatory_rules_passed"] == recommendation["mandatory_rules_passed"]


def test_missing_profile_fact_is_not_reported_as_missing_document(
    client, test_db, monkeypatch
):
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.LAND_DOCUMENT)
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert response.status_code == 201, response.json()
    recommendation = response.json()["data"]["recommendations"][0]



def test_case6_upload_after_generate_refreshes_detail(client, test_db, monkeypatch):
    """CASE 6: a previously-missing upload flips the detail on re-request."""
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    generate_response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert generate_response.status_code == 201, generate_response.json()
    recommendation_id = generate_response.json()["data"]["recommendations"][0]["id"]

    before = client.get(
        f"/api/recommendations/{recommendation_id}", headers=auth_headers
    )
    assert before.status_code == 200, before.json()
    statuses_before = {
        item["requirement"]: item["status"]
        for item in before.json()["data"]["evidence_checklist"]
    }
    assert statuses_before.get("aadhaar") != "verified"
    assert statuses_before.get("land_record") != "verified"

    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.LAND_DOCUMENT)

    after = client.get(
        f"/api/recommendations/{recommendation_id}", headers=auth_headers
    )
    assert after.status_code == 200, after.json()
    refreshed = after.json()["data"]
    checklist = {item["requirement"]: item for item in refreshed["evidence_checklist"]}
    assert checklist["aadhaar"]["status"] == "verified"
    assert checklist["land_record"]["status"] == "verified"

    conditions = {
        item.get("field") or item.get("condition")
        for item in refreshed["missing_requirements"]
    }
    assert "aadhaar" not in conditions
    assert "land_record" not in conditions


def test_raw_ocr_text_never_becomes_scheme_description(client, test_db, monkeypatch):
    """Raw letterhead / OCR dumps must not surface as "What is this scheme?"."""
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    description = (
        "1 PRADHAN MANTRI KISAN SAMMAN NIDHI SCHEME Ministry of Agriculture "
        "and Farmers Welfare Krishi Bhawan NewDelhi-110001"
    )
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")
    scheme.description = description
    scheme.benefits = "NewDelhi-110001"
    scheme.eligibility_summary = "NewDelhi-110001"
    test_db.commit()

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert response.status_code == 201, response.json()
    detail = client.get(
        f"/api/recommendations/{response.json()['data']['recommendations'][0]['id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200, detail.json()
    body = detail.json()["data"]
    for key in ("description", "benefits"):
        value = body.get(key)
        assert value is None or (
            "NewDelhi" not in value
            and "New Delhi" not in value
            and "110001" not in value
            and "PRADHAN MANTRI KISAN" not in value
        ), f"{key} leaked raw OCR text: {value!r}"

    assert body is not None
    assert body is not None


def test_recommendation_api_returns_structured_presentation(client, test_db, monkeypatch):
    """Recommendation API exposes clean structured presentation fields."""
    from app.services.scheme_presentation_service import FALLBACK_DESCRIPTION

    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.LAND_DOCUMENT)
    # Catalogue-backed name so the presentation metadata resolves by id.
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")
    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert response.status_code == 201, response.json()
    body = response.json()["data"]["recommendations"][0]

    assert body["display_name"] == "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)"
    assert body["short_description"].startswith(
        "PM-KISAN gives income support to landholding farmer families"
    )
    assert isinstance(body["benefits_list"], list) and body["benefits_list"]
    for bullet in body["benefits_list"]:
        assert "Page No" not in bullet
        assert "Government of India" not in bullet

    detail = client.get(
        f"/api/recommendations/{body['id']}", headers=auth_headers
    )
    assert detail.status_code == 200, detail.json()
    refreshed = detail.json()["data"]
    assert refreshed["short_description"] == body["short_description"]


def test_recommendation_api_never_returns_raw_extraction_in_presentation(
    client, test_db, monkeypatch
):
    """A scheme whose stored text is pure noise gets the safe fallback."""
    from app.services.scheme_presentation_service import FALLBACK_DESCRIPTION

    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    # Unknown scheme name -> no presentation entry resolves; stored text is
    # a raw PDF dump that must never leak into presentation fields.
    scheme = create_scheme(test_db, "Unknown Blob Guidelines 2099")
    scheme.description = (
        "Page No. 1 Uttam fasal Uttam Enam NATIONAL AGRICULTURE MARKET (e-NAM) "
        "A National Portal for eTrading Directory Government of India he"
    )
    test_db.commit()
    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert response.status_code == 201, response.json()
    body = response.json()["data"]["recommendations"][0]

    assert body["short_description"] == FALLBACK_DESCRIPTION
    assert body["benefits_list"] == []
    assert "Page No" not in (body["short_description"] or "")
    assert "Government of India" not in (body["short_description"] or "")


def test_presentation_marks_review_required_schemes(client, test_db, monkeypatch):
    """Schemes flagged needs_review expose only the safe fallback text."""
    from app.services.scheme_presentation_service import (
        FALLBACK_DESCRIPTION,
        load_scheme_presentation,
    )

    flagged = [
        sid
        for sid, entry in load_scheme_presentation().items()
        if entry["needs_review"]
    ]
    assert flagged, "needs_review flags disappeared from presentation metadata"
    assert "pm-svanidhi" in flagged
    assert "free-bus-travel-women-tn" in flagged

    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    scheme = create_scheme(test_db, "PM Street Vendor AtmaNirbhar Nidhi")
    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )
    response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert response.status_code == 201, response.json()
    body = response.json()["data"]["recommendations"][0]
    assert body["short_description"] == FALLBACK_DESCRIPTION
    assert body["benefits_list"] == []




def test_checklist_uses_authoritative_evidence_shortfall(client, test_db, monkeypatch):
    """Checklist marks genuinely-unavailable documents as "needed"."""
    citizen, auth_headers = create_citizen(test_db)
    citizen_id = citizen.id
    create_profile(test_db, citizen_id)
    create_land_record(test_db, citizen_id)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.AADHAAR_CARD)
    create_uploaded_document(test_db, citizen_id, CitizenDocumentType.LAND_DOCUMENT)
    scheme = create_scheme(test_db, "PM-KISAN Operational Guidelines")

    monkeypatch.setattr(
        scheme_service_module.GovernmentSchemeService,
        "semantic_search",
        lambda self, query, limit=5, category=None: FakeSearchService(
            scheme.id
        ).semantic_search(query, limit, category),
    )

    response = client.post(
        "/api/recommendations/generate",
        headers=auth_headers,
        json={"limit": 5, "category": "agriculture"},
    )
    assert response.status_code == 201, response.json()
    recommendation = response.json()["data"]["recommendations"][0]

    checklist = {item["requirement"]: item for item in recommendation["evidence_checklist"]}
    assert checklist["aadhaar"]["status"] == "verified"
    assert checklist["land_record"]["status"] == "verified"
    assert checklist["bank_account"]["status"] == "needed"

    conditions = {
        item.get("field") or item.get("condition")
        for item in recommendation["missing_requirements"]
    }
    assert "income_tax_payer" in conditions
    assert "aadhaar" not in conditions
    assert "land_record" not in conditions
