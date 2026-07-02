"""System Health and Info Routes"""
from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.connection import get_db, test_db_connection
from app.core.config import settings
from app.schemas.citizen import HealthCheckResponse, SuccessResponse
from app import __version__
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=SuccessResponse,
    status_code=200,
    summary="Health check",
    description="Check API and database health status",
)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db_connected = test_db_connection()
        
        health_data = HealthCheckResponse(
            status="healthy" if db_connected else "degraded",
            version=__version__,
            timestamp=datetime.utcnow(),
            database="connected" if db_connected else "disconnected",
            environment=settings.ENVIRONMENT,
        )

        return SuccessResponse(
            success=True,
            message="API is healthy",
            data=health_data.model_dump(),
        )
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return SuccessResponse(
            success=True,
            message="API is running but with issues",
            data={
                "status": "degraded",
                "version": __version__,
                "timestamp": datetime.utcnow(),
                "database": "disconnected",
                "environment": settings.ENVIRONMENT,
            },
        )


@router.get(
    "/version",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get API version",
    description="Get the version of the API",
)
async def get_version():
    """Get API version"""
    return SuccessResponse(
        success=True,
        message="Version retrieved successfully",
        data={
            "version": __version__,
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        },
    )


@router.get(
    "/info",
    response_model=SuccessResponse,
    status_code=200,
    summary="Get API info",
    description="Get API information and configuration",
)
async def get_info():
    """Get API information"""
    return SuccessResponse(
        success=True,
        message="API information retrieved successfully",
        data={
            "app_name": settings.APP_NAME,
            "version": __version__,
            "description": settings.APP_DESCRIPTION,
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "docs_url": settings.DOCS_URL,
            "openapi_url": settings.OPENAPI_URL,
        },
    )
