"""Tests for risk feature engineering."""

import pytest

from src.services.risk.features import (
    FEATURE_NAMES,
    RiskFeatures,
    get_country_risk,
    normalize_adverse_media_count,
    normalize_document_age,
)


class TestRiskFeatures:
    """Test cases for RiskFeatures dataclass."""

    def test_valid_features(self) -> None:
        """Test creating features with valid values."""
        features = RiskFeatures(
            document_quality=0.95,
            sanctions_score=0.1,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.1,
            document_age_days=30,
        )
        assert features.document_quality == 0.95
        assert features.sanctions_match == 0

    def test_to_array(self) -> None:
        """Test conversion to array."""
        features = RiskFeatures(
            document_quality=0.95,
            sanctions_score=0.1,
            sanctions_match=0,
            adverse_media_count=2,
            adverse_media_sentiment=-0.5,
            country_risk=0.1,
            document_age_days=30,
        )
        arr = features.to_array()

        assert len(arr) == len(FEATURE_NAMES)
        assert arr[0] == 0.95  # document_quality
        assert arr[1] == 0.1  # sanctions_score
        assert arr[2] == 0.0  # sanctions_match (converted to float)
        assert arr[3] == 2.0  # adverse_media_count
        assert arr[4] == -0.5  # adverse_media_sentiment
        assert arr[5] == 0.1  # country_risk
        assert arr[6] == 30.0  # document_age_days

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        features = RiskFeatures(
            document_quality=0.95,
            sanctions_score=0.1,
            sanctions_match=1,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.1,
            document_age_days=30,
        )
        d = features.to_dict()

        assert d["document_quality"] == 0.95
        assert d["sanctions_score"] == 0.1
        assert d["sanctions_match"] == 1.0
        assert "country_risk" in d
        assert len(d) == len(FEATURE_NAMES)

    def test_invalid_document_quality(self) -> None:
        """Test validation of document_quality bounds."""
        with pytest.raises(ValueError, match="document_quality"):
            RiskFeatures(
                document_quality=1.5,  # Invalid
                sanctions_score=0.1,
                sanctions_match=0,
                adverse_media_count=0,
                adverse_media_sentiment=0.0,
                country_risk=0.1,
                document_age_days=30,
            )

    def test_invalid_sanctions_score(self) -> None:
        """Test validation of sanctions_score bounds."""
        with pytest.raises(ValueError, match="sanctions_score"):
            RiskFeatures(
                document_quality=0.9,
                sanctions_score=-0.1,  # Invalid
                sanctions_match=0,
                adverse_media_count=0,
                adverse_media_sentiment=0.0,
                country_risk=0.1,
                document_age_days=30,
            )

    def test_invalid_sanctions_match(self) -> None:
        """Test validation of sanctions_match."""
        with pytest.raises(ValueError, match="sanctions_match"):
            RiskFeatures(
                document_quality=0.9,
                sanctions_score=0.1,
                sanctions_match=2,  # Invalid
                adverse_media_count=0,
                adverse_media_sentiment=0.0,
                country_risk=0.1,
                document_age_days=30,
            )

    def test_invalid_adverse_media_count(self) -> None:
        """Test validation of adverse_media_count."""
        with pytest.raises(ValueError, match="adverse_media_count"):
            RiskFeatures(
                document_quality=0.9,
                sanctions_score=0.1,
                sanctions_match=0,
                adverse_media_count=-1,  # Invalid
                adverse_media_sentiment=0.0,
                country_risk=0.1,
                document_age_days=30,
            )

    def test_invalid_adverse_media_sentiment(self) -> None:
        """Test validation of adverse_media_sentiment bounds."""
        with pytest.raises(ValueError, match="adverse_media_sentiment"):
            RiskFeatures(
                document_quality=0.9,
                sanctions_score=0.1,
                sanctions_match=0,
                adverse_media_count=0,
                adverse_media_sentiment=1.5,  # Invalid
                country_risk=0.1,
                document_age_days=30,
            )

    def test_invalid_country_risk(self) -> None:
        """Test validation of country_risk bounds."""
        with pytest.raises(ValueError, match="country_risk"):
            RiskFeatures(
                document_quality=0.9,
                sanctions_score=0.1,
                sanctions_match=0,
                adverse_media_count=0,
                adverse_media_sentiment=0.0,
                country_risk=1.5,  # Invalid
                document_age_days=30,
            )

    def test_invalid_document_age_days(self) -> None:
        """Test validation of document_age_days."""
        with pytest.raises(ValueError, match="document_age_days"):
            RiskFeatures(
                document_quality=0.9,
                sanctions_score=0.1,
                sanctions_match=0,
                adverse_media_count=0,
                adverse_media_sentiment=0.0,
                country_risk=0.1,
                document_age_days=-1,  # Invalid
            )


