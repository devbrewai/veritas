"""Pydantic schemas for user-related endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


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
