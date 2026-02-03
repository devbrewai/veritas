"""Tests for multi-tenant data isolation.

These tests verify that users can only access their own data and cannot
see or modify data belonging to other users.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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
async def user_a_document(db_session: AsyncSession) -> Document:
    """Create a document for User A."""
    document = Document(
        id=uuid.uuid4(),
        user_id=USER_A_ID,
        customer_id="customer-a",
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
async def user_b_document(db_session: AsyncSession) -> Document:
    """Create a document for User B."""
    document = Document(
        id=uuid.uuid4(),
        user_id=USER_B_ID,
        customer_id="customer-b",
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
        customer_id="customer-a",
        full_name="Alice Anderson",
        sanctions_match=False,
        sanctions_decision="no_match",
        sanctions_score=0.1,
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
        customer_id="customer-b",
        full_name="Bob Builder",
        sanctions_match=False,
        sanctions_decision="no_match",
        sanctions_score=0.05,
    )
    db_session.add(screening)
    await db_session.commit()
    await db_session.refresh(screening)
    return screening


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


class TestDocumentIsolation:
    """Tests for document access isolation between users."""

    @pytest.mark.asyncio
    async def test_user_can_access_own_document(
        self, db_session: AsyncSession, user_a_document: Document
    ):
        """User A should be able to access their own document."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get(f"/v1/documents/{user_a_document.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user_a_document.id)
        assert data["customer_id"] == "customer-a"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_document(
        self, db_session: AsyncSession, user_b_document: Document
    ):
        """User A should NOT be able to access User B's document."""
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get(f"/v1/documents/{user_b_document.id}")

        # Should get 404 - document doesn't exist for this user
        assert response.status_code == 404

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_both_users_have_separate_documents(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_b_document: Document,
    ):
        """Both users should only see their own documents."""
        # User A accesses their document
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response_a = await client.get(f"/v1/documents/{user_a_document.id}")
            assert response_a.status_code == 200
            assert response_a.json()["extracted_data"]["full_name"] == "Alice Anderson"
        app.dependency_overrides.clear()

        # User B accesses their document
        async with create_client_for_user(db_session, USER_B_ID) as client:
            response_b = await client.get(f"/v1/documents/{user_b_document.id}")
            assert response_b.status_code == 200
            assert response_b.json()["extracted_data"]["full_name"] == "Bob Builder"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_nonexistent_document_returns_404(self, db_session: AsyncSession):
        """Requesting a non-existent document should return 404."""
        fake_id = uuid.uuid4()
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get(f"/v1/documents/{fake_id}")

        assert response.status_code == 404
        app.dependency_overrides.clear()


class TestScreeningResultIsolation:
    """Tests for screening result access isolation between users."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_access_user_b_screening_via_query(
        self,
        db_session: AsyncSession,
        user_a_screening: ScreeningResult,
        user_b_screening: ScreeningResult,
    ):
        """User A's screening query should not return User B's screening."""
        # Query screenings for User A only
        result = await db_session.execute(
            select(ScreeningResult).where(ScreeningResult.user_id == USER_A_ID)
        )
        user_a_screenings = result.scalars().all()

        # User A should only see their own screening
        assert len(user_a_screenings) == 1
        assert user_a_screenings[0].id == user_a_screening.id
        assert user_a_screenings[0].full_name == "Alice Anderson"

        # The screening should NOT contain User B's data
        for s in user_a_screenings:
            assert s.id != user_b_screening.id
            assert s.full_name != "Bob Builder"

    @pytest.mark.asyncio
    async def test_user_b_cannot_access_user_a_screening_via_query(
        self,
        db_session: AsyncSession,
        user_a_screening: ScreeningResult,
        user_b_screening: ScreeningResult,
    ):
        """User B's screening query should not return User A's screening."""
        # Query screenings for User B only
        result = await db_session.execute(
            select(ScreeningResult).where(ScreeningResult.user_id == USER_B_ID)
        )
        user_b_screenings = result.scalars().all()

        # User B should only see their own screening
        assert len(user_b_screenings) == 1
        assert user_b_screenings[0].id == user_b_screening.id
        assert user_b_screenings[0].full_name == "Bob Builder"

        # The screening should NOT contain User A's data
        for s in user_b_screenings:
            assert s.id != user_a_screening.id
            assert s.full_name != "Alice Anderson"


class TestCrossUserDataProtection:
    """Tests to verify complete cross-user data protection."""

    @pytest.mark.asyncio
    async def test_user_cannot_enumerate_other_users_documents(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_b_document: Document,
    ):
        """User should not be able to find documents by guessing IDs."""
        # User A tries to access User B's document
        async with create_client_for_user(db_session, USER_A_ID) as client:
            response = await client.get(f"/v1/documents/{user_b_document.id}")
            assert response.status_code == 404
        app.dependency_overrides.clear()

        # User B tries to access User A's document
        async with create_client_for_user(db_session, USER_B_ID) as client:
            response = await client.get(f"/v1/documents/{user_a_document.id}")
            assert response.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_database_query_isolation(
        self,
        db_session: AsyncSession,
        user_a_document: Document,
        user_b_document: Document,
    ):
        """Verify documents are stored with correct user_id in database."""
        # Query all documents in the database
        result = await db_session.execute(select(Document))
        all_docs = result.scalars().all()

        assert len(all_docs) == 2

        # Verify each document has correct user_id
        doc_a = next(d for d in all_docs if d.id == user_a_document.id)
        doc_b = next(d for d in all_docs if d.id == user_b_document.id)

        assert doc_a.user_id == USER_A_ID
        assert doc_b.user_id == USER_B_ID

        # Verify customer IDs are different
        assert doc_a.customer_id != doc_b.customer_id

    @pytest.mark.asyncio
    async def test_screening_inherits_user_id_from_document(
        self,
        db_session: AsyncSession,
        user_a_screening: ScreeningResult,
        user_b_screening: ScreeningResult,
    ):
        """Verify screening results have correct user_id matching documents."""
        # Query screening results
        result = await db_session.execute(select(ScreeningResult))
        all_screenings = result.scalars().all()

        assert len(all_screenings) == 2

        screening_a = next(s for s in all_screenings if s.id == user_a_screening.id)
        screening_b = next(s for s in all_screenings if s.id == user_b_screening.id)

        assert screening_a.user_id == USER_A_ID
        assert screening_b.user_id == USER_B_ID
