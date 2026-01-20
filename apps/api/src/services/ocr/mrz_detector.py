"""MRZ (Machine Readable Zone) detection in passport images."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class MRZRegion:
    """Detected MRZ region with bounding box and cropped image."""

    x: int
    y: int
    width: int
    height: int
    image: np.ndarray


class MRZDetector:
    """Detects Machine Readable Zone in passport/ID images.

    Uses morphological operations to locate the MRZ region which typically
    appears at the bottom of passport pages with characteristic dense text.
    """

    def __init__(
        self,
        rect_kernel_size: tuple[int, int] = (25, 7),
        sq_kernel_size: tuple[int, int] = (21, 21),
    ):
        """Initialize MRZ detector.

        Args:
            rect_kernel_size: Kernel size for horizontal morphological operations.
            sq_kernel_size: Kernel size for square morphological operations.
        """
        self.rect_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            rect_kernel_size,
        )
        self.sq_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            sq_kernel_size,
        )

    def detect(self, image: np.ndarray) -> MRZRegion | None:
        """Detect MRZ region in passport image.

        Args:
            image: Input image (BGR or grayscale).

        Returns:
            MRZRegion with bounding box and cropped image, or None if not found.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Blackhat morphological operation reveals dark text on light background
        blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, self.rect_kernel)

        # Compute Scharr gradient in x-direction (horizontal edges)
        grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        grad_x = np.absolute(grad_x)

        # Normalize gradient to 0-255
        min_val, max_val = grad_x.min(), grad_x.max()
        if max_val - min_val > 0:
            grad_x = (255 * ((grad_x - min_val) / (max_val - min_val))).astype("uint8")
        else:
            grad_x = np.zeros_like(grad_x, dtype="uint8")

        # Close gaps between characters using rectangular kernel
        grad_x = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, self.rect_kernel)

        # Apply Otsu's thresholding
        _, thresh = cv2.threshold(
            grad_x,
            0,
            255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU,
        )

        # Close gaps between MRZ lines using square kernel
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, self.sq_kernel)

        # Erode to separate different text regions
        thresh = cv2.erode(thresh, None, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(
            thresh.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return None

        h, w = image.shape[:2]

        # Filter contours to find MRZ region
        # MRZ should be >75% width and located in lower portion of image
        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            x, y, cw, ch = cv2.boundingRect(contour)

            # MRZ typically spans most of the document width
            width_ratio = cw / w
            # MRZ is usually in the lower 40% of the document
            y_position_ratio = y / h

            if width_ratio > 0.7 and y_position_ratio > 0.5:
                # Add padding - more vertical padding to capture both MRZ lines
                # MRZ has 2 lines, detection often only finds one
                pad_x = int(w * 0.03)
                pad_y = int(h * 0.08)  # 8% vertical padding to capture both lines

                x = max(0, x - pad_x)
                y = max(0, y - pad_y)
                cw = min(w - x, cw + 2 * pad_x)
                ch = min(h - y, ch + 2 * pad_y)

                mrz_image = image[y : y + ch, x : x + cw]

                return MRZRegion(
                    x=x,
                    y=y,
                    width=cw,
                    height=ch,
                    image=mrz_image,
                )

        # Fallback: try to find any wide region in lower portion
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
            x, y, cw, ch = cv2.boundingRect(contour)

            width_ratio = cw / w
            if width_ratio > 0.5:
                pad_x = int(w * 0.03)
                pad_y = int(h * 0.08)

                x = max(0, x - pad_x)
                y = max(0, y - pad_y)
                cw = min(w - x, cw + 2 * pad_x)
                ch = min(h - y, ch + 2 * pad_y)

                mrz_image = image[y : y + ch, x : x + cw]

                return MRZRegion(
                    x=x,
                    y=y,
                    width=cw,
                    height=ch,
                    image=mrz_image,
                )

        return None

    def detect_with_fallback(
        self,
        image: np.ndarray,
        bottom_percentage: float = 0.35,
    ) -> MRZRegion:
        """Detect MRZ with fallback to bottom portion of image.

        Args:
            image: Input image.
            bottom_percentage: Percentage of image height to use as fallback.

        Returns:
            MRZRegion from detection or fallback to bottom portion.
        """
        result = self.detect(image)
        if result is not None:
            return result

        # Fallback: return bottom portion of image
        h, w = image.shape[:2]
        y = int(h * (1 - bottom_percentage))
        mrz_image = image[y:h, 0:w]

        return MRZRegion(
            x=0,
            y=y,
            width=w,
            height=h - y,
            image=mrz_image,
        )
