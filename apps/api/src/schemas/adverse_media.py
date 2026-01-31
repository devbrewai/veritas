"""Pydantic schemas for adverse media scanning."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SentimentCategory(str, Enum):
    """Sentiment classification for article titles."""

    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class AdverseMediaArticle(BaseModel):
    """A single article from adverse media search."""

    title: str
    url: str
    source: str | None = None
    published_date: datetime | None = None
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_category: SentimentCategory


class AdverseMediaData(BaseModel):
    """Core adverse media scan result data."""

    query_name: str
    articles_found: int
    negative_mentions: int
    average_sentiment: float = Field(ge=-1.0, le=1.0)
    articles: list[AdverseMediaArticle] = Field(default_factory=list)
    search_terms_used: list[str] = Field(default_factory=list)


class AdverseMediaResult(BaseModel):
    """Full adverse media scan result."""

    success: bool
    data: AdverseMediaData | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    cached: bool = False


class AdverseMediaRequest(BaseModel):
    """Request for adverse media scan."""

    name: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)


class AdverseMediaResponse(BaseModel):
    """API response for adverse media scan."""

    result: AdverseMediaResult
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    api_version: str = "1.0.0"
