"""Unit Tests for Validators"""
import pytest
from app.validators.validators import (
    AadhaarValidator,
    RationCardValidator,
    EmailValidator,
    PhoneValidator,
    NameValidator,
    PincodeValidator,
    AgeValidator,
)


class TestAadhaarValidator:
    """Test Aadhaar validation"""

    def test_valid_aadhaar(self):
        """Test valid Aadhaar number"""
        # Valid Aadhaar with correct checksum
        is_valid, error = AadhaarValidator.validate("123456789012")
        assert is_valid is True

    def test_invalid_aadhaar_length(self):
        """Test invalid Aadhaar length"""
        is_valid, error = AadhaarValidator.validate("12345678901")
        assert is_valid is False
        assert "12 digits" in error

    def test_invalid_aadhaar_all_zeros(self):
        """Test all zeros Aadhaar"""
        is_valid, error = AadhaarValidator.validate("000000000000")
        assert is_valid is False

    def test_invalid_aadhaar_non_numeric(self):
        """Test non-numeric Aadhaar"""
        is_valid, error = AadhaarValidator.validate("12345678901a")
        assert is_valid is False


class TestRationCardValidator:
    """Test Ration Card validation"""

    def test_valid_ration_card(self):
        """Test valid Ration Card"""
        is_valid, error = RationCardValidator.validate("TN1234567890")
        assert is_valid is True

    def test_invalid_ration_card_format(self):
        """Test invalid format"""
        is_valid, error = RationCardValidator.validate("1234567890")
        assert is_valid is False

    def test_invalid_ration_card_state_code(self):
        """Test invalid state code"""
        is_valid, error = RationCardValidator.validate("XX1234567890")
        assert is_valid is False

    def test_ration_card_case_insensitive(self):
        """Test case insensitivity"""
        is_valid, error = RationCardValidator.validate("tn1234567890")
        assert is_valid is True


class TestEmailValidator:
    """Test Email validation"""

    def test_valid_email(self):
        """Test valid email"""
        is_valid, error = EmailValidator.validate("test@example.com")
        assert is_valid is True

    def test_invalid_email_no_domain(self):
        """Test email without domain"""
        is_valid, error = EmailValidator.validate("test@")
        assert is_valid is False

    def test_invalid_email_consecutive_dots(self):
        """Test consecutive dots"""
        is_valid, error = EmailValidator.validate("test..email@example.com")
        assert is_valid is False

    def test_invalid_email_no_at(self):
        """Test email without @"""
        is_valid, error = EmailValidator.validate("testexample.com")
        assert is_valid is False


class TestPhoneValidator:
    """Test Phone validation"""

    def test_valid_phone(self):
        """Test valid phone"""
        is_valid, error = PhoneValidator.validate("9876543210")
        assert is_valid is True

    def test_valid_phone_with_country_code_91(self):
        """Test phone with 91 prefix"""
        is_valid, error = PhoneValidator.validate("919876543210")
        assert is_valid is True

    def test_valid_phone_with_country_code_plus(self):
        """Test phone with +91 prefix"""
        is_valid, error = PhoneValidator.validate("+919876543210")
        assert is_valid is True

    def test_invalid_phone_starting_with_5(self):
        """Test phone starting with 5"""
        is_valid, error = PhoneValidator.validate("5876543210")
        assert is_valid is False

    def test_invalid_phone_short(self):
        """Test short phone"""
        is_valid, error = PhoneValidator.validate("987654321")
        assert is_valid is False


class TestNameValidator:
    """Test Name validation"""

    def test_valid_name(self):
        """Test valid name"""
        is_valid, error = NameValidator.validate("John Doe")
        assert is_valid is True

    def test_valid_name_with_hyphen(self):
        """Test name with hyphen"""
        is_valid, error = NameValidator.validate("Mary-Jane")
        assert is_valid is True

    def test_invalid_name_too_short(self):
        """Test name too short"""
        is_valid, error = NameValidator.validate("A")
        assert is_valid is False

    def test_invalid_name_with_numbers(self):
        """Test name with numbers"""
        is_valid, error = NameValidator.validate("John123")
        assert is_valid is False

    def test_invalid_name_excessive_spaces(self):
        """Test excessive spaces"""
        is_valid, error = NameValidator.validate("John  Doe")
        assert is_valid is False


class TestPincodeValidator:
    """Test Pincode validation"""

    def test_valid_pincode(self):
        """Test valid pincode"""
        is_valid, error = PincodeValidator.validate("600001")
        assert is_valid is True

    def test_invalid_pincode_short(self):
        """Test short pincode"""
        is_valid, error = PincodeValidator.validate("60001")
        assert is_valid is False

    def test_invalid_pincode_long(self):
        """Test long pincode"""
        is_valid, error = PincodeValidator.validate("6000001")
        assert is_valid is False

    def test_invalid_pincode_non_numeric(self):
        """Test non-numeric pincode"""
        is_valid, error = PincodeValidator.validate("6000a1")
        assert is_valid is False


class TestAgeValidator:
    """Test Age validation"""

    def test_valid_age(self):
        """Test valid age"""
        is_valid, error = AgeValidator.validate(25)
        assert is_valid is True

    def test_invalid_age_too_young(self):
        """Test age too young"""
        is_valid, error = AgeValidator.validate(15)
        assert is_valid is False

    def test_invalid_age_too_old(self):
        """Test age too old"""
        is_valid, error = AgeValidator.validate(150)
        assert is_valid is False

    def test_invalid_age_type(self):
        """Test invalid type"""
        is_valid, error = AgeValidator.validate("25")
        assert is_valid is False
