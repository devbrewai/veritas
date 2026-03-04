"""Pydantic schemas for document operations."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

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
    """Response after document upload."""

    document_id: UUID
    status: Literal["processing", "completed", "failed"]
    message: str


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

    model_config = {"from_attributes": True}
