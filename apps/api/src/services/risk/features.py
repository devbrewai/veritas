"""Feature engineering utilities for risk scoring.

Defines the input features for the risk classification model
and provides utilities for country risk scoring.
"""

from dataclasses import dataclass

# Feature names in the order expected by the model
FEATURE_NAMES = [
    "document_quality",
    "sanctions_score",
    "sanctions_match",
    "adverse_media_count",
    "adverse_media_sentiment",
    "country_risk",
    "document_age_days",
]


@dataclass
class RiskFeatures:
    """Input features for risk scoring model.

    All features are normalized to [0, 1] range where applicable
    for consistent model input.

    Attributes:
        document_quality: OCR confidence score [0, 1].
        sanctions_score: Sanctions match similarity score [0, 1].
        sanctions_match: Binary flag (1 if sanctions match, 0 otherwise).
        adverse_media_count: Number of negative media mentions.
        adverse_media_sentiment: Average sentiment score [-1, 1].
        country_risk: Country risk score [0, 1].
        document_age_days: Days since document was issued.
    """

    document_quality: float
    sanctions_score: float
    sanctions_match: int
    adverse_media_count: int
    adverse_media_sentiment: float
    country_risk: float
    document_age_days: int

    def __post_init__(self) -> None:
        """Validate feature values after initialization."""
        if not 0.0 <= self.document_quality <= 1.0:
            raise ValueError(f"document_quality must be in [0, 1], got {self.document_quality}")
        if not 0.0 <= self.sanctions_score <= 1.0:
            raise ValueError(f"sanctions_score must be in [0, 1], got {self.sanctions_score}")
        if self.sanctions_match not in (0, 1):
            raise ValueError(f"sanctions_match must be 0 or 1, got {self.sanctions_match}")
        if self.adverse_media_count < 0:
            raise ValueError(f"adverse_media_count must be >= 0, got {self.adverse_media_count}")
        if not -1.0 <= self.adverse_media_sentiment <= 1.0:
            raise ValueError(f"adverse_media_sentiment must be in [-1, 1], got {self.adverse_media_sentiment}")
        if not 0.0 <= self.country_risk <= 1.0:
            raise ValueError(f"country_risk must be in [0, 1], got {self.country_risk}")
        if self.document_age_days < 0:
            raise ValueError(f"document_age_days must be >= 0, got {self.document_age_days}")

    def to_array(self) -> list[float]:
        """Convert features to array for model input.

        Returns:
            List of feature values in the order expected by the model.
        """
        return [
            self.document_quality,
            self.sanctions_score,
            float(self.sanctions_match),
            float(self.adverse_media_count),
            self.adverse_media_sentiment,
            self.country_risk,
            float(self.document_age_days),
        ]

    def to_dict(self) -> dict[str, float]:
        """Convert features to dictionary.

        Returns:
            Dictionary mapping feature names to values.
        """
        return {
            "document_quality": self.document_quality,
            "sanctions_score": self.sanctions_score,
            "sanctions_match": float(self.sanctions_match),
            "adverse_media_count": float(self.adverse_media_count),
            "adverse_media_sentiment": self.adverse_media_sentiment,
            "country_risk": self.country_risk,
            "document_age_days": float(self.document_age_days),
        }


