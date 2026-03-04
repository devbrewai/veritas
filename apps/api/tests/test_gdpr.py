"""Tests for GDPR retention: file deletion and cleanup."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import Base
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.services.retention import (
    delete_document_files,
    run_retention_cleanup,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