class TestCountryRisk:
    """Test cases for country risk scoring."""

    def test_low_risk_countries_alpha2(self) -> None:
        """Test low-risk countries with alpha-2 codes."""
        assert get_country_risk("US") == 0.10
        assert get_country_risk("GB") == 0.10
        assert get_country_risk("DE") == 0.10
        assert get_country_risk("SG") == 0.10

    def test_low_risk_countries_alpha3(self) -> None:
        """Test low-risk countries with alpha-3 codes."""
        assert get_country_risk("USA") == 0.10
        assert get_country_risk("GBR") == 0.10
        assert get_country_risk("DEU") == 0.10

    def test_high_risk_countries(self) -> None:
        """Test high-risk countries."""
        assert get_country_risk("IR") == 0.95
        assert get_country_risk("IRN") == 0.95
        assert get_country_risk("KP") == 0.99
        assert get_country_risk("PRK") == 0.99
        assert get_country_risk("SY") == 0.95
        assert get_country_risk("RU") == 0.75

    def test_medium_risk_countries(self) -> None:
        """Test medium-risk countries."""
        assert get_country_risk("BR") == 0.40
        assert get_country_risk("MX") == 0.45
        assert get_country_risk("CN") == 0.40

    def test_unknown_country(self) -> None:
        """Test unknown country code returns default."""
        assert get_country_risk("XX") == 0.50
        assert get_country_risk("ZZZ") == 0.50

    def test_none_country(self) -> None:
        """Test None country code returns default."""
        assert get_country_risk(None) == 0.50

    def test_empty_country(self) -> None:
        """Test empty string country code returns default."""
        assert get_country_risk("") == 0.50

    def test_case_insensitive(self) -> None:
        """Test country code is case insensitive."""
        assert get_country_risk("us") == 0.10
        assert get_country_risk("Us") == 0.10
        assert get_country_risk("US") == 0.10

    def test_whitespace_stripped(self) -> None:
        """Test whitespace is stripped from country code."""
        assert get_country_risk(" US ") == 0.10
        assert get_country_risk("  GB  ") == 0.10


class TestNormalizationFunctions:
    """Test cases for normalization utilities."""

    def test_normalize_adverse_media_count_zero(self) -> None:
        """Test normalizing zero count."""
        assert normalize_adverse_media_count(0) == 0.0

    def test_normalize_adverse_media_count_within_max(self) -> None:
        """Test normalizing counts within max."""
        assert normalize_adverse_media_count(5) == 0.5
        assert normalize_adverse_media_count(10) == 1.0

    def test_normalize_adverse_media_count_exceeds_max(self) -> None:
        """Test normalizing counts exceeding max clips to 1.0."""
        assert normalize_adverse_media_count(15) == 1.0
        assert normalize_adverse_media_count(100) == 1.0

    def test_normalize_adverse_media_count_custom_max(self) -> None:
        """Test normalizing with custom max."""
        assert normalize_adverse_media_count(5, max_count=5) == 1.0
        assert normalize_adverse_media_count(2, max_count=5) == 0.4

    def test_normalize_document_age_zero(self) -> None:
        """Test normalizing zero days."""
        assert normalize_document_age(0) == 0.0

    def test_normalize_document_age_within_max(self) -> None:
        """Test normalizing age within max."""
        one_year = 365
        three_years = 365 * 3
        assert normalize_document_age(one_year) == pytest.approx(1/3, rel=0.01)
        assert normalize_document_age(three_years) == 1.0

    def test_normalize_document_age_exceeds_max(self) -> None:
        """Test normalizing age exceeding max clips to 1.0."""
        assert normalize_document_age(365 * 5) == 1.0

    def test_normalize_document_age_custom_max(self) -> None:
        """Test normalizing with custom max."""
        assert normalize_document_age(180, max_days=365) == pytest.approx(0.493, rel=0.01)
