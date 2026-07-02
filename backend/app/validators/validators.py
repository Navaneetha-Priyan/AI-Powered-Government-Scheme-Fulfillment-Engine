"""Validators for Aadhaar and Ration Card"""
import re
from typing import Tuple
from app.exceptions.exceptions import InvalidAadhaarError, InvalidRationCardError


class AadhaarValidator:
    """Validate Aadhaar number"""

    # Aadhaar is a 12-digit unique identity
    AADHAAR_PATTERN = re.compile(r"^\d{12}$")

    @staticmethod
    def validate(aadhaar: str) -> Tuple[bool, str]:
        """
        Validate Aadhaar number
        Returns: (is_valid, error_message)

        Validation rules:
        1. Must be exactly 12 digits
        2. Cannot be all zeros
        3. Implements Verhoeff checksum algorithm
        """
        # Remove whitespace
        aadhaar = aadhaar.strip()

        # Check if it matches pattern (12 digits)
        if not AadhaarValidator.AADHAAR_PATTERN.match(aadhaar):
            return False, "Aadhaar must be exactly 12 digits"

        # Check if all zeros
        if aadhaar == "000000000000":
            return False, "Aadhaar cannot be all zeros"

        # Verify Verhoeff checksum
        if not AadhaarValidator._verify_verhoeff_checksum(aadhaar):
            return False, "Aadhaar checksum validation failed"

        return True, ""

    @staticmethod
    def _verify_verhoeff_checksum(aadhaar: str) -> bool:
        """
        Verify Verhoeff checksum for Aadhaar
        Verhoeff algorithm is used for error detection in Aadhaar numbers
        """
        # Verhoeff lookup tables
        d_table = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        ]

        p_table = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        ]

        inv_table = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

        # Calculate checksum
        c = 0
        for i, digit in enumerate(reversed(aadhaar)):
            c = d_table[c][p_table[(i + 1) % 8][int(digit)]]

        return c == 0


class RationCardValidator:
    """Validate Smart Ration Card number"""

    # Ration card format: AAABXXXXXXXY (State Code + Unique Number)
    # More flexible pattern for various state formats
    RATION_CARD_PATTERN = re.compile(r"^[A-Z]{2,3}\d{6,12}$", re.IGNORECASE)

    @staticmethod
    def validate(ration_card: str) -> Tuple[bool, str]:
        """
        Validate Ration Card number
        Returns: (is_valid, error_message)

        Validation rules:
        1. Must contain 2-3 uppercase letters (state code)
        2. Followed by 6-12 digits
        3. Total length 8-15 characters
        """
        # Remove whitespace and convert to uppercase
        ration_card = ration_card.strip().upper()

        # Check minimum length
        if len(ration_card) < 8:
            return False, "Ration Card number is too short"

        # Check maximum length
        if len(ration_card) > 15:
            return False, "Ration Card number is too long"

        # Check if it matches pattern
        if not RationCardValidator.RATION_CARD_PATTERN.match(ration_card):
            return (
                False,
                "Invalid Ration Card format. Should be state code (2-3 letters) + number (6-12 digits)",
            )

        # Extract state code and validate it's known
        state_code = ration_card[:2]
        if not RationCardValidator._is_valid_state_code(state_code):
            return False, f"Unknown state code: {state_code}"

        return True, ""

    @staticmethod
    def _is_valid_state_code(code: str) -> bool:
        """
        Validate Indian state codes
        Returns: True if valid state code
        """
        valid_state_codes = {
            # Union Territories and States
            "AN",  # Andaman and Nicobar Islands
            "AP",  # Andhra Pradesh
            "AR",  # Arunachal Pradesh
            "AS",  # Assam
            "BR",  # Bihar
            "CG",  # Chhattisgarh
            "CH",  # Chandigarh
            "CT",  # Chhattisgarh (alternate)
            "DD",  # Daman and Diu
            "DL",  # Delhi
            "GA",  # Goa
            "GJ",  # Gujarat
            "HR",  # Haryana
            "HP",  # Himachal Pradesh
            "JK",  # Jammu and Kashmir
            "JH",  # Jharkhand
            "KA",  # Karnataka
            "KL",  # Kerala
            "LA",  # Ladakh
            "LD",  # Lakshadweep
            "MP",  # Madhya Pradesh
            "MH",  # Maharashtra
            "MN",  # Manipur
            "ML",  # Meghalaya
            "MZ",  # Mizoram
            "NL",  # Nagaland
            "OD",  # Odisha
            "OR",  # Odisha (alternate)
            "PB",  # Punjab
            "PY",  # Puducherry
            "RJ",  # Rajasthan
            "SK",  # Sikkim
            "TN",  # Tamil Nadu
            "TR",  # Tripura
            "UP",  # Uttar Pradesh
            "UK",  # Uttarakhand
            "UT",  # Uttarakhand (alternate)
            "WB",  # West Bengal
        }
        return code.upper() in valid_state_codes


class EmailValidator:
    """Validate email format"""

    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    @staticmethod
    def validate(email: str) -> Tuple[bool, str]:
        """Validate email format"""
        email = email.strip()

        if not email or len(email) > 254:
            return False, "Invalid email format"

        if not EmailValidator.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"

        # Check for consecutive dots
        if ".." in email:
            return False, "Invalid email format (consecutive dots)"

        # Check for valid local part
        local_part = email.split("@")[0]
        if len(local_part) > 64:
            return False, "Email local part is too long"

        return True, ""


class PhoneValidator:
    """Validate phone number"""

    # Indian phone numbers are 10 digits starting with 6-9
    PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")

    @staticmethod
    def validate(phone: str) -> Tuple[bool, str]:
        """Validate Indian phone number"""
        # Remove common formatting characters
        phone = re.sub(r"[\s\-\(\)]", "", phone.strip())

        # Remove country code if present
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91"):
            phone = phone[2:]

        # Check format
        if not PhoneValidator.PHONE_PATTERN.match(phone):
            return False, "Invalid phone number. Must be 10 digits starting with 6-9"

        return True, ""


class NameValidator:
    """Validate person's name"""

    @staticmethod
    def validate(name: str) -> Tuple[bool, str]:
        """Validate name format"""
        name = name.strip()

        # Check length
        if len(name) < 2:
            return False, "Name must be at least 2 characters long"

        if len(name) > 100:
            return False, "Name must not exceed 100 characters"

        # Allow letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            return False, "Name contains invalid characters"

        # Check for multiple consecutive spaces
        if "  " in name:
            return False, "Name contains excessive spaces"

        return True, ""


class AgeValidator:
    """Validate age"""

    @staticmethod
    def validate(age: int, min_age: int = 18, max_age: int = 120) -> Tuple[bool, str]:
        """Validate age"""
        if not isinstance(age, int):
            return False, "Age must be a number"

        if age < min_age:
            return False, f"Must be at least {min_age} years old"

        if age > max_age:
            return False, f"Age must be less than {max_age}"

        return True, ""


class PincodeValidator:
    """Validate Indian pincode"""

    PINCODE_PATTERN = re.compile(r"^\d{6}$")

    @staticmethod
    def validate(pincode: str) -> Tuple[bool, str]:
        """Validate pincode format"""
        pincode = pincode.strip()

        if not PincodeValidator.PINCODE_PATTERN.match(pincode):
            return False, "Pincode must be exactly 6 digits"

        return True, ""
