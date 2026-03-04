"""Integration tests for webhook registration and list."""

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_authenticated_user
from src.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_USER_ID = "test-webhook-user"


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


async def _override_get_authenticated_user(request: Request) -> str:
    request.state.user_id = TEST_USER_ID
    request.state.rate_limit = 60
    request.state.auth_key_id = "session"
    return TEST_USER_ID


@pytest.mark.asyncio
async def test_registration_returns_201(db_session: AsyncSession):
    """POST /v1/webhooks returns 201 with id, url, events, secret, created_at."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_authenticated_user] = _override_get_authenticated_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["document.processed"],
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["url"] == "https://example.com/hook"
    assert data["events"] == ["document.processed"]
    assert "secret" in data
    assert len(data["secret"]) > 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_returns_webhook_without_secret(db_session: AsyncSession):
    """GET /v1/webhooks returns list of webhooks; list items do not include secret."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_authenticated_user] = _override_get_authenticated_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post(
            "/v1/webhooks",
            json={
                "url": "https://example.com/callback",
                "events": ["document.processed", "kyc.complete"],
            },
        )
        response = await client.get("/v1/webhooks")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "webhooks" in data
    assert len(data["webhooks"]) >= 1
    for item in data["webhooks"]:
        assert "id" in item
        assert "url" in item
        assert "events" in item
        assert "active" in item
        assert "created_at" in item
        assert "secret" not in item


@pytest.mark.asyncio
async def test_delete_webhook_returns_204_and_removes_from_list(db_session: AsyncSession):
    """DELETE /v1/webhooks/{id} returns 204; GET list no longer includes that webhook."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_authenticated_user] = _override_get_authenticated_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        create_resp = await client.post(
            "/v1/webhooks",
            json={"url": "https://example.com/delete-me", "events": ["document.processed"]},
        )
        webhook_id = create_resp.json()["id"]
        delete_resp = await client.delete(f"/v1/webhooks/{webhook_id}")
        list_resp = await client.get("/v1/webhooks")
    app.dependency_overrides.clear()

    assert delete_resp.status_code == 204
    webhooks = list_resp.json()["webhooks"]
    ids = [w["id"] for w in webhooks]
    assert webhook_id not in ids
