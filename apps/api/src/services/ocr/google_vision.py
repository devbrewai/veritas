"""Google Cloud Vision API wrapper for OCR."""

import io
import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image

from src.config import get_settings
from src.services.ocr.extractor import OCRResult

logger = logging.getLogger(__name__)


class GoogleVisionOCR:
    """Google Cloud Vision API wrapper for document OCR.

    Provides high-accuracy OCR as a fallback when Tesseract fails.
    Requires GOOGLE_CLOUD_API_KEY environment variable.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Google Vision OCR client.

        Args:
            api_key: Google Cloud API key. If None, reads from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.GOOGLE_CLOUD_API_KEY
        self._client = None

    @property
    def is_available(self) -> bool:
        """Check if Google Vision API is configured and available."""
        return bool(self.api_key)

    def _get_client(self):
        """Lazy initialization of Vision API client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Google Cloud API key not configured")

            from google.cloud import vision
            from google.api_core.client_options import ClientOptions

            # Use API key authentication
            client_options = ClientOptions(
                api_key=self.api_key,
            )
            self._client = vision.ImageAnnotatorClient(client_options=client_options)

        return self._client

    def _image_to_bytes(self, image: np.ndarray | Image.Image) -> bytes:
        """Convert image to bytes for API request.

        Args:
            image: Input image as numpy array or PIL Image.

        Returns:
            Image encoded as PNG bytes.
        """
        if isinstance(image, np.ndarray):
            # Convert numpy array to PIL Image
            # Handle both grayscale and color images
            if len(image.shape) == 2:
                pil_image = Image.fromarray(image)
            elif image.shape[2] == 3:
                # OpenCV uses BGR, convert to RGB
                import cv2
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
            else:
                pil_image = Image.fromarray(image)
        else:
            pil_image = image

        # Convert to bytes
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        return buffer.getvalue()

    def extract_text(
        self,
        image: np.ndarray | Image.Image,
    ) -> OCRResult:
        """Extract text from image using Google Vision API.

        Args:
            image: Input image (numpy array or PIL Image).

        Returns:
            OCRResult with extracted text and confidence score.
        """
        if not self.is_available:
            return OCRResult(
                text="",
                confidence=0.0,
                raw_data={"error": "Google Vision API not configured"},
            )

        try:
            from google.cloud import vision

            client = self._get_client()

            # Convert image to bytes
            image_bytes = self._image_to_bytes(image)

            # Create Vision API image object
            vision_image = vision.Image(content=image_bytes)

            # Perform text detection
            response = client.text_detection(image=vision_image)

            if response.error.message:
                logger.error(f"Google Vision API error: {response.error.message}")
                return OCRResult(
                    text="",
                    confidence=0.0,
                    raw_data={"error": response.error.message},
                )

            # Extract text from response
            texts = response.text_annotations
            if not texts:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    raw_data={"message": "No text detected"},
                )

            # First annotation contains the full text
            full_text = texts[0].description.strip()

            # Calculate confidence from individual text blocks
            # Google Vision provides confidence per symbol in full_text_annotation
            confidence = self._calculate_confidence(response)

            logger.debug(f"Google Vision extracted {len(full_text)} chars, confidence: {confidence:.2f}")

            return OCRResult(
                text=full_text,
                confidence=confidence,
                raw_data={
                    "text_annotations_count": len(texts),
                    "provider": "google_vision",
                },
            )

        except Exception as e:
            logger.exception(f"Google Vision OCR failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                raw_data={"error": str(e)},
            )

    def _calculate_confidence(self, response) -> float:
        """Calculate average confidence from Vision API response.

        Args:
            response: Google Vision API response.

        Returns:
            Average confidence score (0-1).
        """
        try:
            # Try to get confidence from full_text_annotation
            if not response.full_text_annotation:
                return 0.9  # Default high confidence if not available

            confidences = []
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    if block.confidence:
                        confidences.append(block.confidence)

            if confidences:
                return sum(confidences) / len(confidences)

            return 0.9  # Default high confidence for Vision API

        except Exception:
            return 0.9  # Default high confidence

    def extract_mrz(self, image: np.ndarray | Image.Image) -> OCRResult:
        """Extract MRZ text from passport image.

        Google Vision API handles MRZ well without special configuration,
        so this is just an alias for extract_text.

        Args:
            image: Preprocessed MRZ region image.

        Returns:
            OCRResult with extracted MRZ text and confidence.
        """
        return self.extract_text(image)
