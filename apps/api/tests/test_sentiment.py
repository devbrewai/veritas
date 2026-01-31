"""Tests for VADER sentiment analyzer."""

import pytest

from src.schemas.adverse_media import SentimentCategory
from src.services.adverse_media.sentiment import SentimentAnalyzer


class TestSentimentAnalyzer:
    """Test cases for SentimentAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> SentimentAnalyzer:
        """Create a sentiment analyzer instance."""
        return SentimentAnalyzer()

    def test_negative_sentiment_fraud(self, analyzer: SentimentAnalyzer) -> None:
        """Test that fraud-related text is classified as negative."""
        text = "CEO arrested for fraud and money laundering scheme"
        score, category = analyzer.analyze(text)

        assert score < analyzer.NEGATIVE_THRESHOLD
        assert category == SentimentCategory.NEGATIVE

    def test_negative_sentiment_scandal(self, analyzer: SentimentAnalyzer) -> None:
        """Test that scandal text is classified as negative."""
        text = "Company faces massive scandal over corruption allegations"
        score, category = analyzer.analyze(text)

        assert score < analyzer.NEGATIVE_THRESHOLD
        assert category == SentimentCategory.NEGATIVE

    def test_positive_sentiment(self, analyzer: SentimentAnalyzer) -> None:
        """Test that positive text is classified correctly."""
        text = "Company wins prestigious award for excellence and innovation"
        score, category = analyzer.analyze(text)

        assert score > analyzer.POSITIVE_THRESHOLD
        assert category == SentimentCategory.POSITIVE

    def test_neutral_sentiment(self, analyzer: SentimentAnalyzer) -> None:
        """Test that neutral text is classified correctly."""
        text = "The quarterly meeting was held on Tuesday"
        score, category = analyzer.analyze(text)

        assert analyzer.NEGATIVE_THRESHOLD < score < analyzer.POSITIVE_THRESHOLD
        assert category == SentimentCategory.NEUTRAL

    def test_empty_text_returns_neutral(self, analyzer: SentimentAnalyzer) -> None:
        """Test that empty text returns neutral sentiment."""
        score, category = analyzer.analyze("")
        assert score == 0.0
        assert category == SentimentCategory.NEUTRAL

        score2, category2 = analyzer.analyze("   ")
        assert score2 == 0.0
        assert category2 == SentimentCategory.NEUTRAL

    def test_batch_analyze(self, analyzer: SentimentAnalyzer) -> None:
        """Test batch analysis of multiple texts."""
        texts = [
            "Great success story",
            "Terrible fraud case",
            "Meeting scheduled for Monday",
        ]
        results = analyzer.batch_analyze(texts)

        assert len(results) == 3
        assert results[0][1] == SentimentCategory.POSITIVE
        assert results[1][1] == SentimentCategory.NEGATIVE
        assert results[2][1] == SentimentCategory.NEUTRAL

    def test_get_negative_count(self, analyzer: SentimentAnalyzer) -> None:
        """Test counting negative sentiment texts."""
        texts = [
            "Criminal charges filed against executive",
            "Fraud investigation ongoing",
            "Company announces new product",
            "Stock price rises",
        ]
        count = analyzer.get_negative_count(texts)

        # First two should be negative
        assert count == 2

    def test_get_average_sentiment(self, analyzer: SentimentAnalyzer) -> None:
        """Test average sentiment calculation."""
        texts = [
            "Excellent performance and growth",
            "Terrible scandal rocks company",
        ]
        avg = analyzer.get_average_sentiment(texts)

        # Should be somewhere in the middle
        assert -1.0 <= avg <= 1.0

    def test_get_average_sentiment_empty_list(
        self, analyzer: SentimentAnalyzer
    ) -> None:
        """Test average sentiment with empty list."""
        avg = analyzer.get_average_sentiment([])
        assert avg == 0.0

    def test_kyc_relevant_negative_terms(self, analyzer: SentimentAnalyzer) -> None:
        """Test KYC/AML relevant negative terms are detected."""
        negative_texts = [
            "Individual sanctioned by OFAC for terrorism financing",
            "Bank fined for money laundering violations",
            "Executive indicted on bribery charges",
            "Massive fraud scandal exposed at company",
        ]

        for text in negative_texts:
            score, category = analyzer.analyze(text)
            assert category == SentimentCategory.NEGATIVE, f"Expected negative for: {text}"
