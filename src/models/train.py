"""Training helpers for chronological traffic-model experiments."""

from collections.abc import Sequence

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

from src.config import TARGET_COLUMN


def train_model(
    data: pd.DataFrame, feature_columns: Sequence[str], model_name: str
) -> LinearRegression | HistGradientBoostingRegressor:
    """Train one supported model on pre-filtered chronological training rows."""
    if TARGET_COLUMN not in data.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")
    if model_name == "linear_regression":
        model = LinearRegression()
    elif model_name == "hist_gradient_boosting":
        model = HistGradientBoostingRegressor(random_state=42)
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    model.fit(data[list(feature_columns)], data[TARGET_COLUMN])
    return model
