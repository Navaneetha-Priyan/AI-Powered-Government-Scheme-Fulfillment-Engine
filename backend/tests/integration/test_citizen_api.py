"""Integration Tests for Citizen Profile API (Module 2)"""
import pytest
from fastapi.testclient import TestClient


class TestCitizenProfileNotSynced:
    """Tests for profile endpoints before DigiLocker sync"""

    def test_get_profile_unauthenticated(self, client: TestClient):
        """Profile endpoint requires authentication"""
        response = client.get("/citizen/profile")
        assert response.status_code == 401

    def test_get_profile_details_unauthenticated(self, client: TestClient):
        """Profile details endpoint requires authentication"""
        response = client.get("/citizen/profile/details")
        assert response.status_code == 401

    def test_get_dashboard_unauthenticated(self, client: TestClient):
        """Dashboard endpoint requires authentication"""
        response = client.get("/citizen/dashboard")
        assert response.status_code == 401

    def test_get_income_unauthenticated(self, client: TestClient):
        """Income endpoint requires authentication"""
        response = client.get("/citizen/income")
        assert response.status_code == 401

    def test_get_caste_unauthenticated(self, client: TestClient):
        """Caste endpoint requires authentication"""
        response = client.get("/citizen/caste")
        assert response.status_code == 401

    def test_get_land_records_unauthenticated(self, client: TestClient):
        """Land records endpoint requires authentication"""
        response = client.get("/citizen/land-records")
        assert response.status_code == 401

    def test_get_documents_unauthenticated(self, client: TestClient):
        """Documents endpoint requires authentication"""
        response = client.get("/citizen/documents")
        assert response.status_code == 401

    def test_get_profile_before_sync_returns_404(self, client: TestClient, auth_headers: dict):
        """Profile returns 404 before DigiLocker sync"""
        response = client.get("/citizen/profile", headers=auth_headers)
        assert response.status_code == 404

    def test_get_income_before_sync_returns_404(self, client: TestClient, auth_headers: dict):
        """Income returns 404 before DigiLocker sync"""
        response = client.get("/citizen/income", headers=auth_headers)
        assert response.status_code == 404

    def test_get_caste_before_sync_returns_404(self, client: TestClient, auth_headers: dict):
        """Caste returns 404 before DigiLocker sync"""
        response = client.get("/citizen/caste", headers=auth_headers)
        assert response.status_code == 404

    def test_get_dashboard_before_sync_returns_200(self, client: TestClient, auth_headers: dict):
        """Dashboard returns 200 even before sync (with empty profile)"""
        response = client.get("/citizen/dashboard", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert data["digilocker_synced"] is False
        assert data["land_records"] == []
        assert data["total_documents"] == 0

    def test_get_land_records_before_sync_returns_200(self, client: TestClient, auth_headers: dict):
        """Land records returns 200 with empty list before sync"""
        response = client.get("/citizen/land-records", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["total_records"] == 0

    def test_get_documents_before_sync_returns_200(self, client: TestClient, auth_headers: dict):
        """Documents returns 200 with empty list before sync"""
        response = client.get("/citizen/documents", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["total_documents"] == 0


class TestCitizenProfileAfterSync:
    """Tests for profile endpoints after DigiLocker sync"""

    def test_get_profile_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Profile returns full data after sync"""
        response = client.get("/citizen/profile", headers=synced_auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert data["sync_status"] == "synced"
        assert data["profile_completion_percentage"] > 0
        assert data["is_farmer"] is True
        assert data["income_category"] == "bpl"

    def test_get_profile_details_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Profile details returns combined data after sync"""
        response = client.get("/citizen/profile/details", headers=synced_auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert data["full_name"] == "Selvam Murugan"
        assert data["aadhaar_number"] == "234123456789"
        assert data["extended_profile"] is not None
        assert data["extended_profile"]["caste"] == "Vanniyar"

    def test_get_dashboard_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Dashboard returns complete data after sync"""
        response = client.get("/citizen/dashboard", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["digilocker_synced"] is True
        assert data["total_documents"] > 0
        assert data["verified_documents"] > 0
        assert len(data["land_records"]) > 0
        assert data["total_land_area"] > 0
        assert data["profile_completion_percentage"] > 0

    def test_get_income_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Income details returns correct data after sync"""
        response = client.get("/citizen/income", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["annual_income"] == 72000.0
        assert data["income_category"] == "bpl"
        assert data["occupation"] == "Farmer"
        assert data["is_farmer"] is True

    def test_get_caste_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Caste details returns correct data after sync"""
        response = client.get("/citizen/caste", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["caste"] == "Vanniyar"
        assert data["community"] == "MBC"
        assert data["religion"] == "Hindu"

    def test_get_land_records_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Land records returns correct data after sync"""
        response = client.get("/citizen/land-records", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_records"] == 2
        assert data["total_land_area"] == 3.5
        assert len(data["land_records"]) == 2
        assert data["land_records"][0]["land_type"] == "agricultural"

    def test_get_documents_after_sync(self, client: TestClient, synced_auth_headers: dict):
        """Documents returns correct data after sync"""
        response = client.get("/citizen/documents", headers=synced_auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_documents"] > 0
        doc_types = [d["document_type"] for d in data["documents"]]
        assert "aadhaar" in doc_types
        assert "smart_ration_card" in doc_types
        assert "income_certificate" in doc_types
        assert "farmer_id" in doc_types

    def test_update_profile(self, client: TestClient, synced_auth_headers: dict):
        """Update profile fields"""
        update_data = {
            "occupation": "Agricultural Laborer",
            "family_member_count": 6,
        }
        response = client.put("/citizen/profile", json=update_data, headers=synced_auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert data["occupation"] == "Agricultural Laborer"
        assert data["family_member_count"] == 6

    def test_update_profile_unauthenticated(self, client: TestClient):
        """Update profile requires authentication"""
        response = client.put("/citizen/profile", json={"occupation": "Farmer"})
        assert response.status_code == 401


class TestCitizenProfileDetails:
    """Tests for profile details endpoint"""

    def test_get_profile_details_no_extended_profile(
        self, client: TestClient, auth_headers: dict
    ):
        """Profile details returns None for extended_profile when not synced"""
        response = client.get("/citizen/profile/details", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["extended_profile"] is None
