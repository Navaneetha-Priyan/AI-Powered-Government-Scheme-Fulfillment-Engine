"""Logging Configuration"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings


def setup_logging() -> None:
    """Configure logging with rotation and console output"""

    # Create logs directory if it doesn't exist
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # File handler with rotation
    log_file = log_dir / settings.LOG_FILE
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a specific module"""
    return logging.getLogger(name)


# Specialized loggers
def get_auth_logger() -> logging.Logger:
    """Get authentication logger"""
    return logging.getLogger("app.auth")


def get_audit_logger() -> logging.Logger:
    """Get audit logger"""
    return logging.getLogger("app.audit")


def get_security_logger() -> logging.Logger:
    """Get security logger"""
    return logging.getLogger("app.security")


def get_database_logger() -> logging.Logger:
    """Get database logger"""
    return logging.getLogger("app.database")
