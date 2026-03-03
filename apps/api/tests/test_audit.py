"""Tests for the audit logging service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import Base
from src.models.audit_log import AuditLog
from src.services.audit import AuditAction, get_client_ip, log_audit_event

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncSession:
    session_maker = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session


# ---------------------------------------------------------------------------
# AuditAction enum
# ---------------------------------------------------------------------------

class TestAuditAction:
    def test_action_values_are_lowercase(self):
        for member in AuditAction:
            assert member.value == member.value.lower()

    def test_expected_actions_exist(self):
        expected = {
            "document_uploaded",
            "document_viewed",
            "sanctions_screened",
            "sanctions_batch_screened",
            "sanctions_document_screened",
            "adverse_media_scanned",
            "adverse_media_document_scanned",
            "risk_scored",
            "risk_screening_scored",
            "kyc_processed",
            "kyc_viewed",
            "kyc_batch_viewed",
        }
        assert {a.value for a in AuditAction} == expected


# ---------------------------------------------------------------------------
# get_client_ip
# ---------------------------------------------------------------------------

class TestGetClientIp:
    def test_returns_forwarded_for_first_ip(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 10.0.0.1"}
        request.client = MagicMock(host="127.0.0.1")
        assert get_client_ip(request) == "1.2.3.4"

    def test_falls_back_to_client_host(self):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.5")
        assert get_client_ip(request) == "192.168.1.5"

    def test_returns_none_when_no_client(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert get_client_ip(request) is None


# ---------------------------------------------------------------------------
# log_audit_event
# ---------------------------------------------------------------------------

class TestLogAuditEvent:
    @pytest.mark.asyncio
    async def test_creates_row_in_db(self, db_session: AsyncSession):
        await log_audit_event(
            db_session,
            user_id="user-123",
            action=AuditAction.DOCUMENT_UPLOADED,
            resource_type="document",
            resource_id=str(uuid.uuid4()),
            details={"status": "completed", "document_type": "passport"},
            ip_address="10.0.0.1",
        )
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        rows = result.scalars().all()

        assert len(rows) == 1
        row = rows[0]
        assert row.user_id == "user-123"
        assert row.action == "document_uploaded"
        assert row.resource_type == "document"
        assert row.details["status"] == "completed"
        assert row.ip_address == "10.0.0.1"
        assert row.created_at is not None

    @pytest.mark.asyncio
    async def test_stores_all_action_types(self, db_session: AsyncSession):
        for action in AuditAction:
            await log_audit_event(
                db_session,
                user_id="user-enum",
                action=action,
                resource_type="test",
            )
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        rows = result.scalars().all()
        assert len(rows) == len(AuditAction)

    @pytest.mark.asyncio
    async def test_does_not_raise_on_db_error(self):
        """Audit logging must never break the calling request."""
        bad_session = AsyncMock(spec=AsyncSession)
        bad_session.add = MagicMock()
        bad_session.flush = AsyncMock(side_effect=RuntimeError("db down"))

        await log_audit_event(
            bad_session,
            user_id="user-fail",
            action=AuditAction.SANCTIONS_SCREENED,
            resource_type="screening",
        )

    @pytest.mark.asyncio
    async def test_nullable_fields_default_to_none(self, db_session: AsyncSession):
        await log_audit_event(
            db_session,
            user_id="user-minimal",
            action=AuditAction.KYC_VIEWED,
            resource_type="kyc",
        )
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        row = result.scalar_one()
        assert row.resource_id is None
        assert row.details is None
        assert row.ip_address is None
