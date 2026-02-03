"""
API tests for sanctions screening endpoints.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models import Base
from src.services.sanctions import sanctions_screening_service

# Fixed test user ID for consistent testing
# Better Auth uses nanoid-style string IDs
TEST_USER_ID = "test-user-001"

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module", autouse=True)
def initialize_service():
    """Initialize the sanctions service before tests."""
    sanctions_screening_service.initialize()
    yield


@pytest.fixture
async def client():
    """Create async test client with auth dependency override."""

    async def override_get_current_user_id() -> str:
        return TEST_USER_ID

    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncSession:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def db_client(db_session: AsyncSession):
    """Create async test client with database and auth dependency overrides."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user_id() -> str:
        return TEST_USER_ID

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


class TestSanctionsHealthEndpoint:
    """Tests for /v1/screening/sanctions/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_status(self, client):
        """Health endpoint should return service status."""
        response = await client.get("/v1/screening/sanctions/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "loaded" in data
        assert "record_count" in data
        assert data["status"] == "healthy"
        assert data["loaded"] is True

    @pytest.mark.asyncio
    async def test_health_shows_record_count(self, client):
        """Health endpoint should show loaded record count."""
        response = await client.get("/v1/screening/sanctions/health")

        data = response.json()
        assert data["record_count"] == 39350


class TestSanctionsScreenEndpoint:
    """Tests for POST /v1/screening/sanctions endpoint."""

    @pytest.mark.asyncio
    async def test_screen_single_name(self, client):
        """Should screen a single name."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "John Smith"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"]["success"] is True
        assert data["result"]["data"]["query_name"] == "John Smith"

    @pytest.mark.asyncio
    async def test_screen_with_nationality(self, client):
        """Should accept nationality filter."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Test Person", "nationality": "US"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["data"]["applied_filters"]["country"] == "US"

    @pytest.mark.asyncio
    async def test_screen_with_aliases(self, client):
        """Should accept aliases."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={
                "name": "John Doe",
                "aliases": ["J. Doe", "Johnny Doe"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_screen_with_top_k(self, client):
        """Should respect top_k parameter."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Test", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]["data"]["all_matches"]) <= 5

    @pytest.mark.asyncio
    async def test_screen_returns_processing_time(self, client):
        """Should return processing time."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Jane Doe"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["processing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_screen_validates_empty_name(self, client):
        """Should reject empty name."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": ""},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_screen_validates_top_k_range(self, client):
        """Should reject invalid top_k values."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Test", "top_k": 15},
        )

        assert response.status_code == 422  # Validation error


class TestSanctionsBatchEndpoint:
    """Tests for POST /v1/screening/sanctions/batch endpoint."""

    @pytest.mark.asyncio
    async def test_batch_screen_multiple_names(self, client):
        """Should screen multiple names in batch."""
        response = await client.post(
            "/v1/screening/sanctions/batch",
            json={
                "queries": [
                    {"name": "John Doe"},
                    {"name": "Jane Smith"},
                    {"name": "Test Person"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_screened"] == 3
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_returns_totals(self, client):
        """Should return aggregate totals."""
        response = await client.post(
            "/v1/screening/sanctions/batch",
            json={
                "queries": [
                    {"name": "John Doe"},
                    {"name": "Jane Smith"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_screened" in data
        assert "total_matches" in data
        assert "total_reviews" in data
        assert "total_processing_time_ms" in data

    @pytest.mark.asyncio
    async def test_batch_respects_max_limit(self, client):
        """Should reject batches exceeding 100 names."""
        queries = [{"name": f"Person {i}"} for i in range(101)]
        response = await client.post(
            "/v1/screening/sanctions/batch",
            json={"queries": queries},
        )

        assert response.status_code == 422  # Validation error


class TestDocumentScreenEndpoint:
    """Tests for POST /v1/screening/document/{document_id} endpoint."""

    @pytest.mark.asyncio
    async def test_screen_nonexistent_document(self, db_client):
        """Should return 404 for nonexistent document."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await db_client.post(f"/v1/screening/document/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_screen_invalid_uuid(self, db_client):
        """Should reject invalid UUID."""
        response = await db_client.post("/v1/screening/document/invalid-uuid")

        assert response.status_code == 422  # Validation error


class TestResponseFormat:
    """Tests for response format and structure."""

    @pytest.mark.asyncio
    async def test_response_includes_timestamp(self, client):
        """Response should include screened_at timestamp."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Test"},
        )

        data = response.json()
        assert "screened_at" in data

    @pytest.mark.asyncio
    async def test_response_includes_api_version(self, client):
        """Response should include API version."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Test"},
        )

        data = response.json()
        assert data["api_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_screening_result_structure(self, client):
        """Screening result should have expected structure."""
        response = await client.post(
            "/v1/screening/sanctions",
            json={"name": "Test Person"},
        )

        data = response.json()
        result = data["result"]

        assert "success" in result
        assert "data" in result
        assert "confidence" in result
        assert "processing_time_ms" in result
        assert "errors" in result
        assert "warnings" in result

        if result["data"]:
            assert "query_name" in result["data"]
            assert "query_normalized" in result["data"]
            assert "decision" in result["data"]
            assert "all_matches" in result["data"]
