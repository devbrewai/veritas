"""Tests for risk model training and synthetic data generation."""

import os
import tempfile

import pytest
import numpy as np

from src.services.risk.features import FEATURE_NAMES
from src.services.risk.training import (
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
    generate_synthetic_data,
    train_risk_model,
    load_trained_model,
)


class TestSyntheticDataGeneration:
    """Test cases for synthetic data generation."""

    def test_generates_correct_number_of_samples(self) -> None:
        """Test that correct number of samples is generated."""
        data = generate_synthetic_data(n_samples=100)
        assert len(data) == 100

    def test_generates_large_dataset(self) -> None:
        """Test generating larger dataset."""
        data = generate_synthetic_data(n_samples=1000)
        assert len(data) == 1000

    def test_has_all_features(self) -> None:
        """Test that all expected features are present."""
        data = generate_synthetic_data(n_samples=10)

        expected_columns = FEATURE_NAMES + ["risk_label"]
        for col in expected_columns:
            assert col in data.columns, f"Missing column: {col}"

    def test_has_risk_label(self) -> None:
        """Test that risk_label column exists."""
        data = generate_synthetic_data(n_samples=10)
        assert "risk_label" in data.columns

    def test_risk_labels_are_valid(self) -> None:
        """Test that risk labels are 0, 1, or 2."""
        data = generate_synthetic_data(n_samples=100)
        assert set(data["risk_label"].unique()).issubset({RISK_LOW, RISK_MEDIUM, RISK_HIGH})

    def test_class_distribution_approximate(self) -> None:
        """Test that class distribution approximately matches."""
        data = generate_synthetic_data(n_samples=1000, class_distribution=(0.7, 0.2, 0.1))
        label_counts = data["risk_label"].value_counts(normalize=True)

        # Allow 10% tolerance
        assert abs(label_counts[RISK_LOW] - 0.70) < 0.10
        assert abs(label_counts[RISK_MEDIUM] - 0.20) < 0.10
        assert abs(label_counts[RISK_HIGH] - 0.10) < 0.10

    def test_custom_class_distribution(self) -> None:
        """Test custom class distribution."""
        data = generate_synthetic_data(n_samples=1000, class_distribution=(0.5, 0.3, 0.2))
        label_counts = data["risk_label"].value_counts(normalize=True)

        assert abs(label_counts[RISK_LOW] - 0.50) < 0.10
        assert abs(label_counts[RISK_MEDIUM] - 0.30) < 0.10
        assert abs(label_counts[RISK_HIGH] - 0.20) < 0.10

    def test_reproducible_with_seed(self) -> None:
        """Test that same seed produces same data."""
        data1 = generate_synthetic_data(n_samples=50, seed=42)
        data2 = generate_synthetic_data(n_samples=50, seed=42)

        assert data1.equals(data2)

    def test_different_seed_produces_different_data(self) -> None:
        """Test that different seeds produce different data."""
        data1 = generate_synthetic_data(n_samples=50, seed=42)
        data2 = generate_synthetic_data(n_samples=50, seed=123)

        assert not data1.equals(data2)

    def test_feature_ranges_valid(self) -> None:
        """Test that features are within valid ranges."""
        data = generate_synthetic_data(n_samples=500)

        # document_quality: [0, 1]
        assert data["document_quality"].min() >= 0
        assert data["document_quality"].max() <= 1

        # sanctions_score: [0, 1]
        assert data["sanctions_score"].min() >= 0
        assert data["sanctions_score"].max() <= 1

        # sanctions_match: 0 or 1
        assert set(data["sanctions_match"].unique()).issubset({0, 1})

        # adverse_media_count: >= 0
        assert data["adverse_media_count"].min() >= 0

        # adverse_media_sentiment: [-1, 1]
        assert data["adverse_media_sentiment"].min() >= -1
        assert data["adverse_media_sentiment"].max() <= 1

        # country_risk: [0, 1]
        assert data["country_risk"].min() >= 0
        assert data["country_risk"].max() <= 1

        # document_age_days: >= 0
        assert data["document_age_days"].min() >= 0


