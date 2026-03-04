"""Standardized API error response schemas and codes."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine and human-readable error payload."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional context")


class ErrorResponse(BaseModel):
    """Consistent error envelope for all 4xx/5xx responses."""

    error: ErrorDetail = Field(..., description="Error payload")
    request_id: str = Field(..., description="Unique request identifier for debugging")


class ErrorCode:
    """Machine-readable error codes used in ErrorDetail.code."""

    DOCUMENT_QUALITY_LOW = "DOCUMENT_QUALITY_LOW"
    DOCUMENT_FORMAT_UNSUPPORTED = "DOCUMENT_FORMAT_UNSUPPORTED"
    DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE"
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_API_KEY = "INVALID_API_KEY"
    WEBHOOK_DELIVERY_FAILED = "WEBHOOK_DELIVERY_FAILED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
