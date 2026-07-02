"""Exception Handlers and Middleware"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.exceptions.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application exceptions"""
        logger.error(
            f"Application exception: {exc.error_code} - {exc.message}",
            extra={"status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            },
        )


def register_middleware(app: FastAPI) -> None:
    """Register middleware"""
    from fastapi.middleware.cors import CORSMiddleware
    from app.core.config import settings
    import json

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log incoming requests"""
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        logger.info(f"Incoming request: {method} {path} from {client_host}")

        response = await call_next(request)
        logger.info(f"Response: {method} {path} - Status: {response.status_code}")
        return response
