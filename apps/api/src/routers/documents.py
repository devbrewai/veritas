"""Document upload and processing endpoints."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.middleware.rate_limit import check_rate_limit
from src.models.document import Document
from src.schemas.document import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
    get_document_processing_status,
)
from src.services.audit import AuditAction, get_client_ip, log_audit_event
from src.services.document_processor import run_document_processing_async
from src.services.retention import compute_expires_at

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    customer_id: str | None = Form(default=None),
    document_type: str = Form(default="passport"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(check_rate_limit),
) -> DocumentUploadResponse:
    """Upload a document for processing. Returns 202; poll GET /v1/documents/{id}/status for completion.

    Rate limited per user (see RATE_LIMIT_UPLOADS_PER_MINUTE). OCR runs in the background.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    supported_types = ["passport", "utility_bill", "business_reg"]
    if document_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Document type '{document_type}' not supported. Supported: {supported_types}",
        )

    doc_id = uuid.uuid4()
    upload_dir = Path(settings.UPLOAD_DIR) / str(doc_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"original.{ext}"
    with open(file_path, "wb") as f:
        f.write(content)

    document = Document(
        id=doc_id,
        user_id=user_id,
        customer_id=customer_id,
        document_type=document_type,
        file_path=str(file_path),
        file_size_bytes=file_size,
        processed=False,
        expires_at=compute_expires_at(settings.DOCUMENT_RETENTION_DAYS),
    )
    db.add(document)

    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.DOCUMENT_UPLOADED,
        resource_type="document",
        resource_id=str(doc_id),
        details={
            "document_type": document_type,
            "status": "processing",
            "file_size_bytes": file_size,
            "customer_id": customer_id,
        },
        ip_address=get_client_ip(request),
    )
    await db.commit()

    background_tasks.add_task(
        run_document_processing_async,
        doc_id,
        document_type,
        file_path,
    )

    status_url = f"{settings.API_V1_PREFIX}/documents/{doc_id}/status"
    estimated_seconds = 10 if document_type == "passport" else 15
    return DocumentUploadResponse(
        document_id=doc_id,
        status="processing",
        message="Document accepted for processing. Poll GET /v1/documents/{id}/status for completion.",
        status_url=status_url,
        estimated_completion_seconds=estimated_seconds,
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> DocumentStatusResponse:
    """Get processing status for a document. Poll until status is completed or failed."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    status_value = get_document_processing_status(
        document.processed,
        document.processing_error,
    )
    message = None
    if status_value == "failed" and document.processing_error:
        message = document.processing_error
    return DocumentStatusResponse(
        document_id=document_id,
        status=status_value,
        message=message,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Document:
    """Retrieve a document by ID.

    Args:
        document_id: UUID of the document.
        db: Database session.
        user_id: Current authenticated user's ID.

    Returns:
        Document details including extracted data.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.DOCUMENT_VIEWED,
        resource_type="document",
        resource_id=str(document_id),
        ip_address=get_client_ip(request),
    )

    return document
