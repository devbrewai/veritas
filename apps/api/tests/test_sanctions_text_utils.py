"""
Unit tests for sanctions screening text utilities.
"""

import pytest

from src.services.sanctions.text_utils import STOPWORDS, normalize_text, tokenize


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_removes_diacritics(self):
        """Should remove accents and diacritics."""
        assert normalize_text("José María") == "jose maria"
        assert normalize_text("François") == "francois"
        assert normalize_text("Müller") == "muller"
        assert normalize_text("Björk") == "bjork"

    def test_removes_quotes(self):
        """Should remove single and double quotes."""
        assert normalize_text("O'Brien") == "obrien"
        assert normalize_text("McDonald's") == "mcdonalds"
        assert normalize_text('"Quoted"') == "quoted"

    def test_handles_hyphens(self):
        """Should preserve hyphens for tokenization."""
        # Hyphens are preserved in normalization, split during tokenization
        assert normalize_text("AL-QAIDA") == "al-qaida"
        assert normalize_text("Jean-Pierre") == "jean-pierre"

    def test_lowercases_text(self):
        """Should convert to lowercase."""
        assert normalize_text("VLADIMIR PUTIN") == "vladimir putin"
        assert normalize_text("John DOE") == "john doe"

    def test_collapses_whitespace(self):
        """Should collapse multiple spaces to single space."""
        assert normalize_text("John    Doe") == "john doe"
        assert normalize_text("  Name   With   Spaces  ") == "name with spaces"

    def test_handles_non_latin_scripts(self):
        """Should return empty string for non-Latin only text."""
        assert normalize_text("中国工商银行") == ""
        assert normalize_text("محمد") == ""
        assert normalize_text("Владимир") == ""

    def test_handles_mixed_scripts(self):
        """Should keep Latin characters from mixed text."""
        # Non-Latin characters become spaces, then collapse
        result = normalize_text("John 中国 Doe")
        assert "john" in result
        assert "doe" in result

    def test_handles_empty_string(self):
        """Should return empty string for empty input."""
        assert normalize_text("") == ""

    def test_handles_none(self):
        """Should return empty string for None input."""
        assert normalize_text(None) == ""

    def test_handles_whitespace_only(self):
        """Should return empty string for whitespace only."""
        assert normalize_text("   ") == ""
        assert normalize_text("\t\n") == ""

    def test_removes_special_characters(self):
        """Should remove special characters except spaces and hyphens."""
        assert normalize_text("John@Doe.com") == "john doe com"
        assert normalize_text("Test (123)") == "test 123"
        assert normalize_text("$100,000") == "100 000"

    def test_normalizes_unicode(self):
        """Should apply NFKC Unicode normalization."""
        # Full-width characters should be normalized
        assert normalize_text("Ｊｏｈｎ") == "john"


class TestTokenize:
    """Tests for tokenize function."""

    def test_splits_on_whitespace(self):
        """Should split on whitespace."""
        assert tokenize("john doe") == ["john", "doe"]
        assert tokenize("john doe smith") == ["john", "doe", "smith"]

    def test_splits_on_hyphens(self):
        """Should split on hyphens."""
        assert tokenize("al qaida") == ["al", "qaida"]
        assert tokenize("jean-pierre") == ["jean", "pierre"]

    def test_removes_stopwords(self):
        """Should remove business suffixes and common words."""
        assert tokenize("acme corporation ltd") == ["acme"]
        assert tokenize("john smith inc") == ["john", "smith"]
        assert tokenize("the company of america") == ["america"]

    def test_removes_short_tokens(self):
        """Should remove tokens shorter than 2 characters."""
        assert tokenize("a b john doe") == ["john", "doe"]
        assert tokenize("x y z") == []

    def test_handles_empty_string(self):
        """Should return empty list for empty input."""
        assert tokenize("") == []

    def test_handles_stopwords_only(self):
        """Should return empty list if only stopwords."""
        assert tokenize("the of and") == []
        assert tokenize("ltd inc co") == []

    def test_preserves_significant_tokens(self):
        """Should preserve meaningful name tokens."""
        assert tokenize("vladimir putin") == ["vladimir", "putin"]
        assert tokenize("kim jong un") == ["kim", "jong", "un"]

    def test_handles_honorifics(self):
        """Should remove honorifics."""
        assert tokenize("mr john smith") == ["john", "smith"]
        assert tokenize("dr jane doe") == ["jane", "doe"]

    def test_handles_mixed_content(self):
        """Should handle mix of stopwords and real tokens."""
        assert tokenize("bank of america ltd") == ["bank", "america"]
        assert tokenize("the first national corp") == ["first", "national"]


class TestStopwords:
    """Tests for STOPWORDS constant."""

    def test_contains_business_suffixes(self):
        """Should include common business suffixes."""
        assert "ltd" in STOPWORDS
        assert "inc" in STOPWORDS
        assert "llc" in STOPWORDS
        assert "corp" in STOPWORDS
        assert "gmbh" in STOPWORDS

    def test_contains_honorifics(self):
        """Should include common honorifics."""
        assert "mr" in STOPWORDS
        assert "mrs" in STOPWORDS
        assert "dr" in STOPWORDS

    def test_contains_common_words(self):
        """Should include common connector words."""
        assert "the" in STOPWORDS
        assert "of" in STOPWORDS
        assert "and" in STOPWORDS


class TestIntegration:
    """Integration tests combining normalize_text and tokenize."""

    def test_full_pipeline_simple_name(self):
        """Test full pipeline with simple name."""
        raw = "JOHN DOE"
        normalized = normalize_text(raw)
        tokens = tokenize(normalized)
        assert tokens == ["john", "doe"]

    def test_full_pipeline_with_diacritics(self):
        """Test full pipeline with diacritics."""
        raw = "José María García"
        normalized = normalize_text(raw)
        tokens = tokenize(normalized)
        assert tokens == ["jose", "maria", "garcia"]

    def test_full_pipeline_company_name(self):
        """Test full pipeline with company name."""
        raw = "Acme Corporation Ltd."
        normalized = normalize_text(raw)
        tokens = tokenize(normalized)
        assert tokens == ["acme"]

    def test_full_pipeline_with_quotes(self):
        """Test full pipeline with quotes and apostrophes."""
        raw = "O'Brien & Sons, Inc."
        normalized = normalize_text(raw)
        tokens = tokenize(normalized)
        assert "obrien" in tokens
        assert "sons" in tokens

    def test_full_pipeline_hyphenated_name(self):
        """Test full pipeline with hyphenated name."""
        raw = "Jean-Pierre de la Croix"
        normalized = normalize_text(raw)
        tokens = tokenize(normalized)
        assert "jean" in tokens
        assert "pierre" in tokens
        assert "croix" in tokens
        # "de" and "la" should be filtered as stopwords
        assert "de" not in tokens
        assert "la" not in tokens
