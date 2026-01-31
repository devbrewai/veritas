"""Document upload and processing endpoints."""

import logging
import uuid
from datetime import date, timedelta
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
from src.services.ocr import (
    DocumentQualityChecker,
    GoogleVisionOCR,
    ImagePreprocessor,
    MRZDetector,
    OCRExtractor,
    PDFHandler,
)
from src.services.parsers import BusinessDocumentParser, PassportParser, UtilityBillParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()

# Initialize services
preprocessor = ImagePreprocessor()
mrz_detector = MRZDetector()
ocr_extractor = OCRExtractor()
pdf_handler = PDFHandler()
quality_checker = DocumentQualityChecker()

# Initialize parsers
passport_parser = PassportParser()
utility_bill_parser = UtilityBillParser()
business_doc_parser = BusinessDocumentParser()

# Initialize Google Vision OCR (optional fallback)
google_vision_ocr: GoogleVisionOCR | None = None
if settings.GOOGLE_VISION_ENABLED:
    google_vision_ocr = GoogleVisionOCR()
    if google_vision_ocr.is_available:
        logger.info("Google Vision OCR enabled as fallback")
    else:
        logger.warning("Google Vision enabled but API key not configured")
        google_vision_ocr = None


def _build_success_response(
    parse_result: Any,
    provider: str,
) -> dict[str, Any]:
    """Build success response from parse result.

    Args:
        parse_result: PassportExtractionResult from parser.
        provider: Name of OCR provider that succeeded.

    Returns:
        Response dictionary with extracted data.
    """
    return {
        "data": parse_result.data.model_dump(mode="json") if parse_result.data else None,
        "confidence": parse_result.confidence,
        "errors": parse_result.errors,
        "warnings": parse_result.warnings,
        "ocr_provider": provider,
    }


def process_passport(file_path: Path) -> dict[str, Any]:
    """Process passport image and extract MRZ data.

    Uses a hybrid OCR strategy:
    1. Tesseract on raw MRZ region (fast, free)
    2. Tesseract on preprocessed MRZ region
    3. Google Vision API fallback (if enabled, higher accuracy)

    Args:
        file_path: Path to the uploaded passport image.

    Returns:
        Dictionary with extracted data, confidence, errors, warnings, and provider.
    """
    # Load image
    image = cv2.imread(str(file_path))
    if image is None:
        return {
            "data": None,
            "confidence": 0.0,
            "errors": ["Could not load image"],
            "ocr_provider": "none",
        }

    # Detect MRZ region
    mrz_region = mrz_detector.detect_with_fallback(image)
    strategies_tried = []
    last_result = None

    # Strategy 1: Tesseract on raw MRZ region (often works best for clear images)
    logger.debug("Trying Tesseract on raw MRZ region")
    ocr_result = ocr_extractor.extract_mrz(mrz_region.image)
    parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_raw")

    if parse_result.success:
        logger.info("Passport extracted successfully with Tesseract (raw)")
        return _build_success_response(parse_result, "tesseract")

    last_result = parse_result

    # Strategy 2: Tesseract on preprocessed MRZ region
    logger.debug("Trying Tesseract on preprocessed MRZ region")
    preprocessed = preprocessor.preprocess_for_mrz(mrz_region.image)
    ocr_result = ocr_extractor.extract_mrz(preprocessed)
    parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_preprocessed")

    if parse_result.success:
        logger.info("Passport extracted successfully with Tesseract (preprocessed)")
        return _build_success_response(parse_result, "tesseract_preprocessed")

    last_result = parse_result

    # Strategy 3: Google Vision API (if enabled and available)
    if google_vision_ocr is not None:
        logger.debug("Trying Google Vision API fallback")

        # Try on raw MRZ region first
        ocr_result = google_vision_ocr.extract_mrz(mrz_region.image)
        parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision_raw")

        if parse_result.success:
            logger.info("Passport extracted successfully with Google Vision")
            return _build_success_response(parse_result, "google_vision")

        last_result = parse_result

        # Try on bottom portion of full image (different crop)
        h, w = image.shape[:2]
        bottom_region = image[int(h * 0.65):h, 0:w]
        ocr_result = google_vision_ocr.extract_mrz(bottom_region)
        parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision_bottom")

        if parse_result.success:
            logger.info("Passport extracted successfully with Google Vision (bottom crop)")
            return _build_success_response(parse_result, "google_vision")

        last_result = parse_result

    # All strategies failed
    logger.warning(f"All OCR strategies failed. Tried: {strategies_tried}")
    return {
        "data": None,
        "confidence": last_result.confidence if last_result else 0.0,
        "errors": last_result.errors if last_result else ["All OCR strategies failed"],
        "warnings": [f"Tried strategies: {', '.join(strategies_tried)}"],
        "ocr_provider": "none",
    }


