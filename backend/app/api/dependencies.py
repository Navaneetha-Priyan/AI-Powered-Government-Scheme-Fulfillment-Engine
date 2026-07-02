"""API Dependencies - Authentication and Authorization"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.jwt import verify_token
from app.core.logging import get_logger

logger = get_logger(__name__)

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> str:
    """
    Get current authenticated user ID from JWT token
    Returns: citizen_id (UUID)
    Raises: HTTPException if token is invalid or expired
    """
    if not credentials or not credentials.credentials:
        logger.warning("Missing or invalid Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "MISSING_TOKEN",
                "message": "Missing or invalid Authorization header",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token
    token = credentials.credentials

    # Verify token
    payload = verify_token(token)
    if not payload:
        logger.warning("Invalid or expired token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": "Invalid or expired token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    citizen_id: str = payload.get("sub")
    if not citizen_id:
        logger.warning("Token missing subject (citizen_id)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": "Invalid token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return citizen_id
