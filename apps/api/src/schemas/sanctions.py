"""Pydantic schemas for sanctions screening."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SanctionsDecision(str, Enum):
    """Sanctions screening decision."""

    MATCH = "match"  # Score >= 0.90
    REVIEW = "review"  # Score >= 0.80 and < 0.90
    NO_MATCH = "no_match"  # Score < 0.80


# --- Request Schemas ---


class SanctionsScreenRequest(BaseModel):
    """Request to screen a single name against sanctions lists."""

    name: str = Field(..., min_length=1, max_length=500, description="Name to screen")
    aliases: list[str] | None = Field(
        default=None,
        max_length=10,
        description="Alternative name variations",
    )
    nationality: str | None = Field(
        default=None,
        max_length=3,
        description="ISO 3166-1 alpha-2 or alpha-3 country code",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of top matches to return",
    )


class SanctionsBatchRequest(BaseModel):
    """Request to screen multiple names against sanctions lists."""

    queries: list[SanctionsScreenRequest] = Field(
        ...,
        max_length=100,
        description="List of names to screen (max 100)",
    )


class DocumentScreenRequest(BaseModel):
    """Request to screen names extracted from a document."""

    document_id: UUID = Field(..., description="ID of the processed document")
    include_aliases: bool = Field(
        default=True,
        description="Include name variations from document",
    )


# --- Data Schemas ---


class SanctionsMatchData(BaseModel):
    """A single match from sanctions screening."""

    matched_name: str = Field(description="Name from sanctions list")
    score: float = Field(ge=0, le=1, description="Composite similarity score")
    decision: SanctionsDecision = Field(description="Screening decision")
    country: str | None = Field(default=None, description="Country code if available")
    program: str | None = Field(
        default=None,
        description="Sanctions program (e.g., IRAN, CUBA)",
    )
    source: Literal["SDN", "Consolidated"] = Field(
        default="SDN",
        description="Source sanctions list",
    )
    uid: str = Field(description="Unique identifier for the sanctions record")
    similarity_details: dict[str, float] | None = Field(
        default=None,
        description="Detailed similarity scores (sim_set, sim_sort, sim_partial)",
    )

    model_config = {"from_attributes": True}


class SanctionsScreeningData(BaseModel):
    """Core screening result data."""

    query_name: str = Field(description="Original query name")
    query_normalized: str = Field(description="Normalized version of query name")
    is_match: bool = Field(description="True if top match exceeds match threshold")
    decision: SanctionsDecision = Field(description="Overall screening decision")
    top_match: SanctionsMatchData | None = Field(
        default=None,
        description="Highest scoring match if any",
    )
    all_matches: list[SanctionsMatchData] = Field(
        default_factory=list,
        description="All matches above minimum threshold",
    )
    lists_checked: list[str] = Field(
        default_factory=lambda: ["OFAC_SDN", "OFAC_Consolidated"],
        description="Sanctions lists that were checked",
    )
    applied_filters: dict[str, str | None] = Field(
        default_factory=dict,
        description="Filters that were applied (country, program)",
    )


# --- Result Schemas ---


class SanctionsScreeningResult(BaseModel):
    """Full screening result with metadata."""

    success: bool = Field(description="Whether screening completed successfully")
    data: SanctionsScreeningData | None = Field(
        default=None,
        description="Screening data if successful",
    )
    confidence: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Confidence in the screening result",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages if screening failed",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages for attention",
    )
    processing_time_ms: float = Field(
        default=0.0,
        description="Time taken to perform screening",
    )
    cached: bool = Field(default=False, description="Whether result was from cache")


# --- Response Schemas ---


class SanctionsScreenResponse(BaseModel):
    """API response for single name screening."""

    result: SanctionsScreeningResult = Field(description="Screening result")
    screened_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of screening",
    )
    api_version: str = Field(default="1.0.0", description="API version")


class SanctionsBatchResponse(BaseModel):
    """API response for batch screening."""

    results: list[SanctionsScreeningResult] = Field(
        description="Screening results for each query",
    )
    total_screened: int = Field(description="Total number of names screened")
    total_matches: int = Field(description="Number of names with match decision")
    total_reviews: int = Field(description="Number of names requiring review")
    total_processing_time_ms: float = Field(description="Total processing time")
    screened_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of batch screening",
    )


class SanctionsServiceStatus(BaseModel):
    """Sanctions service health status."""

    status: Literal["healthy", "degraded", "unavailable"] = Field(
        description="Service health status",
    )
    loaded: bool = Field(description="Whether screener data is loaded")
    record_count: int = Field(description="Number of sanctions records loaded")
    version: str = Field(description="Screener version")
    last_updated: datetime | None = Field(
        default=None,
        description="When sanctions data was last updated",
    )
    cache_enabled: bool = Field(default=False, description="Whether caching is enabled")
