"""Image preprocessing pipeline for improved OCR accuracy."""

from pathlib import Path

import cv2
import numpy as np


class ImagePreprocessor:
    """Preprocessing pipeline to improve OCR accuracy on document images."""

    @staticmethod
    def load_image(file_path: str | Path) -> np.ndarray:
        """Load image from file path.

        Args:
            file_path: Path to the image file.

        Returns:
            Image as numpy array in BGR format.

        Raises:
            ValueError: If image cannot be loaded.
        """
        image = cv2.imread(str(file_path))
        if image is None:
            raise ValueError(f"Could not load image: {file_path}")
        return image

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale.

        Args:
            image: Input image (BGR or grayscale).

        Returns:
            Grayscale image.
        """
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    @staticmethod
    def denoise(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """Remove noise using median blur.

        Args:
            image: Input grayscale image.
            kernel_size: Size of the median filter kernel (must be odd).

        Returns:
            Denoised image.
        """
        return cv2.medianBlur(image, kernel_size)

    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Input grayscale image.

        Returns:
            Contrast-enhanced image.
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    @staticmethod
    def binarize(image: np.ndarray) -> np.ndarray:
        """Apply Otsu's thresholding for binary image.

        Args:
            image: Input grayscale image.

        Returns:
            Binary image.
        """
        _, binary = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        return binary

    @staticmethod
    def deskew(image: np.ndarray, angle_threshold: float = 0.5) -> np.ndarray:
        """Correct image rotation/skew.

        Args:
            image: Input image.
            angle_threshold: Minimum angle (degrees) to trigger deskewing.

        Returns:
            Deskewed image.
        """
        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 5:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < angle_threshold:
            return image

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        return cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    @staticmethod
    def resize_for_ocr(
        image: np.ndarray,
        target_dpi: int = 300,
        current_dpi: int = 72,
    ) -> np.ndarray:
        """Resize image to optimal DPI for OCR (300 DPI recommended).

        Args:
            image: Input image.
            target_dpi: Target DPI for OCR.
            current_dpi: Estimated current DPI of the image.

        Returns:
            Resized image.
        """
        if current_dpi >= target_dpi:
            return image

        scale = target_dpi / current_dpi
        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)

        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    def preprocess_for_ocr(
        self,
        image: np.ndarray,
        apply_deskew: bool = True,
    ) -> np.ndarray:
        """Full preprocessing pipeline for OCR.

        Args:
            image: Input image (BGR format).
            apply_deskew: Whether to apply deskewing.

        Returns:
            Preprocessed binary image optimized for OCR.
        """
        gray = self.to_grayscale(image)
        denoised = self.denoise(gray)
        enhanced = self.enhance_contrast(denoised)
        binary = self.binarize(enhanced)

        if apply_deskew:
            binary = self.deskew(binary)

        return binary

    def preprocess_for_mrz(self, image: np.ndarray) -> np.ndarray:
        """Preprocessing specifically optimized for MRZ region.

        MRZ uses OCR-B font which is designed for machine reading,
        so we use lighter preprocessing to preserve character shapes.

        Args:
            image: Input image (BGR or grayscale).

        Returns:
            Preprocessed image optimized for MRZ OCR.
        """
        gray = self.to_grayscale(image)

        # Lighter denoising for MRZ
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)

        # Adaptive thresholding works better for MRZ
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        return binary
