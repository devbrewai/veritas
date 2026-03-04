"""Tests for API key create, list, revoke."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_USER_ID = "test-api-key-user"


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


@pytest.mark.asyncio
async def test_create_api_key_returns_key_once(db_session: AsyncSession):
    """POST /v1/api-keys returns 201 with api_key, prefix, name, id."""
    async def override_get_db():
        yield db_session
    async def override_get_current_user_id():
        return TEST_USER_ID

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/api-keys",
            json={"name": "Production"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["api_key"].startswith("vrt_sk_")
    assert len(data["api_key"]) > 20
    assert data["prefix"].startswith("vrt_sk_")
    assert data["name"] == "Production"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_api_keys(db_session: AsyncSession):
    """GET /v1/api-keys returns list without full key."""
    async def override_get_db():
        yield db_session
    async def override_get_current_user_id():
        return TEST_USER_ID

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post("/v1/api-keys", json={"name": "Key1"})
        response = await client.get("/v1/api-keys")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "api_keys" in data
    assert len(data["api_keys"]) >= 1
    item = data["api_keys"][0]
    assert "id" in item
    assert "name" in item
    assert "prefix" in item
    assert "api_key" not in item


@pytest.mark.asyncio
async def test_revoke_api_key(db_session: AsyncSession):
    """DELETE /v1/api-keys/{id} returns 204 and key no longer in list."""
    async def override_get_db():
        yield db_session
    async def override_get_current_user_id():
        return TEST_USER_ID

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        create_resp = await client.post("/v1/api-keys", json={"name": "ToRevoke"})
        key_id = create_resp.json()["id"]
        revoke_resp = await client.delete(f"/v1/api-keys/{key_id}")
        list_resp = await client.get("/v1/api-keys")
    app.dependency_overrides.clear()

    assert revoke_resp.status_code == 204
    keys = list_resp.json()["api_keys"]
    ids = [k["id"] for k in keys]
    assert key_id not in ids