def _load_image(file_path: Path) -> tuple[Any, str | None]:
    """Load image from file path, handling PDF conversion.

    Args:
        file_path: Path to the image or PDF file.

    Returns:
        Tuple of (image as numpy array, error message if failed).
    """
    if pdf_handler.is_pdf(file_path):
        image = pdf_handler.get_first_page(file_path)
        if image is None:
            return None, "Could not read PDF file"
        return image, None

    image = cv2.imread(str(file_path))
    if image is None:
        return None, "Could not load image"
    return image, None


def process_utility_bill(file_path: Path) -> dict[str, Any]:
    """Process utility bill image/PDF and extract data.

    Uses full-page OCR with regex-based field extraction.

    Args:
        file_path: Path to the uploaded utility bill.

    Returns:
        Dictionary with extracted data, confidence, errors, warnings, and provider.
    """
    # Load image (handle PDF)
    image, error = _load_image(file_path)
    if error:
        return {
            "data": None,
            "confidence": 0.0,
            "errors": [error],
            "ocr_provider": "none",
        }

    # Check image quality
    quality = quality_checker.check_quality(image)
    quality_warnings = []
    if not quality["is_acceptable"]:
        quality_warnings = quality["suggestions"]

    strategies_tried = []
    last_result = None

    # Strategy 1: Tesseract on preprocessed full page
    logger.debug("Trying Tesseract on preprocessed image")
    preprocessed = preprocessor.preprocess_for_ocr(image)
    ocr_result = ocr_extractor.extract_document_text(preprocessed)
    parse_result = utility_bill_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_preprocessed")

    if parse_result.success:
        logger.info("Utility bill extracted successfully with Tesseract (preprocessed)")
        result = _build_success_response(parse_result, "tesseract")
        result["warnings"] = result.get("warnings", []) + quality_warnings
        return result

    last_result = parse_result

    # Strategy 2: Tesseract on raw image
    logger.debug("Trying Tesseract on raw image")
    ocr_result = ocr_extractor.extract_document_text(image)
    parse_result = utility_bill_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_raw")

    if parse_result.success:
        logger.info("Utility bill extracted successfully with Tesseract (raw)")
        result = _build_success_response(parse_result, "tesseract")
        result["warnings"] = result.get("warnings", []) + quality_warnings
        return result

    last_result = parse_result

    # Strategy 3: Google Vision API (if enabled)
    if google_vision_ocr is not None:
        logger.debug("Trying Google Vision API fallback")
        ocr_result = google_vision_ocr.extract_text(image)
        parse_result = utility_bill_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision")

        if parse_result.success:
            logger.info("Utility bill extracted successfully with Google Vision")
            result = _build_success_response(parse_result, "google_vision")
            result["warnings"] = result.get("warnings", []) + quality_warnings
            return result

        last_result = parse_result

    # All strategies failed
    logger.warning(f"All OCR strategies failed for utility bill. Tried: {strategies_tried}")
    return {
        "data": None,
        "confidence": last_result.confidence if last_result else 0.0,
        "errors": last_result.errors if last_result else ["All OCR strategies failed"],
        "warnings": [f"Tried strategies: {', '.join(strategies_tried)}"] + quality_warnings,
        "ocr_provider": "none",
    }


