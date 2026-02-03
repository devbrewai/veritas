"""Pydantic schemas for KYC aggregation endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KYCStatus(str, Enum):
    """Overall KYC status for a customer."""

    PENDING = "pending"
    APPROVED = "approved"
    REVIEW = "review"
    REJECTED = "rejected"


class KYCDocumentSummary(BaseModel):
    """Summary of a processed document."""

    document_id: UUID
    document_type: str
    processed: bool
    ocr_confidence: float | None = None
    extracted_data: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class KYCSanctionsResult(BaseModel):
    """Sanctions screening result for KYC."""

    screening_id: UUID
    decision: str  # match, review, no_match
    top_match_score: float | None = None
    matched_name: str | None = None
    screened_at: datetime

    model_config = {"from_attributes": True}


class KYCAdverseMediaResult(BaseModel):
    """Adverse media result for KYC."""

    article_count: int = 0
    average_sentiment: float | None = None
    sentiment_category: str | None = None


class KYCRiskResult(BaseModel):
    """Risk assessment result for KYC."""

    risk_score: float
    risk_tier: str  # Low, Medium, High
    recommendation: str  # Approve, Review, Reject
    top_risk_factors: list[str] = Field(default_factory=list)


class KYCResult(BaseModel):
    """Aggregated KYC result for a customer."""

    customer_id: str
    documents: list[KYCDocumentSummary] = Field(default_factory=list)
    sanctions_screening: KYCSanctionsResult | None = None
    adverse_media: KYCAdverseMediaResult | None = None
    risk_assessment: KYCRiskResult | None = None
    overall_status: KYCStatus = KYCStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KYCBatchRequest(BaseModel):
    """Request for batch KYC processing."""

    customer_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of customer IDs to process (max 10)",
    )


class KYCBatchResponse(BaseModel):
    """Response for batch KYC processing."""

    results: list[KYCResult]
    total_processed: int
    total_approved: int = 0
    total_review: int = 0
    total_rejected: int = 0
    total_pending: int = 0
