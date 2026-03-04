"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint returns healthy status."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "veritas-api"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns API info."""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Veritas KYC/AML API"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_error_response_shape_and_request_id(client: AsyncClient):
    """4xx responses use standardized error shape and include X-Request-Id."""
    response = await client.get("/v1/documents/00000000-0000-0000-0000-000000000000/status")
    assert response.status_code in (401, 404)
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data
    assert "X-Request-Id" in response.headers
    assert response.headers["X-Request-Id"] == data["request_id"]
