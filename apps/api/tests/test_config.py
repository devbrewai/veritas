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


def test_database_url_strips_sslmode_from_postgres_url() -> None:
    settings = Settings(DATABASE_URL="postgres://user:pass@host:5432/db?sslmode=require")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@host:5432/db"
    assert settings.DATABASE_SSL_REQUIRED is True


def test_database_url_strips_sslmode_from_postgresql_url() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:pass@host:5432/db?sslmode=require")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@host:5432/db"
    assert settings.DATABASE_SSL_REQUIRED is True


def test_database_url_preserves_other_query_params_when_stripping_sslmode() -> None:
    settings = Settings(
        DATABASE_URL="postgres://user:pass@host:5432/db?sslmode=require&application_name=veritas"
    )
    assert "sslmode" not in settings.DATABASE_URL
    assert "application_name=veritas" in settings.DATABASE_URL
    assert settings.DATABASE_SSL_REQUIRED is True


def test_database_ssl_not_required_without_sslmode() -> None:
    settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert settings.DATABASE_SSL_REQUIRED is False


def test_database_ssl_required_can_be_set_explicitly() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
        DATABASE_SSL_REQUIRED=True,
    )
    assert settings.DATABASE_SSL_REQUIRED is True
