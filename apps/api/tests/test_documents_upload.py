"""Tests for document upload (202 Accepted, background processing)."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.middleware.rate_limit import check_rate_limit
from src.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_USER_ID = "test-upload-user"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    async_session_maker = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


def _client_with_overrides(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    async def override_get_current_user_id() -> str:
        return TEST_USER_ID

    async def override_check_rate_limit() -> str:
        return TEST_USER_ID

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[check_rate_limit] = override_check_rate_limit

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_upload_returns_202_and_processing_status(db_session: AsyncSession):
    """POST /v1/documents/upload returns 202 with status processing and document_id."""
    async with _client_with_overrides(db_session) as client:
        response = await client.post(
            "/v1/documents/upload",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
            data={"document_type": "passport"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "processing"
    assert "document_id" in data
    assert data["message"]
    assert "poll" in data["message"].lower() or "status" in data["message"].lower()
    assert "status_url" in data
    assert data["status_url"].endswith("/status")
    assert str(data["document_id"]) in data["status_url"]
    assert "estimated_completion_seconds" in data
    assert data["estimated_completion_seconds"] in (10, 15)


@pytest.mark.asyncio
async def test_upload_rejects_missing_filename(db_session: AsyncSession):
    async with _client_with_overrides(db_session) as client:
        response = await client.post(
            "/v1/documents/upload",
            files={"file": ("", b"content", "application/octet-stream")},
            data={"document_type": "passport"},
        )
    app.dependency_overrides.clear()
    # FastAPI/Starlette may return 422 for invalid file upload
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_extension(db_session: AsyncSession):
    async with _client_with_overrides(db_session) as client:
        response = await client.post(
            "/v1/documents/upload",
            files={"file": ("file.exe", b"content", "application/octet-stream")},
            data={"document_type": "passport"},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 400
    data = response.json()
    assert "error" in data and "message" in data["error"]
    assert "not allowed" in data["error"]["message"].lower()
    assert "request_id" in data
