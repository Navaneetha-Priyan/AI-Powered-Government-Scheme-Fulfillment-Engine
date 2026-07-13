"""Integration Tests for DigiLocker API (Module 2)"""
import pytest
from fastapi.testclient import TestClient


class TestDigiLockerSync:
    """Tests for DigiLocker sync endpoint"""

    def test_sync_unauthenticated(self, client: TestClient):
        """Sync requires authentication"""
        response = client.post("/digilocker/sync", json={"force_refresh": False})
        assert response.status_code == 401

    def test_sync_success(self, client: TestClient, auth_headers_with_aadhaar: dict):
        """Sync completes successfully for citizen with Aadhaar"""
        response = client.post(
            "/digilocker/sync",
            json={"force_refresh": False},
            headers=auth_headers_with_aadhaar,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert data["sync_status"] == "synced"
        assert data["documents_synced"] > 0
        assert data["profile_updated"] is True

    def test_sync_already_synced_no_force(self, client: TestClient, auth_headers_with_aadhaar: dict):
        """Second sync without force_refresh skips re-sync"""
        # First sync
        client.post(
            "/digilocker/sync",
            json={"force_refresh": False},
            headers=auth_headers_with_aadhaar,
        )
        # Second sync without force
        response = client.post(
            "/digilocker/sync",
            json={"force_refresh": False},
            headers=auth_headers_with_aadhaar,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["sync_status"] == "synced"
        assert data["profile_updated"] is False

    def test_sync_force_refresh(self, client: TestClient, auth_headers_with_aadhaar: dict):
        """Force refresh triggers full re-sync"""
        # First sync
        client.post(
            "/digilocker/sync",
            json={"force_refresh": False},
            headers=auth_headers_with_aadhaar,
        )
        # Force re-sync
        response = client.post(
            "/digilocker/sync",
            json={"force_refresh": True},
            headers=auth_headers_with_aadhaar,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["sync_status"] == "synced"
        assert data["profile_updated"] is True

    def test_sync_citizen_without_aadhaar(self, client: TestClient, auth_headers: dict):
        """Sync works for citizen without Aadhaar (generic profile)"""
        response = client.post(
            "/digilocker/sync",
            json={"force_refresh": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert data["sync_status"] == "synced"


class TestDigiLockerStatus:
    """Tests for DigiLocker status endpoint"""

    def test_status_unauthenticated(self, client: TestClient):
        """Status requires authentication"""
        response = client.get("/digilocker/status")
        assert response.status_code == 401

    def test_status_before_sync(self, client: TestClient, auth_headers: dict):
        """Status returns not-synced state before sync"""
        response = client.get("/digilocker/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["digilocker_id"] is None
        assert data["is_active"] is False
        assert data["total_documents"] == 0

    def test_status_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Status returns synced state after sync"""
        response = client.get("/digilocker/status", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["digilocker_id"] is not None
        assert data["is_active"] is True
        assert data["last_sync_at"] is not None
        assert data["total_documents"] > 0
        assert data["verified_documents"] > 0
        assert data["sync_count"] == "1"


class TestDigiLockerDocuments:
    """Tests for DigiLocker document endpoints"""

    def test_get_documents_unauthenticated(self, client: TestClient):
        """Documents requires authentication"""
        response = client.get("/digilocker/documents")
        assert response.status_code == 401

    def test_get_documents_before_sync(self, client: TestClient, auth_headers: dict):
        """Documents returns empty list before sync"""
        response = client.get("/digilocker/documents", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["total_documents"] == 0

    def test_get_documents_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Documents returns full list after sync"""
        response = client.get("/digilocker/documents", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_documents"] > 0
        docs = data["documents"]
        assert len(docs) > 0
        # Verify document structure
        doc = docs[0]
        assert "id" in doc
        assert "document_type" in doc
        assert "document_name" in doc
        assert "verification_status" in doc
        assert "download_url" in doc

    def test_get_documents_contains_expected_types(
        self, client: TestClient, synced_auth_headers: dict
    ):
        """Synced farmer citizen has expected document types"""
        response = client.get("/digilocker/documents", headers=synced_auth_headers)
        assert response.status_code == 200
        doc_types = [d["document_type"] for d in response.json()["data"]["documents"]]
        assert "aadhaar" in doc_types
        assert "smart_ration_card" in doc_types
        assert "income_certificate" in doc_types
        assert "community_certificate" in doc_types
        assert "residence_certificate" in doc_types
        assert "farmer_id" in doc_types
        assert "land_record" in doc_types

    def test_get_document_by_id(self, client: TestClient, synced_auth_headers: dict):
        """Get specific document by ID"""
        # Get all documents first
        list_response = client.get("/digilocker/documents", headers=synced_auth_headers)
        assert list_response.status_code == 200
        docs = list_response.json()["data"]["documents"]
        assert len(docs) > 0

        doc_id = docs[0]["id"]
        response = client.get(f"/digilocker/documents/{doc_id}", headers=synced_auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["id"] == doc_id

    def test_get_document_by_invalid_id(self, client: TestClient, synced_auth_headers: dict):
        """Get document with invalid ID returns 404"""
        response = client.get(
            "/digilocker/documents/nonexistent-id-000",
            headers=synced_auth_headers,
        )
        assert response.status_code == 404

    def test_get_document_by_id_unauthenticated(self, client: TestClient):
        """Get document by ID requires authentication"""
        response = client.get("/digilocker/documents/some-id")
        assert response.status_code == 401


class TestLoginAutoSync:
    """Tests that login triggers automatic DigiLocker sync"""

    def test_login_triggers_sync(self, client: TestClient):
        """Login automatically triggers DigiLocker sync"""
        # Register with Aadhaar
        register_data = {
            "email": "autosync@example.com",
            "phone": "9876543299",
            "full_name": "Auto Sync User",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "aadhaar_number": "234123456789",
            "smart_ration_card": "TN1234567890",
            "district": "Villupuram",
            "state": "Tamil Nadu",
        }
        reg_response = client.post("/auth/register", json=register_data)
        assert reg_response.status_code == 201

        # Login — should trigger auto-sync
        login_response = client.post(
            "/auth/login",
            json={"email": "autosync@example.com", "password": "TestPass123!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check DigiLocker status — should be synced
        status_response = client.get("/digilocker/status", headers=headers)
        assert status_response.status_code == 200
        data = status_response.json()["data"]
        assert data["is_active"] is True
        assert data["total_documents"] > 0

        # The profile created by the automatic sync is immediately available.
        profile_response = client.get("/citizen/profile", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["data"]["sync_status"] == "synced"
