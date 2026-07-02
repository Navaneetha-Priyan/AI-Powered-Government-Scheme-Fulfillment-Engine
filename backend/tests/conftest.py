"""Test Configuration and Fixtures"""
import pytest
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager
from typing import Generator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.connection import Base, get_db
from app.core.config import settings
from app.api.auth_routes import router as auth_router
from app.api.health_routes import router as health_router
from app.middleware.handlers import register_exception_handlers, register_middleware
from app import __version__

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the entire test session"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function", autouse=True)
def clean_tables():
    """Delete all rows from all tables before and after each test"""
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(test_db: Session) -> TestClient:

    @asynccontextmanager
    async def test_lifespan(app):
        yield

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=__version__,
        lifespan=test_lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(health_router)

    app.dependency_overrides[get_db] = lambda: test_db

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client: TestClient) -> dict:
    """Register a user and return auth headers"""
    register_data = {
        "email": "test@example.com",
        "phone": "9876543210",
        "full_name": "Test User",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "district": "Chennai",
        "state": "Tamil Nadu",
    }
    response = client.post("/auth/register", json=register_data)
    if response.status_code != 201:
        print(f"Registration failed: {response.json()}")
    assert response.status_code == 201

    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
