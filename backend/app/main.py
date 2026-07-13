"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.database.connection import init_db, close_db
from app.api.auth_routes import router as auth_router
from app.api.health_routes import router as health_router
from app.api.citizen_routes import router as citizen_router
from app.api.digilocker_routes import router as digilocker_router
from app.middleware.handlers import register_exception_handlers, register_middleware
from app import __version__

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    # Startup
    logger.info("=" * 80)
    logger.info(f"Starting {settings.APP_NAME} v{__version__}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info("=" * 80)

    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info(f"Shutting down {settings.APP_NAME}")
    logger.info("=" * 80)
    close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=__version__,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan,
)

# Register middleware
register_middleware(app)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(citizen_router)
app.include_router(digilocker_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return JSONResponse(
        {
            "message": "Welcome to AI-Powered Government Scheme Fulfillment Engine API",
            "version": __version__,
            "docs": settings.DOCS_URL,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.SERVER_RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
