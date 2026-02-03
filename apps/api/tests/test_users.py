"""Tests for user stats endpoint."""

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models import Base
from src.models.document import Document
from src.models.screening_result import ScreeningResult

# Test user IDs
USER_A_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_B_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
async def user_a_documents(db_session: AsyncSession) -> list[Document]:
    """Create multiple documents for User A."""
    docs = [
        Document(
            id=uuid.uuid4(),
            user_id=USER_A_ID,
            customer_id="CUST001",
            document_type="passport",
            file_path="/tmp/passport1.jpg",
            file_size_bytes=1024,
            processed=True,
            ocr_confidence=0.95,
        ),
        Document(
            id=uuid.uuid4(),
            user_id=USER_A_ID,
            customer_id="CUST002",
            document_type="passport",
            file_path="/tmp/passport2.jpg",
            file_size_bytes=2048,
            processed=True,
            ocr_confidence=0.88,
        ),
        Document(
            id=uuid.uuid4(),
            user_id=USER_A_ID,
            customer_id="CUST001",
            document_type="utility_bill",
            file_path="/tmp/bill1.pdf",
            file_size_bytes=3072,
            processed=True,
            ocr_confidence=0.82,
        ),
    ]
    for doc in docs:
        db_session.add(doc)
    await db_session.commit()
    return docs


@pytest_asyncio.fixture
async def user_a_screenings(
    db_session: AsyncSession, user_a_documents: list[Document]
) -> list[ScreeningResult]:
    """Create screening results for User A."""
    screenings = [
        ScreeningResult(
            id=uuid.uuid4(),
            user_id=USER_A_ID,
            document_id=user_a_documents[0].id,
            customer_id="CUST001",
            full_name="Alice Anderson",
            sanctions_match=False,
            sanctions_decision="no_match",
            sanctions_score=0.1,
            risk_score=0.25,
            risk_tier="Low",
            recommendation="Approve",
        ),
        ScreeningResult(
            id=uuid.uuid4(),
            user_id=USER_A_ID,
            document_id=user_a_documents[1].id,
            customer_id="CUST002",
            full_name="Bob Builder",
            sanctions_match=False,
            sanctions_decision="review",
            sanctions_score=0.45,
            risk_score=0.55,
            risk_tier="Medium",
            recommendation="Review",
        ),
    ]
    for screening in screenings:
        db_session.add(screening)
    await db_session.commit()
    return screenings


@pytest_asyncio.fixture
async def user_b_document(db_session: AsyncSession) -> Document:
    """Create a document for User B."""
    doc = Document(
        id=uuid.uuid4(),
        user_id=USER_B_ID,
        customer_id="CUST003",
        document_type="passport",
        file_path="/tmp/b_passport.jpg",
        file_size_bytes=1024,
        processed=True,
        ocr_confidence=0.90,
    )
    db_session.add(doc)
    await db_session.commit()
    return doc


def create_client_for_user(db_session: AsyncSession, user_id: uuid.UUID):
    """Create a test client authenticated as a specific user."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user_id() -> uuid.UUID:
        return user_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


class TestUserStats:
    """Tests for GET /v1/users/me/stats."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, db_session: AsyncSession):
        """New user has zero stats."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/users/me/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 0
        assert data["documents_by_type"] == {}
        assert data["documents_this_month"] == 0
        assert data["total_screenings"] == 0
        assert data["screenings_by_decision"] == {}
        assert data["screenings_this_month"] == 0
        assert data["average_risk_score"] is None
        assert data["risk_tier_distribution"] == {}

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stats_with_documents(
        self, db_session: AsyncSession, user_a_documents: list[Document]
    ):
        """Returns correct document counts."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/users/me/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 3
        assert data["documents_this_month"] == 3  # All created this month

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stats_by_type(
        self, db_session: AsyncSession, user_a_documents: list[Document]
    ):
        """Correctly groups by document type."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/users/me/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["documents_by_type"]["passport"] == 2
        assert data["documents_by_type"]["utility_bill"] == 1

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stats_with_screenings(
        self,
        db_session: AsyncSession,
        user_a_documents: list[Document],
        user_a_screenings: list[ScreeningResult],
    ):
        """Returns correct screening counts and averages."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/users/me/stats")

        assert response.status_code == 200
        data = response.json()

        # Screening counts
        assert data["total_screenings"] == 2
        assert data["screenings_by_decision"]["no_match"] == 1
        assert data["screenings_by_decision"]["review"] == 1

        # Average risk score: (0.25 + 0.55) / 2 = 0.4
        assert data["average_risk_score"] == pytest.approx(0.4, abs=0.01)

        # Risk tier distribution
        assert data["risk_tier_distribution"]["Low"] == 1
        assert data["risk_tier_distribution"]["Medium"] == 1

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stats_isolation(
        self,
        db_session: AsyncSession,
        user_a_documents: list[Document],
        user_a_screenings: list[ScreeningResult],
        user_b_document: Document,
    ):
        """User A cannot see User B's stats."""
        # Get User A's stats
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response_a = await client.get("/v1/users/me/stats")
        app.dependency_overrides.clear()

        # Get User B's stats
        async with create_client_for_user(db_session, USER_B_ID) as client:
            response_b = await client.get("/v1/users/me/stats")
        app.dependency_overrides.clear()

        # User A should have 3 documents, 2 screenings
        data_a = response_a.json()
        assert data_a["total_documents"] == 3
        assert data_a["total_screenings"] == 2

        # User B should have 1 document, 0 screenings
        data_b = response_b.json()
        assert data_b["total_documents"] == 1
        assert data_b["total_screenings"] == 0
