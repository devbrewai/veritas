"""Tesseract OCR wrapper with MRZ-optimized configuration."""

from dataclasses import dataclass

import numpy as np
import pytesseract
from PIL import Image

from src.config import get_settings


@dataclass
class OCRResult:
    """OCR extraction result with text and confidence."""

    text: str
    confidence: float
    raw_data: dict | None = None


class OCRExtractor:
    """Tesseract OCR wrapper optimized for document and MRZ extraction."""

    # MRZ character whitelist (uppercase letters, digits, and filler character)
    MRZ_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

    def __init__(self):
        """Initialize OCR extractor with optional custom Tesseract path."""
        settings = get_settings()
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def _to_pil_image(self, image: np.ndarray | Image.Image) -> Image.Image:
        """Convert numpy array to PIL Image if needed."""
        if isinstance(image, np.ndarray):
            return Image.fromarray(image)
        return image

    def extract_text(
        self,
        image: np.ndarray | Image.Image,
        config: str = "",
    ) -> OCRResult:
        """Extract text from image using Tesseract.

        Args:
            image: Input image (numpy array or PIL Image).
            config: Additional Tesseract configuration string.

        Returns:
            OCRResult with extracted text and confidence score.
        """
        pil_image = self._to_pil_image(image)

        # Get detailed data including confidence scores
        try:
            data = pytesseract.image_to_data(
                pil_image,
                config=config,
                output_type=pytesseract.Output.DICT,
            )

            # Calculate average confidence (excluding empty/low-conf results)
            confidences = [
                int(c)
                for c, t in zip(data["conf"], data["text"])
                if int(c) > 0 and t.strip()
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Get full text
            text = pytesseract.image_to_string(pil_image, config=config)

            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence / 100,  # Normalize to 0-1
                raw_data=data,
            )
        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                raw_data={"error": str(e)},
            )

    def extract_mrz(self, image: np.ndarray | Image.Image) -> OCRResult:
        """Extract MRZ text with optimized configuration.

        Uses Tesseract PSM 6 (single uniform block) and character whitelist
        restricted to valid MRZ characters.

        Args:
            image: Preprocessed MRZ region image.

        Returns:
            OCRResult with extracted MRZ text and confidence.
        """
        # MRZ-specific Tesseract configuration
        # PSM 6: Assume a single uniform block of text
        # OEM 3: Default OCR Engine Mode
        mrz_config = (
            "--psm 6 "
            "--oem 3 "
            f"-c tessedit_char_whitelist={self.MRZ_WHITELIST}"
        )

        return self.extract_text(image, config=mrz_config)

    def extract_document_text(self, image: np.ndarray | Image.Image) -> OCRResult:
        """Extract text from general document (not MRZ).

        Uses PSM 3 for automatic page segmentation.

        Args:
            image: Document image.

        Returns:
            OCRResult with extracted text and confidence.
        """
        # PSM 3: Fully automatic page segmentation (default)
        config = "--psm 3 --oem 3"
        return self.extract_text(image, config=config)

    def get_text_regions(
        self,
        image: np.ndarray | Image.Image,
    ) -> list[dict]:
        """Get individual text regions with bounding boxes.

        Args:
            image: Input image.

        Returns:
            List of dicts with text, confidence, and bounding box info.
        """
        pil_image = self._to_pil_image(image)

        try:
            data = pytesseract.image_to_data(
                pil_image,
                output_type=pytesseract.Output.DICT,
            )

            regions = []
            for i, text in enumerate(data["text"]):
                if text.strip() and int(data["conf"][i]) > 0:
                    regions.append(
                        {
                            "text": text,
                            "confidence": int(data["conf"][i]) / 100,
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                            "level": data["level"][i],
                        }
                    )

            return regions
        except Exception:
            return []
