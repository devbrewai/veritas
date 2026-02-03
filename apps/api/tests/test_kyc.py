"""Tests for KYC aggregation endpoints."""

import uuid
from datetime import datetime

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

# Test user IDs - Better Auth uses nanoid-style string IDs
USER_A_ID = "test-user-a"
USER_B_ID = "test-user-b"

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
async def user_a_document(db_session: AsyncSession) -> Document:
    """Create a document for User A."""
    document = Document(
        id=uuid.uuid4(),
        user_id=USER_A_ID,
        customer_id="CUST001",
        document_type="passport",
        file_path="/tmp/user_a_doc.jpg",
        file_size_bytes=1024,
        processed=True,
        extracted_data={
            "full_name": "Alice Anderson",
            "nationality": "US",
            "expiry_date": "2030-01-01",
        },
        ocr_confidence=0.95,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest_asyncio.fixture
async def user_a_second_document(db_session: AsyncSession) -> Document:
    """Create a second document for User A (same customer)."""
    document = Document(
        id=uuid.uuid4(),
        user_id=USER_A_ID,
        customer_id="CUST001",
        document_type="utility_bill",
        file_path="/tmp/user_a_bill.pdf",
        file_size_bytes=2048,
        processed=True,
        extracted_data={
            "full_name": "Alice Anderson",
            "service_address": "123 Main St",
        },
        ocr_confidence=0.88,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest_asyncio.fixture
async def user_b_document(db_session: AsyncSession) -> Document:
    """Create a document for User B."""
    document = Document(
        id=uuid.uuid4(),
        user_id=USER_B_ID,
        customer_id="CUST001",  # Same customer_id but different user
        document_type="passport",
        file_path="/tmp/user_b_doc.jpg",
        file_size_bytes=1024,
        processed=True,
        extracted_data={
            "full_name": "Bob Builder",
            "nationality": "GB",
            "expiry_date": "2029-06-15",
        },
        ocr_confidence=0.92,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest_asyncio.fixture
async def user_a_screening(
    db_session: AsyncSession, user_a_document: Document
) -> ScreeningResult:
    """Create a screening result for User A's document."""
    screening = ScreeningResult(
        id=uuid.uuid4(),
        user_id=USER_A_ID,
        document_id=user_a_document.id,
        customer_id="CUST001",
        full_name="Alice Anderson",
        sanctions_match=False,
        sanctions_decision="no_match",
        sanctions_score=0.1,
        adverse_media_count=2,
        adverse_media_summary={
            "average_sentiment": -0.3,
            "sentiment_category": "Negative",
        },
        risk_score=0.25,
        risk_tier="Low",
        recommendation="Approve",
        risk_reasons={
            "top_risk_factors": ["Minor adverse media mentions"],
        },
    )
    db_session.add(screening)
    await db_session.commit()
    await db_session.refresh(screening)
    return screening


@pytest_asyncio.fixture
async def user_b_screening(
    db_session: AsyncSession, user_b_document: Document
) -> ScreeningResult:
    """Create a screening result for User B's document."""
    screening = ScreeningResult(
        id=uuid.uuid4(),
        user_id=USER_B_ID,
        document_id=user_b_document.id,
        customer_id="CUST001",
        full_name="Bob Builder",
        sanctions_match=True,
        sanctions_decision="match",
        sanctions_score=0.95,
        risk_score=0.85,
        risk_tier="High",
        recommendation="Reject",
        risk_reasons={
            "top_risk_factors": ["Sanctions list match", "High-risk country"],
        },
    )
    db_session.add(screening)
    await db_session.commit()
    await db_session.refresh(screening)
    return screening


def create_client_for_user(db_session: AsyncSession, user_id: str):
    """Create a test client authenticated as a specific user."""

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


class TestKYCGetEndpoint:
    """Tests for GET /v1/kyc/{customer_id}."""

    @pytest.mark.asyncio
    async def test_get_kyc_no_documents(self, db_session: AsyncSession):
        """Returns empty result for customer with no documents."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/kyc/NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "NONEXISTENT"
        assert data["documents"] == []
        assert data["sanctions_screening"] is None
        assert data["adverse_media"] is None
        assert data["risk_assessment"] is None
        assert data["overall_status"] == "pending"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_kyc_with_document(
        self, db_session: AsyncSession, user_a_document: Document
    ):
        """Returns document summary correctly."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/kyc/CUST001")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "CUST001"
        assert len(data["documents"]) == 1
        assert data["documents"][0]["document_type"] == "passport"
        assert data["documents"][0]["processed"] is True
        assert data["documents"][0]["ocr_confidence"] == 0.95

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_kyc_with_multiple_documents(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_a_second_document: Document,
    ):
        """Returns multiple documents for same customer."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/kyc/CUST001")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2

        doc_types = {d["document_type"] for d in data["documents"]}
        assert doc_types == {"passport", "utility_bill"}

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_kyc_with_screening(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_a_screening: ScreeningResult,
    ):
        """Returns screening results correctly."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/kyc/CUST001")

        assert response.status_code == 200
        data = response.json()

        # Check sanctions screening
        assert data["sanctions_screening"] is not None
        assert data["sanctions_screening"]["decision"] == "no_match"
        assert data["sanctions_screening"]["top_match_score"] == 0.1

        # Check adverse media
        assert data["adverse_media"] is not None
        assert data["adverse_media"]["article_count"] == 2
        assert data["adverse_media"]["sentiment_category"] == "Negative"

        # Check risk assessment
        assert data["risk_assessment"] is not None
        assert data["risk_assessment"]["risk_score"] == 0.25
        assert data["risk_assessment"]["risk_tier"] == "Low"
        assert data["risk_assessment"]["recommendation"] == "Approve"

        # Check overall status
        assert data["overall_status"] == "approved"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_kyc_customer_isolation(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_a_screening: ScreeningResult,
        user_b_document: Document,
        user_b_screening: ScreeningResult,
    ):
        """User A cannot see User B's KYC data (same customer_id)."""
        # User A requests KYC for CUST001
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get("/v1/kyc/CUST001")

        assert response.status_code == 200
        data = response.json()

        # User A should see their own data (Alice)
        assert len(data["documents"]) == 1
        assert data["documents"][0]["extracted_data"]["full_name"] == "Alice Anderson"
        assert data["risk_assessment"]["recommendation"] == "Approve"

        app.dependency_overrides.clear()

        # User B requests KYC for same CUST001
        async with create_client_for_user(db_session, USER_B_ID) as client:
            response = await client.get("/v1/kyc/CUST001")

        assert response.status_code == 200
        data = response.json()

        # User B should see their own data (Bob)
        assert len(data["documents"]) == 1
        assert data["documents"][0]["extracted_data"]["full_name"] == "Bob Builder"
        assert data["risk_assessment"]["recommendation"] == "Reject"

        app.dependency_overrides.clear()


class TestKYCBatchEndpoint:
    """Tests for POST /v1/kyc/batch."""

    @pytest.mark.asyncio
    async def test_batch_kyc_success(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_a_screening: ScreeningResult,
    ):
        """Process multiple customers successfully."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.post(
                "/v1/kyc/batch",
                json={"customer_ids": ["CUST001", "CUST002", "CUST003"]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 3
        assert len(data["results"]) == 3

        # Check that CUST001 has data
        cust001 = next(r for r in data["results"] if r["customer_id"] == "CUST001")
        assert len(cust001["documents"]) == 1
        assert cust001["overall_status"] == "approved"

        # Check that CUST002 and CUST003 are pending (no data)
        cust002 = next(r for r in data["results"] if r["customer_id"] == "CUST002")
        assert cust002["overall_status"] == "pending"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_batch_kyc_max_limit(self, db_session: AsyncSession):
        """Reject requests with > 10 customers."""
        customer_ids = [f"CUST{i:03d}" for i in range(11)]

        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.post(
                "/v1/kyc/batch",
                json={"customer_ids": customer_ids},
            )

        assert response.status_code == 422  # Validation error from Pydantic

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_batch_kyc_counts_statuses(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_a_screening: ScreeningResult,
    ):
        """Batch response includes correct status counts."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.post(
                "/v1/kyc/batch",
                json={"customer_ids": ["CUST001", "NONEXISTENT"]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_approved"] == 1  # CUST001
        assert data["total_pending"] == 1   # NONEXISTENT

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_batch_kyc_empty_list_rejected(self, db_session: AsyncSession):
        """Empty customer list is rejected."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.post(
                "/v1/kyc/batch",
                json={"customer_ids": []},
            )

        assert response.status_code == 422  # Validation error

        app.dependency_overrides.clear()
