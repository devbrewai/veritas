"""GDPR retention: document expiry and cleanup.

Single place for retention logic (DRY): compute_expires_at is used when
creating documents; delete_document_files and run_retention_cleanup
are used by the cleanup script and DELETE /v1/users/me.
"""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.screening_result import ScreeningResult

logger = logging.getLogger(__name__)


def compute_expires_at(retention_days: int) -> datetime:
    """Compute expiry datetime as now + retention_days (UTC, naive).

    Used when creating documents so expiry lives in one place.
    """
    return datetime.utcnow() + timedelta(days=retention_days)


def delete_document_files(file_path: str, upload_dir: Path | str) -> None:
    """Delete a document's file and its parent directory if under upload_dir.

    Path traversal safety: only deletes if file_path resolves under upload_dir.
    Raises ValueError if file_path is outside upload_dir.
    """
    resolved = Path(file_path).resolve()
    upload_resolved = Path(upload_dir).resolve()
    try:
        resolved.relative_to(upload_resolved)
    except ValueError:
        raise ValueError(
            f"file_path {file_path!r} is not under upload_dir {upload_dir!r}"
        ) from None
    if resolved.is_file():
        resolved.unlink()
    parent = resolved.parent
    if parent != upload_resolved and parent.exists():
        try:
            shutil.rmtree(parent)
        except OSError as e:
            logger.warning("Could not remove document directory %s: %s", parent, e)


async def run_retention_cleanup(db: AsyncSession, upload_dir: Path | str) -> int:
    """Delete expired documents and their files. Returns number of documents deleted.

    Order: delete screening_results for expired document_ids, then for each
    document delete file/dir via delete_document_files, then delete document row.
    """
    now = datetime.utcnow()
    result = await db.execute(
        select(Document).where(
            Document.expires_at.isnot(None),
            Document.expires_at < now,
        )
    )
    expired = result.scalars().all()
    if not expired:
        return 0
    upload_resolved = Path(upload_dir).resolve()
    doc_ids = [d.id for d in expired]
    await db.execute(delete(ScreeningResult).where(ScreeningResult.document_id.in_(doc_ids)))
    await db.flush()
    for doc in expired:
        try:
            delete_document_files(doc.file_path, upload_resolved)
        except ValueError:
            logger.warning(
                "Skipping file deletion for doc %s (path outside upload_dir)",
                doc.id,
            )
        await db.delete(doc)
    await db.flush()
    return len(expired)
