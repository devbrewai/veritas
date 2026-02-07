"""Tests for application settings normalization."""

from src.config import Settings


def test_database_url_normalizes_postgres_scheme() -> None:
    settings = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/veritas")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/veritas"


def test_database_url_normalizes_postgresql_scheme() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/veritas")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/veritas"


def test_database_url_normalizes_other_postgresql_drivers() -> None:
    settings = Settings(DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/veritas")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/veritas"


def test_database_url_keeps_asyncpg_scheme() -> None:
    settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/veritas")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/veritas"


def test_database_url_keeps_sqlite_scheme() -> None:
    settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
    assert settings.DATABASE_URL == "sqlite+aiosqlite:///:memory:"
