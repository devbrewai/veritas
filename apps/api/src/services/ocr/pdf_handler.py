"""PDF handling utilities for document processing."""

from pathlib import Path

import numpy as np
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError


class PDFHandler:
    """Handles PDF to image conversion for OCR processing."""

    SUPPORTED_EXTENSIONS = {".pdf"}

    def __init__(self, dpi: int = 300):
        """Initialize PDF handler.

        Args:
            dpi: Resolution for PDF to image conversion. Higher DPI = better OCR but slower.
        """
        self.dpi = dpi

    def is_pdf(self, file_path: Path | str) -> bool:
        """Check if file is a PDF based on extension.

        Args:
            file_path: Path to the file.

        Returns:
            True if file has .pdf extension.
        """
        path = Path(file_path)
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def pdf_to_images(self, file_path: Path | str) -> list[np.ndarray]:
        """Convert all PDF pages to numpy arrays.

        Args:
            file_path: Path to PDF file.

        Returns:
            List of numpy arrays (BGR format for OpenCV compatibility) for each page.

        Raises:
            PDFPageCountError: If PDF has no pages.
            PDFSyntaxError: If PDF is malformed.
            FileNotFoundError: If file doesn't exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        pil_images = convert_from_path(str(path), dpi=self.dpi)

        images = []
        for pil_img in pil_images:
            # Convert PIL Image to numpy array (RGB)
            np_img = np.array(pil_img)
            # Convert RGB to BGR for OpenCV compatibility
            if len(np_img.shape) == 3 and np_img.shape[2] == 3:
                np_img = np_img[:, :, ::-1].copy()
            images.append(np_img)

        return images

    def get_first_page(self, file_path: Path | str) -> np.ndarray | None:
        """Get first page of PDF as numpy array.

        This is optimized for single-page documents (utility bills, certificates).

        Args:
            file_path: Path to PDF file.

        Returns:
            Numpy array (BGR format) of first page, or None if conversion fails.
        """
        try:
            images = self.pdf_to_images(file_path)
            return images[0] if images else None
        except (PDFPageCountError, PDFSyntaxError, FileNotFoundError):
            return None

    def get_page_count(self, file_path: Path | str) -> int:
        """Get number of pages in PDF.

        Args:
            file_path: Path to PDF file.

        Returns:
            Number of pages, or 0 if file cannot be read.
        """
        try:
            # Use first_page_only=False but only count
            images = convert_from_path(str(file_path), dpi=72, first_page=1, last_page=1)
            # Get actual count by checking PDF info
            from pdf2image.pdf2image import pdfinfo_from_path

            info = pdfinfo_from_path(str(file_path))
            return info.get("Pages", 0)
        except Exception:
            return 0
