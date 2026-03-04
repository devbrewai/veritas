"""Tests for GDPR retention, data export, and right-to-be-forgotten."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models import Base
from src.models.audit_log import AuditLog
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.services.retention import (
    delete_document_files,
    run_retention_cleanup,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
EXPORT_USER_ID = "export-test-user"


class TestDeleteDocumentFiles:
    """Unit tests for delete_document_files path-safety and deletion."""

    def test_raises_when_path_outside_upload_dir(self, tmp_path: Path) -> None:
        """Path outside upload_dir must raise ValueError."""
        upload = tmp_path / "uploads"
        upload.mkdir()
        outside = tmp_path / "other" / "file.jpg"
        outside.parent.mkdir()
        outside.write_text("x")
        with pytest.raises(ValueError, match="not under upload_dir"):
            delete_document_files(str(outside), upload)

    def test_deletes_file_and_parent_dir_when_under_upload_dir(
        self, tmp_path: Path
    ) -> None:
        """When path is under upload_dir, file and parent doc dir are removed."""
        upload = tmp_path / "uploads"
        upload.mkdir()
        doc_dir = upload / str(uuid.uuid4())
        doc_dir.mkdir()
        file_path = doc_dir / "original.jpg"
        file_path.write_text("content")
        delete_document_files(str(file_path), upload)
        assert not file_path.exists()
        assert not doc_dir.exists()
        assert upload.exists()


class TestRunRetentionCleanup:
    """Integration tests for run_retention_cleanup."""

    @pytest_asyncio.fixture
    async def db_engine(self):
        """Create test database engine."""
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest_asyncio.fixture
    async def db_session(self, db_engine) -> AsyncSession:
        """Create test database session."""
        async_session_maker = async_sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_document_and_screenings_and_files(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Expired document and its screenings and files are deleted."""
        upload = tmp_path / "uploads"
        upload.mkdir()
        doc_id = uuid.uuid4()
        doc_dir = upload / str(doc_id)
        doc_dir.mkdir()
        file_path = doc_dir / "original.jpg"
        file_path.write_text("x")
        expired_at = datetime.utcnow() - timedelta(days=1)
        doc = Document(
            id=doc_id,
            user_id="user-1",
            customer_id="c1",
            document_type="passport",
            file_path=str(file_path),
            file_size_bytes=1,
            processed=True,
            expires_at=expired_at,
        )
        db_session.add(doc)
        await db_session.flush()
        screening = ScreeningResult(
            id=uuid.uuid4(),
            user_id="user-1",
            document_id=doc_id,
            full_name="Test",
            sanctions_match=False,
            sanctions_decision="no_match",
        )
        db_session.add(screening)
        await db_session.commit()

        deleted = await run_retention_cleanup(db_session, upload)
        await db_session.commit()

        assert deleted == 1
        assert not file_path.exists()
        assert not doc_dir.exists()
        result = await db_session.execute(select(Document).where(Document.id == doc_id))
        assert result.scalar_one_or_none() is None
        result = await db_session.execute(
            select(ScreeningResult).where(ScreeningResult.document_id == doc_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cleanup_ignores_non_expired_documents(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Documents with expires_at in the future are not deleted."""
        upload = tmp_path / "uploads"
        upload.mkdir()
        doc_id = uuid.uuid4()
        doc_dir = upload / str(doc_id)
        doc_dir.mkdir()
        file_path = doc_dir / "original.jpg"
        file_path.write_text("x")
        future_expires = datetime.utcnow() + timedelta(days=30)
        doc = Document(
            id=doc_id,
            user_id="user-1",
            customer_id="c1",
            document_type="passport",
            file_path=str(file_path),
            file_size_bytes=1,
            processed=True,
            expires_at=future_expires,
        )
        db_session.add(doc)
        await db_session.commit()

        deleted = await run_retention_cleanup(db_session, upload)
        await db_session.commit()

        assert deleted == 0
        assert file_path.exists()
        result = await db_session.execute(select(Document).where(Document.id == doc_id))
        assert result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Data export (GET /v1/users/me/export)
# ---------------------------------------------------------------------------


class TestDataExport:
    """Tests for GET /v1/users/me/export."""

    @pytest_asyncio.fixture
    async def db_engine(self):
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest_asyncio.fixture
    async def db_session(self, db_engine) -> AsyncSession:
        async_session_maker = async_sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    @pytest.mark.asyncio
    async def test_export_returns_documents_screenings_audit_logs(
        self, db_session: AsyncSession
    ) -> None:
        """Export includes documents, screening_results, audit_logs and logs the request."""
        doc = Document(
            id=uuid.uuid4(),
            user_id=EXPORT_USER_ID,
            customer_id="c1",
            document_type="passport",
            file_path="/tmp/x.jpg",
            file_size_bytes=100,
            processed=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db_session.add(doc)
        await db_session.flush()
        screening = ScreeningResult(
            id=uuid.uuid4(),
            user_id=EXPORT_USER_ID,
            document_id=doc.id,
            full_name="Test User",
            sanctions_match=False,
            sanctions_decision="no_match",
        )
        db_session.add(screening)
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=EXPORT_USER_ID,
            action="document_uploaded",
            resource_type="document",
            resource_id=str(doc.id),
        )
        db_session.add(audit)
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user_id() -> str:
            return EXPORT_USER_ID

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/v1/users/me/export")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "screening_results" in data
        assert "audit_logs" in data
        assert "exported_at" in data
        assert len(data["documents"]) == 1
        assert len(data["screening_results"]) == 1
        assert len(data["audit_logs"]) >= 1  # pre-existing + data_export_requested

        # Export request must be audited
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.user_id == EXPORT_USER_ID,
                AuditLog.action == "data_export_requested",
            )
        )
        assert result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Right to be forgotten (DELETE /v1/users/me)
# ---------------------------------------------------------------------------


class TestDeleteMe:
    """Tests for DELETE /v1/users/me."""

    @pytest_asyncio.fixture
    async def db_engine(self):
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest_asyncio.fixture
    async def db_session(self, db_engine) -> AsyncSession:
        async_session_maker = async_sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    @pytest.mark.asyncio
    async def test_delete_me_removes_user_data_and_audits(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """DELETE /me removes documents, screenings, files; leaves audit entry; other user unchanged."""
        upload = tmp_path / "uploads"
        upload.mkdir()
        delete_user_id = "delete-me-user"
        other_user_id = "other-user"
        from src.routers import users as users_router
        original_upload_dir = users_router.settings.UPLOAD_DIR
        users_router.settings.UPLOAD_DIR = str(upload)
        try:
            doc_id = uuid.uuid4()
            doc_dir = upload / str(doc_id)
            doc_dir.mkdir()
            file_path = doc_dir / "original.jpg"
            file_path.write_text("x")
            doc = Document(
                id=doc_id,
                user_id=delete_user_id,
                customer_id="c1",
                document_type="passport",
                file_path=str(file_path),
                file_size_bytes=1,
                processed=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
            db_session.add(doc)
            await db_session.flush()
            screening = ScreeningResult(
                id=uuid.uuid4(),
                user_id=delete_user_id,
                document_id=doc_id,
                full_name="Test",
                sanctions_match=False,
                sanctions_decision="no_match",
            )
            db_session.add(screening)
            other_doc = Document(
                id=uuid.uuid4(),
                user_id=other_user_id,
                customer_id="c2",
                document_type="passport",
                file_path="/tmp/other.jpg",
                file_size_bytes=1,
                processed=True,
            )
            db_session.add(other_doc)
            await db_session.commit()

            async def override_get_db():
                yield db_session

            async def override_get_current_user_id() -> str:
                return delete_user_id

            app.dependency_overrides[get_db] = override_get_db
            app.dependency_overrides[get_current_user_id] = override_get_current_user_id

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.delete("/v1/users/me")

            app.dependency_overrides.clear()

            assert response.status_code == 204
            assert not file_path.exists()
            assert not doc_dir.exists()
            result = await db_session.execute(select(Document).where(Document.user_id == delete_user_id))
            assert result.scalar_one_or_none() is None
            result = await db_session.execute(
                select(ScreeningResult).where(ScreeningResult.user_id == delete_user_id)
            )
            assert result.scalar_one_or_none() is None
            result = await db_session.execute(select(Document).where(Document.user_id == other_user_id))
            assert result.scalar_one_or_none() is not None
            result = await db_session.execute(
                select(AuditLog).where(
                    AuditLog.user_id == delete_user_id,
                    AuditLog.action == "account_deleted",
                )
            )
            assert result.scalar_one_or_none() is not None
        finally:
            users_router.settings.UPLOAD_DIR = original_upload_dir
