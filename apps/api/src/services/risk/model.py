"""Risk scoring model with SHAP explanations.

Loads the trained LightGBM model and provides prediction
with explainability through SHAP values.
"""

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import shap

from src.services.risk.features import FEATURE_NAMES, RiskFeatures
from src.services.risk.training import DEFAULT_MODEL_PATH

logger = logging.getLogger(__name__)


class RiskScoringModel:
    """LightGBM risk model with SHAP explanations.

    Provides risk predictions with feature contribution explanations
    for transparency and interpretability.
    """

    def __init__(self) -> None:
        """Initialize the model (not loaded until load() is called)."""
        self._model = None
        self._base_model = None
        self._explainer = None
        self._loaded = False
        self._version = "unknown"
        self._feature_importance: dict[str, float] = {}

    def load(self, model_path: str | None = None) -> bool:
        """Load model from pickle file.

        Args:
            model_path: Path to the model file. Uses default if None.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        if model_path is None:
            model_path = DEFAULT_MODEL_PATH

        path = Path(model_path)
        if not path.exists():
            logger.warning(f"Risk model not found at: {path}")
            return False

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)

            self._model = data["model"]
            self._base_model = data.get("base_model")
            self._version = data.get("version", "1.0.0")
            self._feature_importance = data.get("feature_importance", {})

            # Initialize SHAP TreeExplainer with the base LightGBM model
            if self._base_model is not None:
                self._explainer = shap.TreeExplainer(self._base_model)
            else:
                logger.warning("Base model not found, SHAP explanations unavailable")

            self._loaded = True
            logger.info(f"Loaded risk model v{self._version}")
            return True

        except Exception as e:
            logger.exception(f"Failed to load risk model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self._loaded

    @property
    def version(self) -> str:
        """Return model version."""
        return self._version

    @property
    def feature_importance(self) -> dict[str, float]:
        """Return feature importance from training."""
        return self._feature_importance.copy()

    def predict(
        self,
        features: RiskFeatures,
    ) -> tuple[float, int, list[tuple[str, float, float]]]:
        """Predict risk score with SHAP explanations.

        Args:
            features: Input features for prediction.

        Returns:
            Tuple of (risk_score, risk_class, feature_contributions):
            - risk_score: Calibrated probability [0, 1]
            - risk_class: 0 (Low), 1 (Medium), 2 (High)
            - feature_contributions: List of (feature_name, value, shap_value)
                sorted by absolute SHAP value (most important first)

        Raises:
            RuntimeError: If model is not loaded.
        """
        if not self._loaded:
            raise RuntimeError("Risk model not loaded. Call load() first.")

        # Convert features to array
        X = np.array([features.to_array()])

        # Get calibrated probabilities for all classes
        proba = self._model.predict_proba(X)[0]

        # Compute risk score as weighted average of class probabilities
        # Low risk contributes 0, Medium contributes 0.5, High contributes 1.0
        risk_score = proba[1] * 0.5 + proba[2] * 1.0

        # Predicted class (argmax)
        risk_class = int(np.argmax(proba))

        # Compute SHAP explanations
        feature_contributions = self._get_shap_explanations(X, features)

        return risk_score, risk_class, feature_contributions

    def predict_proba(self, features: RiskFeatures) -> np.ndarray:
        """Get class probabilities.

        Args:
            features: Input features for prediction.

        Returns:
            Array of shape (3,) with probabilities for [Low, Medium, High].

        Raises:
            RuntimeError: If model is not loaded.
        """
        if not self._loaded:
            raise RuntimeError("Risk model not loaded. Call load() first.")

        X = np.array([features.to_array()])
        return self._model.predict_proba(X)[0]

    def _get_shap_explanations(
        self,
        X: np.ndarray,
        features: RiskFeatures,
    ) -> list[tuple[str, float, float]]:
        """Get SHAP value explanations for prediction.

        Args:
            X: Feature array for prediction.
            features: Original RiskFeatures for value lookup.

        Returns:
            List of (feature_name, feature_value, shap_value) tuples
            sorted by absolute SHAP value descending.
        """
        if self._explainer is None:
            # Return empty if no explainer available
            return []

        try:
            # Convert to DataFrame with proper feature names for SHAP
            X_df = pd.DataFrame(X, columns=FEATURE_NAMES)

            # Get SHAP values
            shap_values = self._explainer.shap_values(X_df)

            # SHAP values shape: (n_samples, n_features, n_classes)
            # For multi-class LightGBM with shape (1, 7, 3):
            # - Index 0: sample
            # - Index :,2: High risk class SHAP values for all features
            if shap_values.ndim == 3:
                # Shape is (n_samples, n_features, n_classes)
                # Get high risk class (index 2) for first sample
                high_risk_shap = shap_values[0, :, 2]
            elif isinstance(shap_values, list):
                # Legacy format: list of arrays per class
                high_risk_shap = shap_values[2][0]
            else:
                high_risk_shap = shap_values[0]

            # Build feature contributions
            feature_dict = features.to_dict()
            contributions = []

            for i, name in enumerate(FEATURE_NAMES):
                shap_val = high_risk_shap[i]
                # Handle numpy types
                if hasattr(shap_val, 'item'):
                    shap_val = shap_val.item()
                contributions.append((
                    name,
                    feature_dict[name],
                    float(shap_val),
                ))

            # Sort by absolute SHAP value (most important first)
            contributions.sort(key=lambda x: abs(x[2]), reverse=True)

            return contributions

        except Exception as e:
            logger.warning(f"Error computing SHAP values: {e}")
            return []


# Global model instance
risk_model = RiskScoringModel()
