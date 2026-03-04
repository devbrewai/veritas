"""Pydantic schemas for user-related endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class UserStats(BaseModel):
    """User statistics for documents and screenings."""

    total_documents: int = Field(default=0, ge=0)
    documents_by_type: dict[str, int] = Field(default_factory=dict)
    documents_this_month: int = Field(default=0, ge=0)

    total_screenings: int = Field(default=0, ge=0)
    screenings_by_decision: dict[str, int] = Field(default_factory=dict)
    screenings_this_month: int = Field(default=0, ge=0)

    average_risk_score: float | None = None
    risk_tier_distribution: dict[str, int] = Field(default_factory=dict)

    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Data export (GDPR)
# ---------------------------------------------------------------------------


class DocumentExportItem(BaseModel):
    """Document row for user data export."""

    id: UUID
    customer_id: str | None
    document_type: str
    uploaded_at: datetime
    expires_at: datetime | None
    file_size_bytes: int
    processed: bool
    ocr_confidence: float | None
    issue_date: date | None

    @field_serializer("id")
    def serialize_id(self, v: UUID) -> str:
        return str(v)

    @field_serializer("uploaded_at", "expires_at")
    def serialize_datetime(self, v: datetime | None) -> str | None:
        return v.isoformat() if v else None

    @field_serializer("issue_date")
    def serialize_date(self, v: date | None) -> str | None:
        return v.isoformat() if v else None


class ScreeningExportItem(BaseModel):
    """Screening result row for user data export."""

    id: UUID
    document_id: UUID | None
    customer_id: str | None
    full_name: str
    sanctions_decision: str
    sanctions_score: float | None
    risk_score: float | None
    risk_tier: str | None
    recommendation: str | None
    screened_at: datetime

    @field_serializer("id", "document_id")
    def serialize_uuid(self, v: UUID | None) -> str | None:
        return str(v) if v else None

    @field_serializer("screened_at")
    def serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()


class AuditLogExportItem(BaseModel):
    """Audit log row for user data export."""

    id: UUID
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    created_at: datetime

    @field_serializer("id")
    def serialize_id(self, v: UUID) -> str:
        return str(v)

    @field_serializer("created_at")
    def serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()


class UserDataExport(BaseModel):
    """Full user data export payload (GDPR data export)."""

    documents: list[DocumentExportItem] = Field(default_factory=list)
    screening_results: list[ScreeningExportItem] = Field(default_factory=list)
    audit_logs: list[AuditLogExportItem] = Field(default_factory=list)
    exported_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
