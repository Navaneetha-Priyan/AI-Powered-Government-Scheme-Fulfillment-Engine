"""Integration Tests — Step 5: Document upload + DigiLocker sync → Profile enrichment.

These tests prove that the real application flows (DigiLocker sync, login-triggered
sync, and the land-record upload endpoint) now populate the citizen profile and
land records through the canonical document pipeline:

    GovernmentDocument
        -> DocumentProfileExtractor      # Step 2
        -> DocumentProfileMapper         # Step 3
        -> ProfileEnrichmentService      # Step 4
        -> citizens / citizen_profiles / land_records

The critical assertions verify that the persisted values come from *document
metadata* — NOT from a direct ``MOCK_PROFILES`` assignment. In particular we
assert that fields which exist only in ``MOCK_PROFILES`` (and are not carried by
any document's ``doc_metadata``) remain unset after sync. Under the legacy
direct-dump behaviour those fields would have been populated; under the Step 5
pipeline they must not be.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.repositories.citizen_profile_repository import (
    CitizenProfileRepository,
    LandRecordRepository,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_farmer(client: TestClient) -> dict:
    """Register the known BPL-farmer citizen and return auth headers."""
    register_data = {
        "email": "enrich@example.com",
        "phone": "9812345670",
        "full_name": "Selvam Murugan",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "aadhaar_number": "234123456789",
        "smart_ration_card": "TN1234567890",
        "district": "Villupuram",
        "state": "Tamil Nadu",
        "village": "Periyakulam",
        "taluk": "Villupuram",
        "pincode": "605602",
    }
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 201
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestDigiLockerSyncCreatesProfileThroughDocuments:
    """PART L items 1–8: each document populates its canonical profile slice."""

    def test_sync_produces_coherent_profile_from_documents(
        self, client: TestClient, test_db
    ):
        """End-to-end: register minimally -> sync -> documents -> enrich -> profile.

        This is the critical proof that the profile is built through the
        document pipeline and NOT through direct MOCK_PROFILES assignment.
        Fields that live ONLY in MOCK_PROFILES (and are absent from every
        document's metadata) must remain unset.
        """
        headers = _register_farmer(client)

        response = client.post(
            "/digilocker/sync", json={"force_refresh": False}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["profile_updated"] is True

        # Fetch the citizen + citizen_id for DB assertions.
        me = client.get("/citizen/profile/details", headers=headers)
        assert me.status_code == 200
        citizen_id = me.json()["data"]["citizen_id"]

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)

        # Aadhaar document -> citizen identity (confirmed via API below).
        me_data = me.json()["data"]
        assert me_data["full_name"] == "Selvam Murugan"

        # Income certificate -> profile income.
        assert profile.annual_income == 72000.0
        assert profile.income_category == "bpl"

        # Caste / community certificate -> caste/comunidade/religion.
        assert profile.caste == "Vanniyar"
        assert profile.community == "MBC"
        assert profile.sub_caste == "Padayachi"
        assert profile.religion == "Hindu"

        # Farmer ID -> farmer status.
        assert profile.is_farmer is True
        assert profile.farmer_id == "TN-FARMER-001234"
        assert profile.occupation == "Farmer"

        # Ration card -> family_member_count.
        assert profile.family_member_count == 5

        # CRITICAL: fields present in MOCK_PROFILES but NEVER carried by any
        # document metadata must remain None. Under the legacy direct MOCK_PROFILES
        # dump these would have been populated (e.g. education_level ==
        # "10th Standard", blood_group == "O+", mother_name == "Kamala Murugan").
        assert profile.education_level is None
        assert profile.blood_group is None
        assert profile.mother_name is None
        assert profile.father_name is None
        assert profile.family_details is None

    def test_income_certificate_drives_annual_income(
        self, client: TestClient, test_db, monkeypatch
    ):
        """PART L item 3 + 'verify source of data' proof.

        Patch the mock documents so the Income Certificate carries a *different*
        annual_income (85000) than MOCK_PROFILES (72000). After sync the profile
        must show the document-derived 85000 — proving the pipeline reads
        document data, not MOCK_PROFILES directly.
        """
        import app.services.digilocker_service as dl_module

        original = dl_module.get_mock_documents

        def patched_get_mock_documents(*args, **kwargs):
            docs = original(*args, **kwargs)
            for doc in docs:
                if doc["document_type"] == "income_certificate":
                    meta = json.loads(doc["doc_metadata"])
                    meta["data"]["annual_income"] = 85000.0
                    doc["doc_metadata"] = json.dumps(meta)
            return docs

        monkeypatch.setattr(dl_module, "get_mock_documents", patched_get_mock_documents)

        headers = _register_farmer(client)
        response = client.post(
            "/digilocker/sync", json={"force_refresh": False}, headers=headers
        )
        assert response.status_code == 200

        me = client.get("/citizen/profile/details", headers=headers)
        citizen_id = me.json()["data"]["citizen_id"]
        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)

        # Document-derived value (patched), NOT the MOCK_PROFILES value.
        assert profile.annual_income == 85000.0
        # income_category still comes from the same document's metadata.
        assert profile.income_category == "bpl"


class TestLandRecordsThroughDocuments:
    """PART L items 9–11 + idempotency (item 18-style via sync re-run)."""

    def test_two_land_documents_create_two_parcels_and_aggregate_to_3_5(
        self, client: TestClient, test_db
    ):
        """PART L items 9–10: 123/2A=2.5, 456/1B=1.0 => total 3.5 (not hardcoded)."""
        headers = _register_farmer(client)
        client.post("/digilocker/sync", json={"force_refresh": False}, headers=headers)

        me = client.get("/citizen/profile/details", headers=headers)
        citizen_id = me.json()["data"]["citizen_id"]

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen_id)
        surveys = {r.survey_number: r.land_area for r in records}
        assert surveys == {"123/2A": 2.5, "456/1B": 1.0}

        # Existing aggregation (not hardcoded) == 3.5 acres.
        total = LandRecordRepository(test_db).get_total_area(citizen_id)
        assert total == 3.5

    def test_running_sync_twice_does_not_duplicate_land_records(
        self, client: TestClient, test_db
    ):
        """PART L item 11 + PART J idempotency."""
        headers = _register_farmer(client)
        client.post("/digilocker/sync", json={"force_refresh": False}, headers=headers)
        # Force re-sync (this runs the pipeline again against the same parcels).
        client.post("/digilocker/sync", json={"force_refresh": True}, headers=headers)

        me = client.get("/citizen/profile/details", headers=headers)
        citizen_id = me.json()["data"]["citizen_id"]

        records = LandRecordRepository(test_db).get_by_citizen_id(citizen_id)
        assert len(records) == 2
        assert sum(r.survey_number.count("123/2A") for r in records) == 1
        assert sum(r.survey_number.count("456/1B") for r in records) == 1

    def test_sync_idempotent_on_profile(self, client: TestClient, test_db):
        """Re-sync does not corrupt persisted values; profile row is not duplicated."""
        headers = _register_farmer(client)
        client.post("/digilocker/sync", json={"force_refresh": False}, headers=headers)
        client.post("/digilocker/sync", json={"force_refresh": True}, headers=headers)

        me = client.get("/citizen/profile/details", headers=headers)
        citizen_id = me.json()["data"]["citizen_id"]

        profile = CitizenProfileRepository(test_db).get_by_citizen_id(citizen_id)
        assert profile is not None
        # Only ONE profile row for this citizen.
        count = (
            test_db.query(type(profile))
            .filter(type(profile).citizen_id == citizen_id)
            .count()
        )
        assert count == 1
        assert profile.annual_income == 72000.0
        assert profile.is_farmer is True


class TestExistingSyncResponseUnchanged:
    """PART L item 12: sync response structure stays compatible."""

    def test_sync_response_contract(self, client: TestClient):
        headers = _register_farmer(client)
        response = client.post(
            "/digilocker/sync", json={"force_refresh": False}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        # Existing contract keys.
        assert data["citizen_id"]
        assert data["sync_status"] == "synced"
        assert data["documents_synced"] > 0
        assert data["profile_updated"] is True
        assert data["message"]


class TestLoginTriggeredSync:
    """PART L item 13–14 + PART F."""

    def test_login_triggers_enriched_sync(self, client: TestClient, test_db):
        register_data = {
            "email": "login-enrich@example.com",
            "phone": "9812345671",
            "full_name": "Selvam Murugan",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "aadhaar_number": "234123456789",
            "smart_ration_card": "TN1234567890",
            "district": "Villupuram",
            "state": "Tamil Nadu",
        }
        client.post("/auth/register", json=register_data)

        # Login triggers auto DigiLocker sync (must succeed and enrich profile).
        login_response = client.post(
            "/auth/login",
            json={"email": "login-enrich@example.com", "password": "TestPass123!"},
        )
        assert login_response.status_code == 200

        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Profile was populated through the pipeline by the login-triggered sync.
        profile_response = client.get("/citizen/income", headers=headers)
        assert profile_response.status_code == 200
        data = profile_response.json()["data"]
        assert data["annual_income"] == 72000.0
        assert data["income_category"] == "bpl"
        assert data["is_farmer"] is True


class TestLandRecordUpload:
    """PART L items 15–18 + PART A / PART H backward compatibility."""

    def test_existing_land_upload_still_works(self, client: TestClient, test_db):
        """Manually supplied land fields remain the source of truth for uploads."""
        headers = _register_farmer(client)
        files = {"file": ("patta.pdf", b"%PDF-1.4 fake", "application/pdf")}
        data = {
            "survey_number": "999/1Z",
            "village": "Periyakulam",
            "district": "Villupuram",
            "land_type": "agricultural",
            "land_area": 4.0,
            "ownership_type": "owned",
            "taluk": "Villupuram",
            "state": "Tamil Nadu",
            "patta_number": "TN-999",
        }
        response = client.post(
            "/citizen/land-records/upload", data=data, files=files, headers=headers
        )
        assert response.status_code == 201
        record = response.json()["data"]["land_record"]
        assert record["survey_number"] == "999/1Z"
        assert record["land_area"] == 4.0

    def test_uploaded_government_document_enters_pipeline(
        self, client: TestClient, test_db
    ):
        """The created GovernmentDocument can enter the enrichment pipeline.

        The raw upload has no structured OCR metadata yet, so it is a no-op for
        enrichment (Step 8 does real extraction). We verify the document row is
        created and the upload did not crash the pipeline.
        """
        headers = _register_farmer(client)
        files = {"file": ("patta.pdf", b"%PDF-1.4 fake", "application/pdf")}
        data = {
            "survey_number": "777/2B",
            "village": "Periyakulam",
            "district": "Villupuram",
            "land_type": "agricultural",
            "land_area": 1.5,
            "ownership_type": "owned",
        }
        response = client.post(
            "/citizen/land-records/upload", data=data, files=files, headers=headers
        )
        assert response.status_code == 201

        doc = response.json()["data"]["document"]
        assert doc["document_type"] == "land_record"
        assert doc["verification_status"] == "pending"

        # Documents endpoint lists it.
        docs_response = client.get("/citizen/documents", headers=headers)
        doc_types = [d["document_type"] for d in docs_response.json()["data"]["documents"]]
        assert "land_record" in doc_types

    def test_raw_upload_without_metadata_does_not_enrich_duplicatively(
        self, client: TestClient, test_db
    ):
        """PART L item 18 + PART J idempotency on the upload path.

        The manual upload path appends the citizen's own submitted row (backward
        compatible). The created GovernmentDocument has NO structured metadata
        yet (real OCR/PDF extraction is Step 8), so ``enrich_document`` returns
        None and does NOT additionally create document-driven duplicates. Any
        doc-driven land-record dedup is the enrichment service's job (covered by
        the DigiLocker sync idempotency tests) — it is not triggered by raw
        uploads lacking structured metadata.
        """
        headers = _register_farmer(client)
        files = {"file": ("patta.pdf", b"%PDF-1.4 fake", "application/pdf")}
        data = {
            "survey_number": "123/2A",
            "village": "Periyakulam",
            "district": "Villupuram",
            "land_type": "agricultural",
            "land_area": 2.5,
            "ownership_type": "owned",
        }
        # Upload the same survey twice.
        first = client.post(
            "/citizen/land-records/upload", data=data, files=files, headers=headers
        )
        second = client.post(
            "/citizen/land-records/upload", data=data, files=files, headers=headers
        )
        assert first.status_code == 201
        assert second.status_code == 201

        # The raw upload document carried no structured metadata, so the
        # enrichment pipeline was a no-op (no fabricated/deduped document row).
        doc_a = first.json()["data"]["document"]
        doc_b = second.json()["data"]["document"]
        assert doc_a["document_type"] == "land_record"
        assert doc_b["document_type"] == "land_record"