def process_business_document(file_path: Path) -> dict[str, Any]:
    """Process business registration document image/PDF and extract data.

    Uses full-page OCR with regex-based field extraction.

    Args:
        file_path: Path to the uploaded business document.

    Returns:
        Dictionary with extracted data, confidence, errors, warnings, and provider.
    """
    # Load image (handle PDF)
    image, error = _load_image(file_path)
    if error:
        return {
            "data": None,
            "confidence": 0.0,
            "errors": [error],
            "ocr_provider": "none",
        }

    # Check image quality
    quality = quality_checker.check_quality(image)
    quality_warnings = []
    if not quality["is_acceptable"]:
        quality_warnings = quality["suggestions"]

    strategies_tried = []
    last_result = None

    # Strategy 1: Tesseract on preprocessed full page
    logger.debug("Trying Tesseract on preprocessed image")
    preprocessed = preprocessor.preprocess_for_ocr(image)
    ocr_result = ocr_extractor.extract_document_text(preprocessed)
    parse_result = business_doc_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_preprocessed")

    if parse_result.success:
        logger.info("Business document extracted successfully with Tesseract (preprocessed)")
        result = _build_success_response(parse_result, "tesseract")
        result["warnings"] = result.get("warnings", []) + quality_warnings
        return result

    last_result = parse_result

    # Strategy 2: Tesseract on raw image
    logger.debug("Trying Tesseract on raw image")
    ocr_result = ocr_extractor.extract_document_text(image)
    parse_result = business_doc_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_raw")

    if parse_result.success:
        logger.info("Business document extracted successfully with Tesseract (raw)")
        result = _build_success_response(parse_result, "tesseract")
        result["warnings"] = result.get("warnings", []) + quality_warnings
        return result

    last_result = parse_result

    # Strategy 3: Google Vision API (if enabled)
    if google_vision_ocr is not None:
        logger.debug("Trying Google Vision API fallback")
        ocr_result = google_vision_ocr.extract_text(image)
        parse_result = business_doc_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision")

        if parse_result.success:
            logger.info("Business document extracted successfully with Google Vision")
            result = _build_success_response(parse_result, "google_vision")
            result["warnings"] = result.get("warnings", []) + quality_warnings
            return result

        last_result = parse_result

    # All strategies failed
    logger.warning(f"All OCR strategies failed for business document. Tried: {strategies_tried}")
    return {
        "data": None,
        "confidence": last_result.confidence if last_result else 0.0,
        "errors": last_result.errors if last_result else ["All OCR strategies failed"],
        "warnings": [f"Tried strategies: {', '.join(strategies_tried)}"] + quality_warnings,
        "ocr_provider": "none",
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
        result = None

        if document_type == "passport":
            result = process_passport(file_path)
        elif document_type == "utility_bill":
            result = process_utility_bill(file_path)
        elif document_type == "business_reg":
            result = process_business_document(file_path)
        else:
            supported = ["passport", "utility_bill", "business_reg"]
            processing_error = f"Document type '{document_type}' not supported. Supported: {supported}"

        if result:
            document.extracted_data = result.get("data")
            document.ocr_confidence = result.get("confidence")

            if result.get("data"):
                document.processed = True
                status = "completed"

                # Calculate issue_date from expiry_date for passports
                # Assumes 10-year passport validity (standard for adults)
                if document_type == "passport" and document.extracted_data:
                    expiry_date_str = document.extracted_data.get("expiry_date")
                    if expiry_date_str:
                        try:
                            # Parse the expiry date (format: YYYY-MM-DD)
                            expiry_date = date.fromisoformat(expiry_date_str)
                            # Calculate issue date assuming 10-year validity
                            document.issue_date = expiry_date - timedelta(days=365 * 10)
                            logger.info(
                                f"Calculated issue_date {document.issue_date} "
                                f"from expiry_date {expiry_date}"
                            )
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Could not parse expiry_date: {e}")
            else:
                errors = result.get("errors", [])
                processing_error = "; ".join(errors) if errors else "Extraction failed"

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
