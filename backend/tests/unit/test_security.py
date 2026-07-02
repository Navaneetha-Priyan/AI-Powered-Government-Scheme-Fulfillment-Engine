"""Unit Tests for Security Functions"""
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20
        assert verify_password(password, hashed)

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_same_password(self):
        """Test that same password produces different hashes"""
        password = "MySecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different (bcrypt adds salt)
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestPasswordStrengthValidation:
    """Test password strength validation"""

    def test_strong_password(self):
        """Test strong password"""
        is_valid, error = validate_password_strength("StrongPass123!")
        assert is_valid is True
        assert error == ""

    def test_password_too_short(self):
        """Test password too short"""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "8 characters" in error

    def test_password_no_uppercase(self):
        """Test password without uppercase"""
        is_valid, error = validate_password_strength("password123!")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_no_lowercase(self):
        """Test password without lowercase"""
        is_valid, error = validate_password_strength("PASSWORD123!")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_no_digit(self):
        """Test password without digit"""
        is_valid, error = validate_password_strength("StrongPass!")
        assert is_valid is False
        assert "digit" in error.lower()

    def test_password_no_special_char(self):
        """Test password without special character"""
        is_valid, error = validate_password_strength("StrongPass123")
        assert is_valid is False
        assert "special character" in error.lower()

    def test_common_strong_passwords(self):
        """Test common strong passwords"""
        strong_passwords = [
            "TestPass123!",
            "MySecure@Pass2024",
            "Citizen#2024Auth",
            "Login@123Secure",
        ]
        
        for password in strong_passwords:
            is_valid, error = validate_password_strength(password)
            assert is_valid is True, f"Password '{password}' should be valid: {error}"

    def test_common_weak_passwords(self):
        """Test common weak passwords"""
        weak_passwords = [
            "password",
            "123456",
            "123456!",
            "abcdef!",
            "ABCDEF!",
        ]
        
        for password in weak_passwords:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False, f"Password '{password}' should be invalid"
