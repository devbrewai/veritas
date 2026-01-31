"""VADER sentiment analysis wrapper for adverse media articles."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.schemas.adverse_media import SentimentCategory


class SentimentAnalyzer:
    """Wrapper for VADER sentiment analysis.

    VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon
    and rule-based sentiment analysis tool specifically attuned to
    sentiments expressed in social media and news.
    """

    # Thresholds for sentiment classification
    NEGATIVE_THRESHOLD = -0.05
    POSITIVE_THRESHOLD = 0.05

    def __init__(self) -> None:
        """Initialize the VADER sentiment analyzer."""
        self._analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> tuple[float, SentimentCategory]:
        """Analyze sentiment of text.

        Args:
            text: The text to analyze (typically article title).

        Returns:
            Tuple of (compound_score, category) where:
            - compound_score: [-1, 1] where -1 is most negative, 1 is most positive
            - category: negative, neutral, or positive classification
        """
        if not text or not text.strip():
            return 0.0, SentimentCategory.NEUTRAL

        scores = self._analyzer.polarity_scores(text)
        compound = scores["compound"]

        if compound <= self.NEGATIVE_THRESHOLD:
            category = SentimentCategory.NEGATIVE
        elif compound >= self.POSITIVE_THRESHOLD:
            category = SentimentCategory.POSITIVE
        else:
            category = SentimentCategory.NEUTRAL

        return compound, category

    def batch_analyze(
        self,
        texts: list[str],
    ) -> list[tuple[float, SentimentCategory]]:
        """Analyze sentiment of multiple texts.

        Args:
            texts: List of texts to analyze.

        Returns:
            List of (compound_score, category) tuples.
        """
        return [self.analyze(text) for text in texts]

    def get_negative_count(self, texts: list[str]) -> int:
        """Count number of texts with negative sentiment.

        Args:
            texts: List of texts to analyze.

        Returns:
            Count of texts classified as negative.
        """
        return sum(
            1 for _, category in self.batch_analyze(texts)
            if category == SentimentCategory.NEGATIVE
        )

    def get_average_sentiment(self, texts: list[str]) -> float:
        """Calculate average sentiment score across texts.

        Args:
            texts: List of texts to analyze.

        Returns:
            Average compound score, or 0.0 if no texts.
        """
        if not texts:
            return 0.0

        scores = [score for score, _ in self.batch_analyze(texts)]
        return sum(scores) / len(scores)
