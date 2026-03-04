"""Webhook configuration model for outbound event delivery."""

import json
import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from src.models.base import Base


class StringArrayType(TypeDecorator):
    """Store list[str] as ARRAY on PostgreSQL and as JSON text on SQLite for tests."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String(64)))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value) if value else "[]"

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return list(value) if value else []
        return json.loads(value) if value else []


class WebhookConfig(Base):
    """Webhook endpoint configuration. Payloads are signed with HMAC-SHA256."""

    __tablename__ = "webhook_configs"

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
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list[str]] = mapped_column(
        StringArrayType(),
        nullable=False,
        default=list,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
