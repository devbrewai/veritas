"""SQLAlchemy model for screening results."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class ScreeningResult(Base):
    """Screening results table for sanctions and adverse media."""

    __tablename__ = "screening_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenant isolation (uncomment in Day 5 with auth)
    # user_id: Mapped[uuid.UUID] = mapped_column(
    #     Uuid,
    #     ForeignKey("users.id"),
    #     nullable=False,
    #     index=True,
    # )

    # Link to source document (optional - may screen without document)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id"),
        nullable=True,
        index=True,
    )

    # Customer reference
    customer_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    # Screened name
    full_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Sanctions screening results
    sanctions_match: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    sanctions_decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="no_match",
    )  # match, review, no_match

    sanctions_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    sanctions_details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )  # Full match details

    # Adverse media (Day 4)
    adverse_media_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    adverse_media_summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Risk scoring (Day 4)
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    risk_tier: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # Low, Medium, High

    risk_reasons: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    recommendation: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # Approve, Review, Reject

    # Timestamps and performance
    screened_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationship to document
    document = relationship("Document", backref="screening_results")
