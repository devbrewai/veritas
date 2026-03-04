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

    document_id: UUID
    status: DocumentProcessingStatus
    message: str | None = None


class DocumentUploadResponse(BaseModel):
    """Response after document upload (202 Accepted)."""

    document_id: UUID
    status: Literal["processing", "completed", "failed"]
    message: str
    status_url: str | None = None
    estimated_completion_seconds: int | None = None


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
