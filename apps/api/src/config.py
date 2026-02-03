from functools import lru_cache

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

    # Sanctions Screening
    SANCTIONS_PICKLE_PATH: str = "./models/sanctions_screener.pkl"
    SANCTIONS_ENABLED: bool = True

    # Authentication (Better Auth JWT validation)
    BETTER_AUTH_URL: str = "http://localhost:3000"
    JWKS_CACHE_TTL: int = 3600  # Cache JWKS for 1 hour

    # Rate Limiting
    RATE_LIMIT_UPLOADS_PER_MINUTE: int = 10


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
