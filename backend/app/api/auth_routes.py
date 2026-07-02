"""Authentication API Routes"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.citizen import (
    CitizenRegisterRequest,
    CitizenLoginRequest,
    CitizenProfileResponse,
    CitizenUpdateProfileRequest,
    ChangePasswordRequest,
    TokenResponse,
    RefreshTokenRequest,
    VerifyTokenRequest,
    VerifyTokenResponse,
    SuccessResponse,
    ErrorResponse,
)
from app.services.auth_service import AuthenticationService
from app.exceptions.exceptions import AppException
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=SuccessResponse,
    status_code=201,
    summary="Register a new citizen",
    description="Create a new citizen account with email, phone, and password",
)
async def register(
    register_data: CitizenRegisterRequest, db: Session = Depends(get_db)
):
    """Register a new citizen"""
    try:
        auth_service = AuthenticationService(db)
        citizen, token_response = auth_service.register(register_data)

        return SuccessResponse(
            success=True,
            message="Registration successful",
            data={
                "citizen_id": citizen.id,
                "email": citizen.email,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in,
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred during registration",
            },
        )


@router.post(
    "/login",
    response_model=SuccessResponse,
    status_code=200,
    summary="Login citizen",
    description="Login with email and password",
)
async def login(login_data: CitizenLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login citizen"""
    try:
        ip_address = request.client.host if request.client else None
        auth_service = AuthenticationService(db)
        token_response = auth_service.login(login_data, ip_address)

        return SuccessResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in,
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred during login",
            },
        )


@router.post(
    "/refresh",
    response_model=SuccessResponse,
    status_code=200,
    summary="Refresh access token",
    description="Get a new access token using refresh token",
)
async def refresh(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token"""
    try:
        auth_service = AuthenticationService(db)
        token_response = auth_service.refresh_token(refresh_data.refresh_token)

        return SuccessResponse(
            success=True,
            message="Token refreshed successfully",
            data={
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in,
            },
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred during token refresh",
            },
        )


@router.get(
    "/me",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get current user profile",
    description="Get the profile of the currently logged in citizen",
)
async def get_me(
    current_user_id: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user profile"""
    try:
        auth_service = AuthenticationService(db)
        profile = auth_service.get_profile(current_user_id)

        return SuccessResponse(
            success=True,
            message="Profile retrieved successfully",
            data=profile.model_dump(),
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred while fetching profile",
            },
        )


@router.put(
    "/profile",
    response_model=SuccessResponse,
    status_code=200,
    summary="Update user profile",
    description="Update the profile of the currently logged in citizen",
)
async def update_profile(
    update_data: CitizenUpdateProfileRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile"""
    try:
        auth_service = AuthenticationService(db)
        profile = auth_service.update_profile(current_user_id, update_data)

        return SuccessResponse(
            success=True,
            message="Profile updated successfully",
            data=profile.model_dump(),
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred while updating profile",
            },
        )


@router.put(
    "/change-password",
    response_model=SuccessResponse,
    status_code=200,
    summary="Change password",
    description="Change the password of the currently logged in citizen",
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password"""
    try:
        auth_service = AuthenticationService(db)
        auth_service.change_password(current_user_id, password_data)

        return SuccessResponse(
            success=True,
            message="Password changed successfully",
            data=None,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred while changing password",
            },
        )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    status_code=200,
    summary="Logout citizen",
    description="Logout the currently logged in citizen",
)
async def logout(
    current_user_id: str = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Logout citizen"""
    try:
        auth_service = AuthenticationService(db)
        auth_service.logout(current_user_id)

        return SuccessResponse(
            success=True,
            message="Logged out successfully",
            data=None,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred during logout",
            },
        )


@router.post(
    "/verify-token",
    response_model=SuccessResponse,
    status_code=200,
    summary="Verify token",
    description="Verify if a token is valid",
)
async def verify_token(
    verify_data: VerifyTokenRequest, db: Session = Depends(get_db)
):
    """Verify token"""
    try:
        auth_service = AuthenticationService(db)
        result = auth_service.verify_token(verify_data.token)

        return SuccessResponse(
            success=True,
            message="Token is valid",
            data=result,
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An error occurred during token verification",
            },
        )
