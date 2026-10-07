"""Training entry point helpers."""

from collections.abc import Sequence

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.config import TARGET_COLUMN


def train_model(data: pd.DataFrame, feature_columns: Sequence[str]) -> HistGradientBoostingRegressor:
    """Train a first gradient-boosting model on an already chronological train set."""
    if TARGET_COLUMN not in data.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")
    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(data[list(feature_columns)], data[TARGET_COLUMN])
    return model
