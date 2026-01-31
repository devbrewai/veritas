"""Tests for risk scoring model with SHAP explanations."""

import pytest
import numpy as np

from src.services.risk.features import FEATURE_NAMES, RiskFeatures
from src.services.risk.model import RiskScoringModel


class TestRiskScoringModel:
    """Test cases for RiskScoringModel."""

    @pytest.fixture
    def model(self) -> RiskScoringModel:
        """Create and load a risk scoring model."""
        model = RiskScoringModel()
        success = model.load()
        if not success:
            pytest.skip("Risk model not available")
        return model

    @pytest.fixture
    def low_risk_features(self) -> RiskFeatures:
        """Create low-risk feature set."""
        return RiskFeatures(
            document_quality=0.95,
            sanctions_score=0.05,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.1,
            country_risk=0.1,
            document_age_days=30,
        )

    @pytest.fixture
    def high_risk_features(self) -> RiskFeatures:
        """Create high-risk feature set."""
        return RiskFeatures(
            document_quality=0.4,
            sanctions_score=0.95,
            sanctions_match=1,
            adverse_media_count=5,
            adverse_media_sentiment=-0.8,
            country_risk=0.9,
            document_age_days=800,
        )

    @pytest.fixture
    def medium_risk_features(self) -> RiskFeatures:
        """Create medium-risk feature set."""
        return RiskFeatures(
            document_quality=0.7,
            sanctions_score=0.5,
            sanctions_match=0,
            adverse_media_count=2,
            adverse_media_sentiment=-0.3,
            country_risk=0.5,
            document_age_days=200,
        )

    def test_model_loads_successfully(self) -> None:
        """Test that model loads without errors."""
        model = RiskScoringModel()
        success = model.load()
        assert success is True
        assert model.is_loaded is True

    def test_model_version(self, model: RiskScoringModel) -> None:
        """Test that model has version."""
        assert model.version is not None
        assert model.version != "unknown"

    def test_model_feature_importance(self, model: RiskScoringModel) -> None:
        """Test that model has feature importance."""
        importance = model.feature_importance
        assert len(importance) == len(FEATURE_NAMES)
        for name in FEATURE_NAMES:
            assert name in importance

    def test_predict_returns_tuple(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that predict returns correct tuple structure."""
        risk_score, risk_class, contributions = model.predict(low_risk_features)

        assert isinstance(risk_score, float)
        assert isinstance(risk_class, int)
        assert isinstance(contributions, list)

    def test_predict_risk_score_range(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that risk score is in valid range."""
        risk_score, _, _ = model.predict(low_risk_features)
        assert 0.0 <= risk_score <= 1.0

    def test_predict_risk_class_valid(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that risk class is valid."""
        _, risk_class, _ = model.predict(low_risk_features)
        assert risk_class in [0, 1, 2]

    def test_low_risk_prediction(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that low-risk features produce low risk score."""
        risk_score, risk_class, _ = model.predict(low_risk_features)

        # Low risk should have low score
        assert risk_score < 0.3
        assert risk_class == 0  # Low

    def test_high_risk_prediction(
        self, model: RiskScoringModel, high_risk_features: RiskFeatures
    ) -> None:
        """Test that high-risk features produce high risk score."""
        risk_score, risk_class, _ = model.predict(high_risk_features)

        # High risk should have high score
        assert risk_score > 0.7
        assert risk_class == 2  # High

    def test_medium_risk_prediction(
        self, model: RiskScoringModel, medium_risk_features: RiskFeatures
    ) -> None:
        """Test that medium-risk features produce medium risk score."""
        risk_score, risk_class, _ = model.predict(medium_risk_features)

        # Medium risk should have medium score
        assert 0.2 <= risk_score <= 0.8

    def test_shap_contributions_returned(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that SHAP contributions are returned."""
        _, _, contributions = model.predict(low_risk_features)

        assert len(contributions) > 0
        # Each contribution is (name, value, shap_value)
        for name, value, shap_value in contributions:
            assert isinstance(name, str)
            assert isinstance(value, (int, float))
            assert isinstance(shap_value, float)

    def test_shap_contributions_sorted(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that contributions are sorted by importance."""
        _, _, contributions = model.predict(low_risk_features)

        if len(contributions) > 1:
            # Should be sorted by absolute SHAP value descending
            shap_values = [abs(c[2]) for c in contributions]
            assert shap_values == sorted(shap_values, reverse=True)

    def test_shap_contributions_include_all_features(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that all features have contributions."""
        _, _, contributions = model.predict(low_risk_features)

        feature_names = [c[0] for c in contributions]
        for name in FEATURE_NAMES:
            assert name in feature_names

    def test_predict_proba_shape(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that predict_proba returns correct shape."""
        proba = model.predict_proba(low_risk_features)

        assert proba.shape == (3,)  # 3 classes
        assert np.isclose(proba.sum(), 1.0)

    def test_predict_proba_values_valid(
        self, model: RiskScoringModel, low_risk_features: RiskFeatures
    ) -> None:
        """Test that probabilities are valid."""
        proba = model.predict_proba(low_risk_features)

        assert all(0 <= p <= 1 for p in proba)

    def test_predict_without_loading_raises(self) -> None:
        """Test that predict raises if model not loaded."""
        model = RiskScoringModel()
        features = RiskFeatures(
            document_quality=0.9,
            sanctions_score=0.1,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.1,
            document_age_days=30,
        )

        with pytest.raises(RuntimeError, match="not loaded"):
            model.predict(features)

    def test_predict_proba_without_loading_raises(self) -> None:
        """Test that predict_proba raises if model not loaded."""
        model = RiskScoringModel()
        features = RiskFeatures(
            document_quality=0.9,
            sanctions_score=0.1,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.1,
            document_age_days=30,
        )

        with pytest.raises(RuntimeError, match="not loaded"):
            model.predict_proba(features)

    def test_load_nonexistent_path_returns_false(self) -> None:
        """Test loading from nonexistent path returns False."""
        model = RiskScoringModel()
        success = model.load("/nonexistent/path/model.pkl")
        assert success is False
        assert model.is_loaded is False


class TestRiskScoringModelConsistency:
    """Test model prediction consistency."""

    @pytest.fixture
    def model(self) -> RiskScoringModel:
        """Create and load a risk scoring model."""
        model = RiskScoringModel()
        success = model.load()
        if not success:
            pytest.skip("Risk model not available")
        return model

    def test_same_input_same_output(self, model: RiskScoringModel) -> None:
        """Test that same input produces same output."""
        features = RiskFeatures(
            document_quality=0.8,
            sanctions_score=0.3,
            sanctions_match=0,
            adverse_media_count=1,
            adverse_media_sentiment=-0.2,
            country_risk=0.3,
            document_age_days=100,
        )

        score1, class1, _ = model.predict(features)
        score2, class2, _ = model.predict(features)

        assert score1 == score2
        assert class1 == class2

    def test_high_sanctions_score_increases_risk(
        self, model: RiskScoringModel
    ) -> None:
        """Test that high sanctions score increases risk score."""
        low_sanctions = RiskFeatures(
            document_quality=0.8,
            sanctions_score=0.1,  # Low sanctions score
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.3,
            document_age_days=100,
        )

        high_sanctions = RiskFeatures(
            document_quality=0.8,
            sanctions_score=0.9,  # High sanctions score
            sanctions_match=1,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.3,
            document_age_days=100,
        )

        low_score, _, _ = model.predict(low_sanctions)
        high_score, _, _ = model.predict(high_sanctions)

        assert high_score > low_score

    def test_high_country_risk_increases_score(
        self, model: RiskScoringModel
    ) -> None:
        """Test that high country risk increases risk score."""
        low_country = RiskFeatures(
            document_quality=0.8,
            sanctions_score=0.3,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.1,  # Low risk country
            document_age_days=100,
        )

        high_country = RiskFeatures(
            document_quality=0.8,
            sanctions_score=0.3,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.9,  # High risk country
            document_age_days=100,
        )

        low_score, _, _ = model.predict(low_country)
        high_score, _, _ = model.predict(high_country)

        assert high_score > low_score
