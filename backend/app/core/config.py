"""Configuration Management for FastAPI Application"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application Configuration"""

    # Application Info
    APP_NAME: str = "Citizen Registration & Authentication API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Module 1: Secure registration and login system for citizens"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        """Accept common deployment labels while preserving boolean settings."""
        if isinstance(value, str) and value.lower() in {"release", "production"}:
            return False
        return value

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_RELOAD: bool = True

    # Database Configuration
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/govt_scheme_db"
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_POOL_SIZE: int = 20
    SQLALCHEMY_POOL_RECYCLE: int = 3600

    # JWT Configuration
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Password Policy
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGITS: bool = True
    REQUIRE_SPECIAL_CHARS: bool = True

    # Email Configuration
    ALLOWED_EMAIL_DOMAINS: List[str] = ["*"]

    # Logging Configuration
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File Upload Configuration (Future Module 7)
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    SCHEME_STORAGE_DIR: str = "storage/schemes"
    MAX_SCHEME_PDF_SIZE_BYTES: int = 10485760
    SCHEME_CHUNK_SIZE: int = 900
    SCHEME_CHUNK_OVERLAP: int = 120
    CHROMA_PERSIST_DIRECTORY: str = "storage/chromadb"
    CHROMA_COLLECTION_NAME: str = "government_scheme_chunks"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Recommendation Engine Configuration
    RECOMMENDATION_TOP_K: int = 5
    RECOMMENDATION_CANDIDATE_LIMIT: int = 20
    RECOMMENDATION_MIN_ELIGIBILITY_SCORE: float = 0.55
    RECOMMENDATION_ELIGIBILITY_WEIGHT: float = 0.45
    RECOMMENDATION_SIMILARITY_WEIGHT: float = 0.25
    RECOMMENDATION_BENEFIT_WEIGHT: float = 0.15
    RECOMMENDATION_PROFILE_WEIGHT: float = 0.10
    RECOMMENDATION_DOCUMENT_WEIGHT: float = 0.05

    # API Documentation
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # Feature Flags
    ENABLE_AADHAAR_VALIDATION: bool = True
    ENABLE_RATION_CARD_VALIDATION: bool = True
    ENABLE_AUDIT_LOGGING: bool = True

    class Config:
        """Pydantic Configuration"""

        env_file = ".env"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get database URL"""
        return self.DATABASE_URL

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create settings instance
settings = get_settings()
