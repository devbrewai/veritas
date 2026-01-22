"""Document quality assessment for OCR processing."""

import cv2
import numpy as np


class DocumentQualityChecker:
    """Assesses document image quality before OCR processing.

    Checks for common issues that affect OCR accuracy:
    - Low resolution
    - Poor brightness (too dark or overexposed)
    - Low contrast
    - Blurriness

    Returns actionable suggestions for improving scan quality.
    """

    def __init__(
        self,
        min_resolution: tuple[int, int] = (300, 400),
        min_brightness: float = 30.0,
        max_brightness: float = 220.0,
        min_contrast: float = 20.0,
        blur_threshold: float = 100.0,
    ):
        """Initialize quality checker with thresholds.

        Args:
            min_resolution: Minimum (width, height) in pixels.
            min_brightness: Minimum average brightness (0-255).
            max_brightness: Maximum average brightness (0-255).
            min_contrast: Minimum standard deviation of pixel values.
            blur_threshold: Minimum Laplacian variance for sharpness.
        """
        self.min_resolution = min_resolution
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast
        self.blur_threshold = blur_threshold

    def check_quality(self, image: np.ndarray) -> dict:
        """Assess image quality and return detailed report.

        Args:
            image: Input image as numpy array (BGR or grayscale).

        Returns:
            Dict with:
                - is_acceptable: bool - Whether image passes quality checks
                - score: float - Overall quality score (0-1)
                - issues: list[str] - List of identified issues
                - suggestions: list[str] - Actionable suggestions
                - metrics: dict - Detailed quality metrics
        """
        if image is None or image.size == 0:
            return {
                "is_acceptable": False,
                "score": 0.0,
                "issues": ["Invalid or empty image"],
                "suggestions": ["Please upload a valid image file"],
                "metrics": {},
            }

        issues: list[str] = []
        suggestions: list[str] = []
        scores: list[float] = []

        # Get image dimensions
        h, w = image.shape[:2]

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Check resolution
        resolution_score = self._check_resolution(w, h, issues, suggestions)
        scores.append(resolution_score)

        # Check brightness
        brightness = np.mean(gray)
        brightness_score = self._check_brightness(brightness, issues, suggestions)
        scores.append(brightness_score)

        # Check contrast
        contrast = np.std(gray)
        contrast_score = self._check_contrast(contrast, issues, suggestions)
        scores.append(contrast_score)

        # Check blur/sharpness
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = self._check_sharpness(sharpness, issues, suggestions)
        scores.append(sharpness_score)

        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Determine if acceptable (score >= 0.7 and at most 1 critical issue)
        critical_issues = len([s for s in scores if s < 0.6])
        is_acceptable = overall_score >= 0.7 and critical_issues <= 1

        return {
            "is_acceptable": is_acceptable,
            "score": round(overall_score, 2),
            "issues": issues,
            "suggestions": suggestions,
            "metrics": {
                "resolution": f"{w}x{h}",
                "brightness": round(brightness, 1),
                "contrast": round(contrast, 1),
                "sharpness": round(sharpness, 1),
            },
        }

    def _check_resolution(
        self, width: int, height: int, issues: list[str], suggestions: list[str]
    ) -> float:
        """Check image resolution."""
        min_w, min_h = self.min_resolution

        if width < min_w or height < min_h:
            issues.append(f"Image resolution too low ({width}x{height})")
            suggestions.append(
                f"Upload a higher resolution scan (minimum {min_w}x{min_h} pixels)"
            )
            # Score based on how close to minimum
            ratio = min(width / min_w, height / min_h)
            return min(ratio, 1.0) * 0.5 + 0.2  # 0.2-0.7 range for low res

        # Give bonus for higher resolution
        if width >= min_w * 2 and height >= min_h * 2:
            return 1.0
        return 0.85

    def _check_brightness(
        self, brightness: float, issues: list[str], suggestions: list[str]
    ) -> float:
        """Check image brightness."""
        if brightness < self.min_brightness:
            issues.append("Image too dark")
            suggestions.append("Ensure adequate lighting when scanning the document")
            return 0.5

        if brightness > self.max_brightness:
            issues.append("Image overexposed/washed out")
            suggestions.append("Reduce lighting or adjust scanner/camera settings")
            return 0.5

        # Ideal brightness is around 120-180
        ideal_range = (120, 180)
        if ideal_range[0] <= brightness <= ideal_range[1]:
            return 1.0
        return 0.8

    def _check_contrast(
        self, contrast: float, issues: list[str], suggestions: list[str]
    ) -> float:
        """Check image contrast."""
        if contrast < self.min_contrast:
            issues.append("Low contrast - text may be hard to distinguish")
            suggestions.append(
                "Use a document with clearer text or increase scanner contrast"
            )
            return 0.6

        # Good contrast is typically 40-80
        if contrast >= 40:
            return 1.0
        return 0.8

    def _check_sharpness(
        self, sharpness: float, issues: list[str], suggestions: list[str]
    ) -> float:
        """Check image sharpness (blur detection)."""
        if sharpness < self.blur_threshold:
            issues.append("Image appears blurry")
            suggestions.append(
                "Ensure the document is flat and the camera/scanner is steady"
            )
            # Very blurry
            if sharpness < self.blur_threshold * 0.5:
                return 0.3
            return 0.5

        # Sharp images have high Laplacian variance
        if sharpness >= self.blur_threshold * 2:
            return 1.0
        return 0.85

    def get_quality_summary(self, quality_result: dict) -> str:
        """Generate a human-readable quality summary.

        Args:
            quality_result: Result from check_quality().

        Returns:
            Human-readable summary string.
        """
        if quality_result["is_acceptable"]:
            return f"Image quality: Good (score: {quality_result['score']})"

        summary_parts = [
            f"Image quality: Poor (score: {quality_result['score']})",
            "Issues found:",
        ]
        for issue in quality_result["issues"]:
            summary_parts.append(f"  - {issue}")

        if quality_result["suggestions"]:
            summary_parts.append("Suggestions:")
            for suggestion in quality_result["suggestions"]:
                summary_parts.append(f"  - {suggestion}")

        return "\n".join(summary_parts)
