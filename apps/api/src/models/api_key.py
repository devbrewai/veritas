"""API key model for programmatic access."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ApiKey(Base):
    """API keys for X-API-Key authentication. Keys are stored hashed (SHA-256)."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(default=10, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
