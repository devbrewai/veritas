from functools import lru_cache
from typing import Any

from pydantic import field_validator
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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        """Normalize PostgreSQL URLs to asyncpg for SQLAlchemy async engine usage."""
        if not isinstance(value, str):
            raise ValueError("DATABASE_URL must be a string")

        database_url = value.strip()
        if database_url.startswith("postgres://"):
            return f"postgresql+asyncpg://{database_url[len('postgres://'):]}"

        if database_url.startswith("postgresql://"):
            return f"postgresql+asyncpg://{database_url[len('postgresql://'):]}"

        scheme, separator, remainder = database_url.partition("://")
        if scheme.startswith("postgresql+") and scheme != "postgresql+asyncpg" and separator:
            return f"postgresql+asyncpg://{remainder}"

        return database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
