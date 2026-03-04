"""Background document processing: OCR and DB update.

Single place for sync OCR (passport, utility_bill, business_reg) and async
run that loads document, runs OCR in a thread, and updates the document.
Used by the upload handler via BackgroundTasks (returns 202, process later).
"""

import asyncio
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import cv2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import async_session_maker
from src.models.document import Document
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
settings = get_settings()

# OCR and parsers (lazy init for Google Vision from settings)
preprocessor = ImagePreprocessor()
mrz_detector = MRZDetector()
ocr_extractor = OCRExtractor()
pdf_handler = PDFHandler()
quality_checker = DocumentQualityChecker()
passport_parser = PassportParser()
utility_bill_parser = UtilityBillParser()
business_doc_parser = BusinessDocumentParser()

_google_vision_ocr: GoogleVisionOCR | None = None


def _get_google_vision_ocr() -> GoogleVisionOCR | None:
    """Lazy init Google Vision OCR when enabled."""
    global _google_vision_ocr
    if _google_vision_ocr is not None:
        return _google_vision_ocr
    if not settings.GOOGLE_VISION_ENABLED:
        return None
    _google_vision_ocr = GoogleVisionOCR()
    if _google_vision_ocr.is_available:
        logger.info("Google Vision OCR enabled as fallback (document_processor)")
    else:
        logger.warning("Google Vision enabled but API key not configured")
        _google_vision_ocr = None
    return _google_vision_ocr


