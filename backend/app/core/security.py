"""Security Module - Password Hashing and Verification"""
from passlib.context import CryptContext
from typing import Tuple

# Initialize password context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Increase security with more rounds
)


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength based on policy
    Returns: (is_valid, error_message)
    """
    from app.core.config import settings

    # Check minimum length
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return (
            False,
            f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long",
        )

    # Check for uppercase
    if settings.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    # Check for lowercase
    if settings.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    # Check for digits
    if settings.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    # Check for special characters
    if settings.REQUIRE_SPECIAL_CHARS:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return (
                False,
                "Password must contain at least one special character (!@#$%^&*...)",
            )

    return True, ""