# Country risk scores based on FATF and international sanctions lists
# Scale: 0.0 (lowest risk) to 1.0 (highest risk)
COUNTRY_RISK_SCORES: dict[str, float] = {
    # Low risk - FATF compliant jurisdictions
    "US": 0.10,
    "USA": 0.10,
    "GB": 0.10,
    "GBR": 0.10,
    "CA": 0.10,
    "CAN": 0.10,
    "AU": 0.10,
    "AUS": 0.10,
    "DE": 0.10,
    "DEU": 0.10,
    "FR": 0.15,
    "FRA": 0.15,
    "JP": 0.10,
    "JPN": 0.10,
    "KR": 0.15,
    "KOR": 0.15,
    "SG": 0.10,
    "SGP": 0.10,
    "NZ": 0.10,
    "NZL": 0.10,
    "CH": 0.15,
    "CHE": 0.15,
    "NL": 0.10,
    "NLD": 0.10,
    "SE": 0.10,
    "SWE": 0.10,
    "NO": 0.10,
    "NOR": 0.10,
    "DK": 0.10,
    "DNK": 0.10,
    "FI": 0.10,
    "FIN": 0.10,
    "IE": 0.15,
    "IRL": 0.15,
    "BE": 0.15,
    "BEL": 0.15,
    "AT": 0.15,
    "AUT": 0.15,
    "IT": 0.20,
    "ITA": 0.20,
    "ES": 0.20,
    "ESP": 0.20,
    "PT": 0.20,
    "PRT": 0.20,

    # Medium risk - Enhanced due diligence recommended
    "BR": 0.40,
    "BRA": 0.40,
    "MX": 0.45,
    "MEX": 0.45,
    "IN": 0.35,
    "IND": 0.35,
    "CN": 0.40,
    "CHN": 0.40,
    "ZA": 0.45,
    "ZAF": 0.45,
    "NG": 0.55,
    "NGA": 0.55,
    "KE": 0.50,
    "KEN": 0.50,
    "AE": 0.35,
    "ARE": 0.35,
    "SA": 0.40,
    "SAU": 0.40,
    "TR": 0.50,
    "TUR": 0.50,
    "PH": 0.50,
    "PHL": 0.50,
    "ID": 0.45,
    "IDN": 0.45,
    "VN": 0.45,
    "VNM": 0.45,
    "TH": 0.40,
    "THA": 0.40,
    "MY": 0.35,
    "MYS": 0.35,

    # High risk - FATF grey list or sanctions concerns
    "RU": 0.75,
    "RUS": 0.75,
    "BY": 0.75,
    "BLR": 0.75,
    "VE": 0.70,
    "VEN": 0.70,
    "MM": 0.70,
    "MMR": 0.70,
    "PK": 0.60,
    "PAK": 0.60,
    "AF": 0.80,
    "AFG": 0.80,
    "YE": 0.75,
    "YEM": 0.75,
    "LY": 0.70,
    "LBY": 0.70,

    # Very high risk - Comprehensive sanctions
    "IR": 0.95,
    "IRN": 0.95,
    "KP": 0.99,
    "PRK": 0.99,
    "SY": 0.95,
    "SYR": 0.95,
    "CU": 0.85,
    "CUB": 0.85,

    # Default for unknown countries
    "DEFAULT": 0.50,
}


def get_country_risk(country_code: str | None) -> float:
    """Get risk score for a country code.

    Supports both ISO 3166-1 alpha-2 (e.g., "US") and
    alpha-3 (e.g., "USA") codes.

    Args:
        country_code: ISO country code or None.

    Returns:
        Risk score in [0, 1] range.
    """
    if not country_code:
        return COUNTRY_RISK_SCORES["DEFAULT"]

    code = country_code.upper().strip()
    return COUNTRY_RISK_SCORES.get(code, COUNTRY_RISK_SCORES["DEFAULT"])


def normalize_adverse_media_count(count: int, max_count: int = 10) -> float:
    """Normalize adverse media count to [0, 1] range.

    Args:
        count: Raw count of negative mentions.
        max_count: Maximum count for normalization (counts above are clipped).

    Returns:
        Normalized count in [0, 1] range.
    """
    return min(count / max_count, 1.0)


def normalize_document_age(days: int, max_days: int = 365 * 3) -> float:
    """Normalize document age to [0, 1] range.

    Older documents are higher risk.

    Args:
        days: Document age in days.
        max_days: Maximum age for normalization (default 3 years).

    Returns:
        Normalized age in [0, 1] range.
    """
    return min(days / max_days, 1.0)
