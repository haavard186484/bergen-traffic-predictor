"""Leakage-safe feature construction."""

import numpy as np
import pandas as pd

from src.config import TARGET_COLUMN


def create_features(data: pd.DataFrame, traffic_column: str = "traffic_volume") -> pd.DataFrame:
    """Create one-hour-ahead target and features known at each timestamp.

    Input must contain hourly observations ordered by timestamp. Lagged traffic
    only uses values from earlier rows; the target is shifted one hour ahead.
    """
    required = {"timestamp", traffic_column}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    features = data.copy()
    features["timestamp"] = pd.to_datetime(features["timestamp"], utc=True)
    features = features.sort_values("timestamp").reset_index(drop=True)
    timestamp = features["timestamp"]

    features["hour"] = timestamp.dt.hour
    features["day_of_week"] = timestamp.dt.dayofweek
    features["month"] = timestamp.dt.month
    features["is_weekend"] = (features["day_of_week"] >= 5).astype(int)
    features["hour_sin"] = np.sin(2 * np.pi * features["hour"] / 24)
    features["hour_cos"] = np.cos(2 * np.pi * features["hour"] / 24)

    for hours in (1, 2, 24, 168):
        features[f"traffic_{hours}h_ago"] = features[traffic_column].shift(hours)

    features[TARGET_COLUMN] = features[traffic_column].shift(-1)
    return features
