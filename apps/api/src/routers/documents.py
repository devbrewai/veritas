"""Document upload and processing endpoints."""

import uuid
from pathlib import Path
from typing import Any

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.models.document import Document
from src.schemas.document import DocumentResponse, DocumentUploadResponse
from src.services.ocr import ImagePreprocessor, MRZDetector, OCRExtractor
from src.services.parsers import PassportParser

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()

# Initialize services
preprocessor = ImagePreprocessor()
mrz_detector = MRZDetector()
ocr_extractor = OCRExtractor()
passport_parser = PassportParser()


def process_passport(file_path: Path) -> dict[str, Any]:
    """Process passport image and extract MRZ data.

    Args:
        file_path: Path to the uploaded passport image.

    Returns:
        Dictionary with extracted data, confidence, errors, and warnings.
    """
    # Load image
    image = cv2.imread(str(file_path))
    if image is None:
        return {"data": None, "confidence": 0.0, "errors": ["Could not load image"]}

    # Detect MRZ region
    mrz_region = mrz_detector.detect_with_fallback(image)

    # Try OCR on raw MRZ region first (often works better than preprocessed)
    ocr_result = ocr_extractor.extract_mrz(mrz_region.image)
    parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)

    # If raw image didn't work, try with preprocessing
    if not parse_result.success:
        preprocessed = preprocessor.preprocess_for_mrz(mrz_region.image)
        ocr_result = ocr_extractor.extract_mrz(preprocessed)
        parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)

    if parse_result.success and parse_result.data:
        return {
            "data": parse_result.data.model_dump(mode="json"),
            "confidence": parse_result.confidence,
            "errors": parse_result.errors,
            "warnings": parse_result.warnings,
        }

    return {
        "data": None,
        "confidence": parse_result.confidence,
        "errors": parse_result.errors,
        "warnings": parse_result.warnings,
    }


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    customer_id: str | None = Form(default=None),
    document_type: str = Form(default="passport"),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload and process a document.

    Args:
        file: The document file (image or PDF).
        customer_id: Optional customer identifier.
        document_type: Type of document (passport, utility_bill, etc.).
        db: Database session.

    Returns:
        DocumentUploadResponse with document ID and processing status.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Generate unique filename and save
    doc_id = uuid.uuid4()
    upload_dir = Path(settings.UPLOAD_DIR) / str(doc_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"original.{ext}"

    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    document = Document(
        id=doc_id,
        customer_id=customer_id,
        document_type=document_type,
        file_path=str(file_path),
        file_size_bytes=file_size,
        processed=False,
    )

    processing_error: str | None = None
    status = "failed"

    try:
        # Process document synchronously for Day 1
        # (Will be made async in Day 6)
        if document_type == "passport":
            result = process_passport(file_path)
            document.extracted_data = result.get("data")
            document.ocr_confidence = result.get("confidence")

            if result.get("data"):
                document.processed = True
                status = "completed"
            else:
                errors = result.get("errors", [])
                processing_error = "; ".join(errors) if errors else "Extraction failed"
        else:
            processing_error = f"Document type '{document_type}' not yet supported"

    except Exception as e:
        processing_error = str(e)

    document.processing_error = processing_error

    db.add(document)
    await db.commit()

    return DocumentUploadResponse(
        document_id=doc_id,
        status=status,
        message="Document processed successfully"
        if status == "completed"
        else (processing_error or "Unknown error"),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Document:
    """Retrieve a document by ID.

    Args:
        document_id: UUID of the document.
        db: Database session.

    Returns:
        Document details including extracted data.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document
