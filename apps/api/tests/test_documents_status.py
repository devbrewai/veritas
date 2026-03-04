"""Tests for GET /v1/documents/{document_id}/status."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models import Base
from src.models.document import Document

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
USER_A = "user-a"
USER_B = "user-b"


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


def _client_for_user(db_session: AsyncSession, user_id: str):
    async def override_get_db():
        yield db_session

    async def override_get_current_user_id() -> str:
        return user_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest_asyncio.fixture
async def doc_processing(db_session: AsyncSession) -> Document:
    """Document in processing state (not processed, no error)."""
    doc = Document(
        id=uuid.uuid4(),
        user_id=USER_A,
        document_type="passport",
        file_path="/tmp/p.jpg",
        file_size_bytes=100,
        processed=False,
        processing_error=None,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def doc_completed(db_session: AsyncSession) -> Document:
    """Document in completed state."""
    doc = Document(
        id=uuid.uuid4(),
        user_id=USER_A,
        document_type="passport",
        file_path="/tmp/c.jpg",
        file_size_bytes=100,
        processed=True,
        processing_error=None,
        extracted_data={"full_name": "Test"},
        ocr_confidence=0.9,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def doc_failed(db_session: AsyncSession) -> Document:
    """Document in failed state."""
    doc = Document(
        id=uuid.uuid4(),
        user_id=USER_A,
        document_type="passport",
        file_path="/tmp/f.jpg",
        file_size_bytes=100,
        processed=False,
        processing_error="Extraction failed",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_status_processing(db_session: AsyncSession, doc_processing: Document):
    async with _client_for_user(db_session, USER_A) as client:
        response = await client.get(f"/v1/documents/{doc_processing.id}/status")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(doc_processing.id)
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_status_completed(db_session: AsyncSession, doc_completed: Document):
    async with _client_for_user(db_session, USER_A) as client:
        response = await client.get(f"/v1/documents/{doc_completed.id}/status")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_status_failed(db_session: AsyncSession, doc_failed: Document):
    async with _client_for_user(db_session, USER_A) as client:
        response = await client.get(f"/v1/documents/{doc_failed.id}/status")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["message"] == "Extraction failed"


@pytest.mark.asyncio
async def test_status_404_wrong_user(db_session: AsyncSession, doc_processing: Document):
    """User B cannot see User A's document status."""
    async with _client_for_user(db_session, USER_B) as client:
        response = await client.get(f"/v1/documents/{doc_processing.id}/status")
    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_status_404_nonexistent(db_session: AsyncSession):
    async with _client_for_user(db_session, USER_A) as client:
        response = await client.get(f"/v1/documents/{uuid.uuid4()}/status")
    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_document_includes_status(db_session: AsyncSession, doc_completed: Document):
    """GET /v1/documents/{id} response includes computed status field."""
    async with _client_for_user(db_session, USER_A) as client:
        response = await client.get(f"/v1/documents/{doc_completed.id}")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "completed"