def _build_success_response(
    parse_result: Any,
    provider: str,
    quality_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build result dict from parse result."""
    warnings = list(parse_result.warnings or [])
    if quality_warnings:
        warnings = warnings + quality_warnings
    return {
        "data": parse_result.data.model_dump(mode="json") if parse_result.data else None,
        "confidence": parse_result.confidence,
        "errors": parse_result.errors,
        "warnings": warnings,
        "ocr_provider": provider,
    }


def _load_image(file_path: Path) -> tuple[Any, str | None]:
    """Load image from file path (PDF, HEIC, or image). Returns (image, error)."""
    if pdf_handler.is_pdf(file_path):
        image = pdf_handler.get_first_page(file_path)
        if image is None:
            return None, "Could not read PDF file"
        return image, None
    suffix = file_path.suffix.lower()
    if suffix in (".heic", ".heif"):
        try:
            from PIL import Image
            from pillow_heif import register_heif_opener

            register_heif_opener()
            pil_image = Image.open(str(file_path)).convert("RGB")
            image = np.array(pil_image)[:, :, ::-1].copy()
            return image, None
        except Exception:
            return None, "Could not read HEIC file"
    image = cv2.imread(str(file_path))
    if image is None:
        return None, "Could not load image"
    return image, None


def process_passport(file_path: Path) -> dict[str, Any]:
    """Process passport image and extract MRZ data (sync, CPU-bound)."""
    image, error = _load_image(file_path)
    if error:
        return {"data": None, "confidence": 0.0, "errors": [error], "ocr_provider": "none"}
    quality = quality_checker.check_quality(image)
    quality_warnings: list[str] = quality["suggestions"] if not quality["is_acceptable"] else []
    mrz_region = mrz_detector.detect_with_fallback(image)
    strategies_tried = []
    last_result = None

    ocr_result = ocr_extractor.extract_mrz(mrz_region.image)
    parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_raw")
    if parse_result.success:
        return _build_success_response(parse_result, "tesseract", quality_warnings)
    last_result = parse_result

    preprocessed = preprocessor.preprocess_for_mrz(mrz_region.image)
    ocr_result = ocr_extractor.extract_mrz(preprocessed)
    parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_preprocessed")
    if parse_result.success:
        return _build_success_response(parse_result, "tesseract_preprocessed", quality_warnings)
    last_result = parse_result

    gv = _get_google_vision_ocr()
    if gv is not None:
        ocr_result = gv.extract_mrz(mrz_region.image)
        parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision_raw")
        if parse_result.success:
            return _build_success_response(parse_result, "google_vision", quality_warnings)
        last_result = parse_result
        h, w = image.shape[:2]
        bottom_region = image[int(h * 0.65) : h, 0:w]
        ocr_result = gv.extract_mrz(bottom_region)
        parse_result = passport_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision_bottom")
        if parse_result.success:
            return _build_success_response(parse_result, "google_vision", quality_warnings)
        last_result = parse_result

    logger.warning("All OCR strategies failed for passport. Tried: %s", strategies_tried)
    return {
        "data": None,
        "confidence": last_result.confidence if last_result else 0.0,
        "errors": last_result.errors if last_result else ["All OCR strategies failed"],
        "warnings": [f"Tried strategies: {', '.join(strategies_tried)}"] + quality_warnings,
        "ocr_provider": "none",
    }


def process_utility_bill(file_path: Path) -> dict[str, Any]:
    """Process utility bill image/PDF (sync, CPU-bound)."""
    image, error = _load_image(file_path)
    if error:
        return {"data": None, "confidence": 0.0, "errors": [error], "ocr_provider": "none"}
    quality = quality_checker.check_quality(image)
    quality_warnings = quality["suggestions"] if not quality["is_acceptable"] else []
    strategies_tried = []
    last_result = None

    preprocessed = preprocessor.preprocess_for_ocr(image)
    ocr_result = ocr_extractor.extract_document_text(preprocessed)
    parse_result = utility_bill_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_preprocessed")
    if parse_result.success:
        return _build_success_response(parse_result, "tesseract", quality_warnings)
    last_result = parse_result

    ocr_result = ocr_extractor.extract_document_text(image)
    parse_result = utility_bill_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_raw")
    if parse_result.success:
        return _build_success_response(parse_result, "tesseract", quality_warnings)
    last_result = parse_result

    gv = _get_google_vision_ocr()
    if gv is not None:
        ocr_result = gv.extract_text(image)
        parse_result = utility_bill_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision")
        if parse_result.success:
            return _build_success_response(parse_result, "google_vision", quality_warnings)
        last_result = parse_result

    logger.warning("All OCR strategies failed for utility bill. Tried: %s", strategies_tried)
    return {
        "data": None,
        "confidence": last_result.confidence if last_result else 0.0,
        "errors": last_result.errors if last_result else ["All OCR strategies failed"],
        "warnings": [f"Tried strategies: {', '.join(strategies_tried)}"] + quality_warnings,
        "ocr_provider": "none",
    }


def process_business_document(file_path: Path) -> dict[str, Any]:
    """Process business registration document (sync, CPU-bound)."""
    image, error = _load_image(file_path)
    if error:
        return {"data": None, "confidence": 0.0, "errors": [error], "ocr_provider": "none"}
    quality = quality_checker.check_quality(image)
    quality_warnings = quality["suggestions"] if not quality["is_acceptable"] else []
    strategies_tried = []
    last_result = None

    preprocessed = preprocessor.preprocess_for_ocr(image)
    ocr_result = ocr_extractor.extract_document_text(preprocessed)
    parse_result = business_doc_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_preprocessed")
    if parse_result.success:
        return _build_success_response(parse_result, "tesseract", quality_warnings)
    last_result = parse_result

    ocr_result = ocr_extractor.extract_document_text(image)
    parse_result = business_doc_parser.parse(ocr_result.text, ocr_result.confidence)
    strategies_tried.append("tesseract_raw")
    if parse_result.success:
        return _build_success_response(parse_result, "tesseract", quality_warnings)
    last_result = parse_result

    gv = _get_google_vision_ocr()
    if gv is not None:
        ocr_result = gv.extract_text(image)
        parse_result = business_doc_parser.parse(ocr_result.text, ocr_result.confidence)
        strategies_tried.append("google_vision")
        if parse_result.success:
            return _build_success_response(parse_result, "google_vision", quality_warnings)
        last_result = parse_result

    logger.warning("All OCR strategies failed for business document. Tried: %s", strategies_tried)
    return {
        "data": None,
        "confidence": last_result.confidence if last_result else 0.0,
        "errors": last_result.errors if last_result else ["All OCR strategies failed"],
        "warnings": [f"Tried strategies: {', '.join(strategies_tried)}"] + quality_warnings,
        "ocr_provider": "none",
    }


def process_document_sync(file_path: Path, document_type: str) -> dict[str, Any]:
    """Run OCR for the given document type (sync). Returns result dict."""
    if document_type == "passport":
        return process_passport(file_path)
    if document_type == "utility_bill":
        return process_utility_bill(file_path)
    if document_type == "business_reg":
        return process_business_document(file_path)
    return {
        "data": None,
        "confidence": 0.0,
        "errors": [f"Document type '{document_type}' not supported"],
        "ocr_provider": "none",
    }


async def run_document_processing_async(
    document_id: UUID,
    document_type: str,
    file_path: Path,
) -> None:
    """Load document, run OCR in a thread, update document. Uses its own DB session."""
    async with async_session_maker() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            if not document:
                logger.warning("Document %s not found for background processing", document_id)
                return
            if document.processed:
                logger.debug("Document %s already processed, skipping", document_id)
                return

            result_dict = await asyncio.to_thread(
                process_document_sync, file_path, document_type
            )

            document.extracted_data = result_dict.get("data")
            document.ocr_confidence = result_dict.get("confidence")
            errors = result_dict.get("errors", [])
            if result_dict.get("data"):
                document.processed = True
                document.processing_error = None
                if document_type == "passport" and document.extracted_data:
                    expiry_date_str = document.extracted_data.get("expiry_date")
                    if expiry_date_str:
                        try:
                            expiry_date = date.fromisoformat(expiry_date_str)
                            document.issue_date = expiry_date - timedelta(days=365 * 10)
                        except (ValueError, TypeError):
                            pass
            else:
                document.processing_error = "; ".join(errors) if errors else "Extraction failed"

            await db.commit()
            logger.info("Background processing completed for document %s", document_id)
        except Exception as e:
            logger.exception("Background processing failed for document %s: %s", document_id, e)
            try:
                result = await db.execute(select(Document).where(Document.id == document_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.processing_error = str(e)
                    await db.commit()
            except Exception:
                await db.rollback()
