"""Synthetic data generation and model training for risk scoring.

Creates realistic training data based on KYC domain knowledge
and trains a LightGBM classifier with probability calibration.
"""

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report

from src.services.risk.features import FEATURE_NAMES

logger = logging.getLogger(__name__)

# Risk class labels
RISK_LOW = 0
RISK_MEDIUM = 1
RISK_HIGH = 2

# Default model path
DEFAULT_MODEL_PATH = "./models/risk_model.pkl"


def generate_synthetic_data(
    n_samples: int = 1000,
    seed: int = 42,
    class_distribution: tuple[float, float, float] = (0.70, 0.20, 0.10),
) -> pd.DataFrame:
    """Generate synthetic training data for risk model.

    Creates realistic feature distributions based on KYC domain
    knowledge with controlled class distribution.

    Args:
        n_samples: Number of samples to generate.
        seed: Random seed for reproducibility.
        class_distribution: Tuple of (low_risk, medium_risk, high_risk) proportions.

    Returns:
        DataFrame with features and risk_label column.
    """
    np.random.seed(seed)
    p_low, p_med, p_high = class_distribution

    data = []

    for _ in range(n_samples):
        # Randomly assign base risk level
        base_risk = np.random.choice([RISK_LOW, RISK_MEDIUM, RISK_HIGH], p=[p_low, p_med, p_high])

        if base_risk == RISK_LOW:
            # Low risk profile
            doc_quality = np.random.beta(8, 2)  # High quality (skewed right)
            sanctions_score = np.random.beta(1, 10)  # Low score (skewed left)
            sanctions_match = 0
            adverse_count = np.random.choice([0, 0, 0, 0, 1], p=[0.85, 0.05, 0.05, 0.025, 0.025])
            adverse_sentiment = np.random.uniform(-0.2, 0.3)
            country_risk = np.random.beta(2, 8)  # Low risk
            doc_age = np.random.randint(0, 365)
            label = RISK_LOW

        elif base_risk == RISK_MEDIUM:
            # Medium risk profile
            doc_quality = np.random.beta(5, 3)
            sanctions_score = np.random.uniform(0.3, 0.7)
            sanctions_match = np.random.choice([0, 1], p=[0.8, 0.2])
            adverse_count = np.random.choice([0, 1, 2, 3], p=[0.4, 0.3, 0.2, 0.1])
            adverse_sentiment = np.random.uniform(-0.5, 0.1)
            country_risk = np.random.beta(5, 5)  # Medium risk
            doc_age = np.random.randint(0, 730)  # Up to 2 years
            label = RISK_MEDIUM

        else:
            # High risk profile
            doc_quality = np.random.beta(2, 5)  # Lower quality
            sanctions_score = np.random.beta(6, 2)  # High score
            sanctions_match = np.random.choice([0, 1], p=[0.3, 0.7])
            adverse_count = np.random.choice([0, 1, 2, 3, 4, 5], p=[0.1, 0.15, 0.2, 0.2, 0.2, 0.15])
            adverse_sentiment = np.random.uniform(-0.9, -0.3)
            country_risk = np.random.beta(7, 3)  # High risk
            doc_age = np.random.randint(365, 1095)  # 1-3 years
            label = RISK_HIGH

        data.append({
            "document_quality": doc_quality,
            "sanctions_score": sanctions_score,
            "sanctions_match": sanctions_match,
            "adverse_media_count": adverse_count,
            "adverse_media_sentiment": adverse_sentiment,
            "country_risk": country_risk,
            "document_age_days": doc_age,
            "risk_label": label,
        })

    return pd.DataFrame(data)


def train_risk_model(
    data: pd.DataFrame | None = None,
    output_path: str = DEFAULT_MODEL_PATH,
    test_size: float = 0.2,
    n_samples: int = 1000,
    verbose: bool = True,
) -> tuple[CalibratedClassifierCV, dict]:
    """Train and calibrate LightGBM risk classification model.

    Uses Platt scaling for probability calibration to produce
    well-calibrated risk scores.

    Args:
        data: Training data. If None, generates synthetic data.
        output_path: Path to save the trained model.
        test_size: Proportion of data for testing.
        n_samples: Number of samples to generate if data is None.
        verbose: Whether to print training progress.

    Returns:
        Tuple of (calibrated_model, metrics_dict).
    """
    # Generate data if not provided
    if data is None:
        if verbose:
            logger.info(f"Generating {n_samples} synthetic samples...")
        data = generate_synthetic_data(n_samples=n_samples)

    # Split features and labels
    X = data[FEATURE_NAMES]
    y = data["risk_label"]

    # Train-test split with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=42,
        stratify=y,
    )

    if verbose:
        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        logger.info(f"Class distribution: {y_train.value_counts().sort_index().to_dict()}")

    # Define base LightGBM model
    base_model = LGBMClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        num_leaves=31,
        min_child_samples=20,
        class_weight="balanced",  # Handle class imbalance
        random_state=42,
        verbose=-1,  # Suppress LightGBM warnings
    )

    # Calibrate probabilities using Platt scaling with 3-fold CV
    # This trains the model and calibrates probabilities in one step
    calibrated_model = CalibratedClassifierCV(
        base_model,
        method="sigmoid",  # Platt scaling
        cv=3,  # 3-fold cross-validation for calibration
    )
    calibrated_model.fit(X_train, y_train)

    # Fit base model on full training data for feature importance
    base_model.fit(X_train, y_train)

    # Evaluate model
    y_pred = calibrated_model.predict(X_test)
    y_proba = calibrated_model.predict_proba(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "f1_macro": f1_score(y_test, y_pred, average="macro"),
        "f1_weighted": f1_score(y_test, y_pred, average="weighted"),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "class_distribution": y.value_counts().sort_index().to_dict(),
    }

    if verbose:
        logger.info(f"Model accuracy: {metrics['accuracy']:.3f}")
        logger.info(f"F1 (macro): {metrics['f1_macro']:.3f}")
        logger.info(f"F1 (weighted): {metrics['f1_weighted']:.3f}")
        logger.info("\nClassification Report:")
        logger.info("\n" + classification_report(
            y_test, y_pred,
            target_names=["Low", "Medium", "High"]
        ))

    # Get feature importances from base model
    feature_importance = dict(zip(FEATURE_NAMES, base_model.feature_importances_))

    # Save model
    model_path = Path(output_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    model_data = {
        "model": calibrated_model,
        "base_model": base_model,
        "feature_names": FEATURE_NAMES,
        "feature_importance": feature_importance,
        "metrics": metrics,
        "version": "1.0.0",
        "risk_labels": {
            RISK_LOW: "Low",
            RISK_MEDIUM: "Medium",
            RISK_HIGH: "High",
        },
    }

    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)

    if verbose:
        logger.info(f"Model saved to: {model_path}")
        logger.info(f"Feature importance: {feature_importance}")

    return calibrated_model, metrics


def load_trained_model(model_path: str = DEFAULT_MODEL_PATH) -> dict | None:
    """Load a previously trained model.

    Args:
        model_path: Path to the saved model.

    Returns:
        Model data dictionary or None if not found.
    """
    path = Path(model_path)
    if not path.exists():
        return None

    with open(path, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    # Train model when run directly
    logging.basicConfig(level=logging.INFO)
    print("Training risk scoring model...")
    model, metrics = train_risk_model(verbose=True)
    print(f"\nTraining complete! Metrics: {metrics}")
