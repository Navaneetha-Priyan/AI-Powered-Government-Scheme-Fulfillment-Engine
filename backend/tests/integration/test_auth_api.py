"""Integration Tests for Authentication API"""
import pytest
from fastapi.testclient import TestClient


class TestRegistration:
    """Test registration endpoints"""

    def test_register_success(self, client: TestClient):
        """Test successful registration"""
        register_data = {
            "email": "newuser@example.com",
            "phone": "9876543210",
            "full_name": "New User",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }
        
        response = client.post("/auth/register", json=register_data)
        
        assert response.status_code == 201
        assert response.json()["success"] is True
        assert "access_token" in response.json()["data"]
        assert "refresh_token" in response.json()["data"]
        assert response.json()["data"]["citizen_id"]

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email"""
        register_data = {
            "email": "test@example.com",
            "phone": "9876543210",
            "full_name": "Test User",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }

        # Register first user
        response1 = client.post("/auth/register", json=register_data)
        assert response1.status_code == 201

        # Try to register with same email
        register_data["phone"] = "9876543211"
        response2 = client.post("/auth/register", json=register_data)
        assert response2.status_code == 409
        assert response2.json()["detail"]["error"] == "DUPLICATE_EMAIL"

    def test_register_duplicate_phone(self, client: TestClient):
        """Test registration with duplicate phone"""
        register_data = {
            "email": "test1@example.com",
            "phone": "9876543210",
            "full_name": "Test User One",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }
        
        # Register first user
        response1 = client.post("/auth/register", json=register_data)
        assert response1.status_code == 201
        
        # Try to register with same phone
        register_data["email"] = "test2@example.com"
        response2 = client.post("/auth/register", json=register_data)
        assert response2.status_code == 409

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password"""
        register_data = {
            "email": "newuser@example.com",
            "phone": "9876543210",
            "full_name": "New User",
            "password": "weak",
            "confirm_password": "weak",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }

        response = client.post("/auth/register", json=register_data)

        assert response.status_code == 422

    def test_register_password_mismatch(self, client: TestClient):
        """Test registration with mismatched passwords"""
        register_data = {
            "email": "newuser@example.com",
            "phone": "9876543210",
            "full_name": "New User",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }

        response = client.post("/auth/register", json=register_data)

        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email"""
        register_data = {
            "email": "invalid-email",
            "phone": "9876543210",
            "full_name": "New User",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }
        
        response = client.post("/auth/register", json=register_data)
        
        assert response.status_code == 422


class TestLogin:
    """Test login endpoints"""

    def test_login_success(self, client: TestClient):
        """Test successful login"""
        # Register user first
        register_data = {
            "email": "testuser@example.com",
            "phone": "9876543210",
            "full_name": "Test User",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }
        client.post("/auth/register", json=register_data)
        
        # Login
        login_data = {
            "email": "testuser@example.com",
            "password": "TestPass123!",
        }
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "access_token" in response.json()["data"]
        assert "refresh_token" in response.json()["data"]

    def test_login_invalid_email(self, client: TestClient):
        """Test login with invalid email"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPass123!",
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401

    def test_login_invalid_password(self, client: TestClient):
        """Test login with invalid password"""
        # Register user first
        register_data = {
            "email": "testuser2@example.com",
            "phone": "9876543211",
            "full_name": "Test User 2",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }
        client.post("/auth/register", json=register_data)

        # Login with wrong password
        login_data = {
            "email": "testuser2@example.com",
            "password": "WrongPassword123!",
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401


class TestProfile:
    """Test profile endpoints"""

    def test_get_profile_authenticated(self, client: TestClient, auth_headers: dict):
        """Test getting profile when authenticated"""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["email"] == "test@example.com"
        assert response.json()["data"]["full_name"] == "Test User"

    def test_get_profile_unauthenticated(self, client: TestClient):
        """Test getting profile without authentication"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401

    def test_update_profile(self, client: TestClient, auth_headers: dict):
        """Test updating profile"""
        update_data = {
            "full_name": "Updated User",
            "gender": "male",
            "village": "Sample Village",
        }
        
        response = client.put("/auth/profile", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["full_name"] == "Updated User"
        assert response.json()["data"]["gender"] == "male"
        assert response.json()["data"]["village"] == "Sample Village"

    def test_change_password_success(self, client: TestClient, auth_headers: dict):
        """Test successful password change"""
        change_data = {
            "old_password": "TestPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }
        
        response = client.put("/auth/change-password", json=change_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_change_password_wrong_old(self, client: TestClient, auth_headers: dict):
        """Test password change with wrong old password"""
        change_data = {
            "old_password": "WrongPassword123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }
        
        response = client.put("/auth/change-password", json=change_data, headers=auth_headers)
        
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh endpoints"""

    def test_refresh_token_success(self, client: TestClient):
        """Test successful token refresh"""
        # Register and get tokens
        register_data = {
            "email": "refreshtest@example.com",
            "phone": "9876543212",
            "full_name": "Refresh Test",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "district": "Chennai",
            "state": "Tamil Nadu",
        }
        
        reg_response = client.post("/auth/register", json=register_data)
        refresh_token = reg_response.json()["data"]["refresh_token"]
        
        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "access_token" in response.json()["data"]

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token"""
        refresh_data = {"refresh_token": "invalid-token"}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401


class TestLogout:
    """Test logout endpoint"""

    def test_logout_authenticated(self, client: TestClient, auth_headers: dict):
        """Test logout when authenticated"""
        response = client.post("/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_logout_unauthenticated(self, client: TestClient):
        """Test logout without authentication"""
        response = client.post("/auth/logout")
        
        assert response.status_code == 401


class TestHealthCheck:
    """Test health check endpoints"""

    def test_health_check(self, client: TestClient):
        """Test health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["status"] == "healthy"

    def test_version_endpoint(self, client: TestClient):
        """Test version endpoint"""
        response = client.get("/version")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "version" in response.json()["data"]

    def test_info_endpoint(self, client: TestClient):
        """Test info endpoint"""
        response = client.get("/info")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "app_name" in response.json()["data"]
