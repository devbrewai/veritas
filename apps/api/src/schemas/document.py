"""Pydantic schemas for document operations."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Single source of truth for document processing status (DRY)
DocumentProcessingStatus = Literal["processing", "completed", "failed"]


def get_document_processing_status(
    processed: bool,
    processing_error: str | None,
) -> DocumentProcessingStatus:
    """Derive status from document fields. Use for GET status and GET document."""
    if processed:
        return "completed"
    if processing_error:
        return "failed"
    return "processing"


class DocumentStatusResponse(BaseModel):
    """Response for GET /v1/documents/{id}/status."""

    document_id: UUID = Field(..., description="Unique identifier for the document")
    status: DocumentProcessingStatus = Field(
        ..., description="Current status: processing, completed, or failed"
    )
    message: str | None = Field(None, description="Error or status message when relevant")
    estimated_completion_seconds: int | None = Field(
        None, description="Estimated seconds until completion (null when completed or failed)"
    )


class DocumentUploadResponse(BaseModel):
    """Response after document upload (202 Accepted)."""

    document_id: UUID = Field(..., description="Unique identifier for the uploaded document")
    status: Literal["processing", "completed", "failed"] = Field(
        default="processing", description="Current processing status"
    )
    message: str = Field(
        ..., description="Human-readable status message (e.g. poll instructions)"
    )
    status_url: str = Field(
        ..., description="URL to poll for status: GET /v1/documents/{document_id}/status"
    )
    estimated_completion_seconds: int | None = Field(
        ..., description="Estimated time to complete processing in seconds"
    )


class DocumentResponse(BaseModel):
    """Response schema for document retrieval."""

    id: UUID
    customer_id: str | None
    document_type: str
    uploaded_at: datetime
    file_size_bytes: int
    processed: bool
    ocr_confidence: float | None
    extracted_data: dict[str, Any] | None
    processing_error: str | None
    status: DocumentProcessingStatus = "processing"

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_status_from_processed(self) -> "DocumentResponse":
        self.status = get_document_processing_status(self.processed, self.processing_error)
        return self
