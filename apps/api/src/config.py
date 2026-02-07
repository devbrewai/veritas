from functools import lru_cache
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/veritas"
    DATABASE_SSL_REQUIRED: bool = False

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list[str] = ["jpg", "jpeg", "png", "pdf"]

    # OCR - Tesseract
    TESSERACT_CMD: str | None = None  # Use system default if None

    # OCR - Google Vision API (fallback for better accuracy)
    GOOGLE_CLOUD_API_KEY: str | None = None
    GOOGLE_VISION_ENABLED: bool = False

    # API
    API_V1_PREFIX: str = "/v1"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"  # Comma-separated for multiple origins

    # Sanctions Screening
    SANCTIONS_PICKLE_PATH: str = "./models/sanctions_screener.pkl"
    SANCTIONS_ENABLED: bool = True

    # Authentication (Better Auth JWT validation)
    BETTER_AUTH_URL: str = "http://localhost:3000"
    JWKS_CACHE_TTL: int = 3600  # Cache JWKS for 1 hour

    # Rate Limiting
    RATE_LIMIT_UPLOADS_PER_MINUTE: int = 10

    @model_validator(mode="before")
    @classmethod
    def detect_ssl_from_database_url(cls, data: Any) -> Any:
        """Detect sslmode in DATABASE_URL and set DATABASE_SSL_REQUIRED."""
        if isinstance(data, dict):
            db_url = data.get("DATABASE_URL") or data.get("database_url")
            if db_url and isinstance(db_url, str) and "sslmode" in db_url:
                if "DATABASE_SSL_REQUIRED" not in data and "database_ssl_required" not in data:
                    data["DATABASE_SSL_REQUIRED"] = True
        return data

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        """Normalize PostgreSQL URLs to asyncpg for SQLAlchemy async engine usage.

        Also strips the sslmode query parameter which is incompatible with asyncpg.
        """
        if not isinstance(value, str):
            raise ValueError("DATABASE_URL must be a string")

        database_url = value.strip()
        if database_url.startswith("postgres://"):
            database_url = f"postgresql+asyncpg://{database_url[len('postgres://'):]}"
        elif database_url.startswith("postgresql://"):
            database_url = f"postgresql+asyncpg://{database_url[len('postgresql://'):]}"
        else:
            scheme, separator, remainder = database_url.partition("://")
            if scheme.startswith("postgresql+") and scheme != "postgresql+asyncpg" and separator:
                database_url = f"postgresql+asyncpg://{remainder}"

        if "sslmode" in database_url:
            parsed = urlparse(database_url)
            query_params = parse_qs(parsed.query)
            query_params.pop("sslmode", None)
            clean_query = urlencode(query_params, doseq=True)
            database_url = urlunparse(parsed._replace(query=clean_query))

        return database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