class TestModelTraining:
    """Test cases for model training."""

    @pytest.fixture
    def temp_model_path(self) -> str:
        """Create temporary path for model."""
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)

    def test_trains_model_successfully(self, temp_model_path: str) -> None:
        """Test that model trains without errors."""
        model, metrics = train_risk_model(
            output_path=temp_model_path,
            n_samples=200,
            verbose=False,
        )

        assert model is not None
        assert metrics is not None

    def test_returns_valid_metrics(self, temp_model_path: str) -> None:
        """Test that valid metrics are returned."""
        _, metrics = train_risk_model(
            output_path=temp_model_path,
            n_samples=200,
            verbose=False,
        )

        assert "accuracy" in metrics
        assert "f1_macro" in metrics
        assert "train_samples" in metrics
        assert "test_samples" in metrics

        # Check metric values are reasonable
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["f1_macro"] <= 1

    def test_accuracy_above_threshold(self, temp_model_path: str) -> None:
        """Test that model achieves minimum accuracy."""
        _, metrics = train_risk_model(
            output_path=temp_model_path,
            n_samples=500,
            verbose=False,
        )

        # Synthetic data should be easy to classify
        # Expect at least 70% accuracy
        assert metrics["accuracy"] >= 0.70

    def test_saves_model_file(self, temp_model_path: str) -> None:
        """Test that model file is saved."""
        train_risk_model(
            output_path=temp_model_path,
            n_samples=200,
            verbose=False,
        )

        assert os.path.exists(temp_model_path)

    def test_model_can_predict(self, temp_model_path: str) -> None:
        """Test that trained model can make predictions."""
        model, _ = train_risk_model(
            output_path=temp_model_path,
            n_samples=200,
            verbose=False,
        )

        # Create sample input
        X_test = [[0.9, 0.1, 0, 0, 0.0, 0.1, 30]]  # Low risk profile
        predictions = model.predict(X_test)

        assert len(predictions) == 1
        assert predictions[0] in [RISK_LOW, RISK_MEDIUM, RISK_HIGH]

    def test_model_returns_probabilities(self, temp_model_path: str) -> None:
        """Test that model returns calibrated probabilities."""
        model, _ = train_risk_model(
            output_path=temp_model_path,
            n_samples=200,
            verbose=False,
        )

        X_test = [[0.9, 0.1, 0, 0, 0.0, 0.1, 30]]
        probabilities = model.predict_proba(X_test)

        assert probabilities.shape == (1, 3)  # 3 classes
        assert np.isclose(probabilities.sum(), 1.0)  # Sum to 1
        assert all(0 <= p <= 1 for p in probabilities[0])

    def test_train_with_custom_data(self, temp_model_path: str) -> None:
        """Test training with custom data."""
        custom_data = generate_synthetic_data(n_samples=300, seed=99)
        model, metrics = train_risk_model(
            data=custom_data,
            output_path=temp_model_path,
            verbose=False,
        )

        assert model is not None
        assert metrics["train_samples"] + metrics["test_samples"] == 300


class TestModelLoading:
    """Test cases for model loading."""

    @pytest.fixture
    def trained_model_path(self) -> str:
        """Train and save a model for testing."""
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)

        train_risk_model(
            output_path=path,
            n_samples=200,
            verbose=False,
        )

        yield path
        if os.path.exists(path):
            os.remove(path)

    def test_load_trained_model(self, trained_model_path: str) -> None:
        """Test loading a trained model."""
        model_data = load_trained_model(trained_model_path)

        assert model_data is not None
        assert "model" in model_data
        assert "base_model" in model_data
        assert "feature_names" in model_data
        assert "metrics" in model_data
        assert "version" in model_data

    def test_load_nonexistent_model(self) -> None:
        """Test loading a non-existent model returns None."""
        result = load_trained_model("/nonexistent/path/model.pkl")
        assert result is None

    def test_loaded_model_can_predict(self, trained_model_path: str) -> None:
        """Test that loaded model can make predictions."""
        model_data = load_trained_model(trained_model_path)
        model = model_data["model"]

        X_test = [[0.9, 0.1, 0, 0, 0.0, 0.1, 30]]
        predictions = model.predict(X_test)

        assert predictions[0] in [RISK_LOW, RISK_MEDIUM, RISK_HIGH]

    def test_loaded_model_has_feature_importance(
        self, trained_model_path: str
    ) -> None:
        """Test that loaded model has feature importance."""
        model_data = load_trained_model(trained_model_path)

        assert "feature_importance" in model_data
        importance = model_data["feature_importance"]

        # Check all features have importance values
        for feature in FEATURE_NAMES:
            assert feature in importance
            assert importance[feature] >= 0
