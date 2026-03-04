"""CLI entrypoint: delete expired documents and their files (GDPR retention).

Run from apps/api with:
  uv run python -m src.scripts.cleanup_expired_documents

Requires the documents.expires_at migration to be applied first:
  uv run alembic upgrade head

Schedule via cron (e.g. daily) to enforce document retention policy.
"""

import asyncio
import logging
import sys

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.services.retention import run_retention_cleanup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MIGRATION_HINT = (
    "The database may be missing the expires_at column. "
    "From apps/api run: uv run alembic upgrade head"
)


async def main() -> int:
    """Run retention cleanup and return exit code."""
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as db:
        try:
            deleted = await run_retention_cleanup(db, settings.UPLOAD_DIR)
            await db.commit()
            logger.info("Retention cleanup completed: %d expired document(s) deleted", deleted)
            return 0
        except ProgrammingError as e:
            if "expires_at" in str(e.orig) or "does not exist" in str(e).lower():
                logger.error("Retention cleanup failed: %s. %s", e.orig, MIGRATION_HINT)
            else:
                logger.exception("Retention cleanup failed")
            await db.rollback()
            return 1
        except Exception:
            logger.exception("Retention cleanup failed")
            await db.rollback()
            return 1
        finally:
            await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
