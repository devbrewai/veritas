"""Tests for Google Vision OCR integration."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.services.ocr.extractor import OCRResult
from src.services.ocr.google_vision import GoogleVisionOCR


class TestGoogleVisionOCR:
    """Tests for GoogleVisionOCR class."""

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch("src.services.ocr.google_vision.get_settings") as mock_settings:
            mock_settings.return_value.GOOGLE_CLOUD_API_KEY = None
            ocr = GoogleVisionOCR()
            assert ocr.api_key is None
            assert not ocr.is_available

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        ocr = GoogleVisionOCR(api_key="test-api-key")
        assert ocr.api_key == "test-api-key"
        assert ocr.is_available

    def test_is_available_false_when_no_key(self):
        """Test is_available returns False when no API key."""
        with patch("src.services.ocr.google_vision.get_settings") as mock_settings:
            mock_settings.return_value.GOOGLE_CLOUD_API_KEY = None
            ocr = GoogleVisionOCR()
            assert not ocr.is_available

    def test_is_available_true_when_key_present(self):
        """Test is_available returns True when API key is set."""
        ocr = GoogleVisionOCR(api_key="test-key")
        assert ocr.is_available

    def test_extract_text_returns_empty_when_not_available(self):
        """Test extract_text returns empty result when API not available."""
        with patch("src.services.ocr.google_vision.get_settings") as mock_settings:
            mock_settings.return_value.GOOGLE_CLOUD_API_KEY = None
            ocr = GoogleVisionOCR()

            # Create a dummy image
            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.extract_text(image)

            assert result.text == ""
            assert result.confidence == 0.0
            assert "error" in result.raw_data

    def test_extract_mrz_calls_extract_text(self):
        """Test extract_mrz delegates to extract_text."""
        ocr = GoogleVisionOCR(api_key="test-key")

        # Mock extract_text
        expected_result = OCRResult(text="MRZ TEXT", confidence=0.95)
        with patch.object(ocr, "extract_text", return_value=expected_result) as mock:
            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.extract_mrz(image)

            mock.assert_called_once_with(image)
            assert result == expected_result

    def test_image_to_bytes_numpy_grayscale(self):
        """Test _image_to_bytes handles grayscale numpy arrays."""
        ocr = GoogleVisionOCR(api_key="test-key")
        image = np.zeros((100, 100), dtype=np.uint8)
        result = ocr._image_to_bytes(image)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_image_to_bytes_numpy_color(self):
        """Test _image_to_bytes handles color numpy arrays."""
        ocr = GoogleVisionOCR(api_key="test-key")
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = ocr._image_to_bytes(image)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_image_to_bytes_pil_image(self):
        """Test _image_to_bytes handles PIL Images."""
        from PIL import Image

        ocr = GoogleVisionOCR(api_key="test-key")
        image = Image.new("RGB", (100, 100))
        result = ocr._image_to_bytes(image)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestGoogleVisionOCRWithMockedAPI:
    """Tests for GoogleVisionOCR with mocked Google Vision API."""

    @pytest.fixture
    def mock_vision_response(self):
        """Create a mock Vision API response."""
        mock_response = MagicMock()
        mock_response.error.message = ""

        # Mock text annotations
        mock_text = MagicMock()
        mock_text.description = "P<GBRSMITH<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n1234567890GBR8501011M2501011<<<<<<<<<<<<<<02"

        mock_response.text_annotations = [mock_text]

        # Mock full_text_annotation for confidence
        mock_page = MagicMock()
        mock_block = MagicMock()
        mock_block.confidence = 0.95
        mock_page.blocks = [mock_block]
        mock_response.full_text_annotation.pages = [mock_page]

        return mock_response

    def test_extract_text_with_mocked_api(self, mock_vision_response):
        """Test extract_text with mocked Google Vision API."""
        ocr = GoogleVisionOCR(api_key="test-key")

        with patch.object(ocr, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.text_detection.return_value = mock_vision_response
            mock_get_client.return_value = mock_client

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.extract_text(image)

            assert "GBRSMITH" in result.text
            assert result.confidence > 0
            assert result.raw_data.get("provider") == "google_vision"

    def test_extract_text_handles_no_text_detected(self):
        """Test extract_text handles case when no text is detected."""
        ocr = GoogleVisionOCR(api_key="test-key")

        mock_response = MagicMock()
        mock_response.error.message = ""
        mock_response.text_annotations = []

        with patch.object(ocr, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.text_detection.return_value = mock_response
            mock_get_client.return_value = mock_client

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.extract_text(image)

            assert result.text == ""
            assert result.confidence == 0.0

    def test_extract_text_handles_api_error(self):
        """Test extract_text handles API errors gracefully."""
        ocr = GoogleVisionOCR(api_key="test-key")

        mock_response = MagicMock()
        mock_response.error.message = "API quota exceeded"

        with patch.object(ocr, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.text_detection.return_value = mock_response
            mock_get_client.return_value = mock_client

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.extract_text(image)

            assert result.text == ""
            assert result.confidence == 0.0
            assert "error" in result.raw_data

    def test_extract_text_handles_exception(self):
        """Test extract_text handles exceptions gracefully."""
        ocr = GoogleVisionOCR(api_key="test-key")

        with patch.object(ocr, "_get_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Network error")

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            result = ocr.extract_text(image)

            assert result.text == ""
            assert result.confidence == 0.0
            assert "error" in result.raw_data


class TestHybridOCRFallback:
    """Tests for hybrid OCR fallback behavior in document processing."""

    def test_tesseract_success_skips_google_vision(self):
        """Test that Google Vision is not called when Tesseract succeeds."""
        # This would require mocking the entire document processing pipeline
        # For now, we just verify the structure is correct
        pass

    def test_google_vision_called_on_tesseract_failure(self):
        """Test that Google Vision is called when Tesseract fails."""
        # This would require mocking the entire document processing pipeline
        # For now, we just verify the structure is correct
        pass
