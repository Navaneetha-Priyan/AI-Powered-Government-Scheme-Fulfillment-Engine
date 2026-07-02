"""Custom Exception Classes"""
from typing import Optional, Any, Dict


class AppException(Exception):
    """Base exception for the application"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(AppException):
    """Validation error"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(AppException):
    """Authentication failed"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(AppException):
    """User not authorized"""

    def __init__(self, message: str = "User not authorized"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
        )


class NotFoundError(AppException):
    """Resource not found"""

    def __init__(self, message: str = "Resource not found", resource: str = ""):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource} if resource else {},
        )


class ConflictError(AppException):
    """Conflict - resource already exists"""

    def __init__(self, message: str, resource: str = ""):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details={"resource": resource} if resource else {},
        )


class TokenExpiredError(AuthenticationError):
    """Token expired"""

    def __init__(self):
        super().__init__("Token has expired")
        self.error_code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """Invalid token"""

    def __init__(self):
        super().__init__("Invalid token")
        self.error_code = "INVALID_TOKEN"


class DuplicateEmailError(ConflictError):
    """Email already exists"""

    def __init__(self, email: str):
        super().__init__(
            message=f"Email '{email}' is already registered",
            resource="citizen",
        )
        self.error_code = "DUPLICATE_EMAIL"


class DuplicatePhoneError(ConflictError):
    """Phone already exists"""

    def __init__(self, phone: str):
        super().__init__(
            message=f"Phone '{phone}' is already registered",
            resource="citizen",
        )
        self.error_code = "DUPLICATE_PHONE"


class DuplicateAadhaarError(ConflictError):
    """Aadhaar already exists"""

    def __init__(self, aadhaar: str):
        super().__init__(
            message=f"Aadhaar '{aadhaar}' is already registered",
            resource="citizen",
        )
        self.error_code = "DUPLICATE_AADHAAR"


class DuplicateRationCardError(ConflictError):
    """Ration Card already exists"""

    def __init__(self, ration_card: str):
        super().__init__(
            message=f"Ration Card '{ration_card}' is already registered",
            resource="citizen",
        )
        self.error_code = "DUPLICATE_RATION_CARD"


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password"""

    def __init__(self):
        super().__init__("Invalid email or password")
        self.error_code = "INVALID_CREDENTIALS"


class AccountDisabledError(AuthenticationError):
    """Account is disabled"""

    def __init__(self):
        super().__init__("Your account has been disabled")
        self.error_code = "ACCOUNT_DISABLED"


class EmailNotVerifiedError(AuthenticationError):
    """Email not verified"""

    def __init__(self):
        super().__init__("Email verification is required")
        self.error_code = "EMAIL_NOT_VERIFIED"


class InvalidAadhaarError(ValidationError):
    """Invalid Aadhaar number"""

    def __init__(self, reason: str = "Invalid Aadhaar number"):
        super().__init__(message=reason)
        self.error_code = "INVALID_AADHAAR"


class InvalidRationCardError(ValidationError):
    """Invalid Ration Card number"""

    def __init__(self, reason: str = "Invalid Ration Card number"):
        super().__init__(message=reason)
        self.error_code = "INVALID_RATION_CARD"


class InvalidEmailError(ValidationError):
    """Invalid email format"""

    def __init__(self, email: str = ""):
        super().__init__(message=f"Invalid email format: {email}")
        self.error_code = "INVALID_EMAIL"


class InvalidPhoneError(ValidationError):
    """Invalid phone format"""

    def __init__(self, phone: str = ""):
        super().__init__(message=f"Invalid phone number: {phone}")
        self.error_code = "INVALID_PHONE"


class WeakPasswordError(ValidationError):
    """Password does not meet security requirements"""

    def __init__(self, reason: str = "Password does not meet security requirements"):
        super().__init__(message=reason)
        self.error_code = "WEAK_PASSWORD"


class DatabaseError(AppException):
    """Database operation error"""

    def __init__(self, message: str = "Database error occurred"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
        )


class InternalServerError(AppException):
    """Internal server error"""

    def __init__(self, message: str = "Internal server error occurred"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
        )
