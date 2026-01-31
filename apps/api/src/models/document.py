import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Document(Base):
    """Document table for storing uploaded documents and extraction results."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenant isolation - will be added in Day 5 with auth
    # user_id: Mapped[uuid.UUID] = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey("users.id"),
    #     nullable=False,
    #     index=True,
    # )

    customer_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # passport, utility_bill, business_reg, drivers_license

    uploaded_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    extracted_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ocr_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Document issue date - calculated from expiry date for passports
    # Used for document age risk scoring (older documents = higher risk)
    issue_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
