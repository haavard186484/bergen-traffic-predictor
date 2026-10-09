"""Leakage-safe feature construction."""

import numpy as np
import pandas as pd

from src.config import TARGET_COLUMN, TIMEZONE

TRAFFIC_LAGS = (1, 2, 24, 168)
FEATURE_COLUMNS = (
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    *(f"traffic_{hours}h_ago" for hours in TRAFFIC_LAGS),
)


def create_features(data: pd.DataFrame, traffic_column: str = "traffic_volume") -> pd.DataFrame:
    """Create one-hour-ahead target and features known at each timestamp.

    Every lag and the target is looked up by its exact timestamp, rather than
    by row position. This deliberately leaves features or targets missing when
    the hourly axis contains a gap, rather than allowing a value to jump over
    that gap. Calendar values use Europe/Oslo, while timestamps remain UTC.
    """
    required = {"timestamp", traffic_column}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    features = data.copy()
    features["timestamp"] = pd.to_datetime(features["timestamp"], utc=True)
    if features["timestamp"].isna().any() or features["timestamp"].duplicated().any():
        raise ValueError("Timestamps must be valid and unique")
    features = features.sort_values("timestamp").reset_index(drop=True)
    timestamp = features["timestamp"]
    local_timestamp = timestamp.dt.tz_convert(TIMEZONE)
    observed = pd.Series(features[traffic_column].to_numpy(), index=timestamp)

    features["hour"] = local_timestamp.dt.hour
    features["day_of_week"] = local_timestamp.dt.dayofweek
    features["month"] = local_timestamp.dt.month
    features["is_weekend"] = (features["day_of_week"] >= 5).astype(int)
    features["hour_sin"] = np.sin(2 * np.pi * features["hour"] / 24)
    features["hour_cos"] = np.cos(2 * np.pi * features["hour"] / 24)

    for hours in TRAFFIC_LAGS:
        features[f"traffic_{hours}h_ago"] = observed.reindex(
            timestamp - pd.Timedelta(hours=hours)
        ).to_numpy()

    features[TARGET_COLUMN] = observed.reindex(timestamp + pd.Timedelta(hours=1)).to_numpy()
    return features
