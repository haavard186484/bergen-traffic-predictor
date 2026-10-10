"""Leakage-safe feature construction."""

import numpy as np
import pandas as pd

from src.config import TARGET_COLUMN, TIMEZONE
from src.data.frost import WEATHER_COLUMNS
from src.features.calendar_events import (
    CALENDAR_EVENT_FEATURE_COLUMNS,
    add_norwegian_calendar_event_features,
)

TRAFFIC_LAGS = (1, 2, 24, 168)
WEATHER_LAGS = (1, 2, 24)
FEATURE_COLUMNS = (
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    *(f"traffic_{hours}h_ago" for hours in TRAFFIC_LAGS),
)


def feature_columns(
    weather_columns: tuple[str, ...] = (), calendar_event_features: bool = False
) -> tuple[str, ...]:
    """Return the common model schema, optionally augmented with weather."""
    unexpected = set(weather_columns).difference(WEATHER_COLUMNS)
    if unexpected:
        raise ValueError(f"Unsupported weather columns: {sorted(unexpected)}")
    weather_lag_columns = tuple(
        f"{column}_{hours}h_ago" for column in weather_columns for hours in WEATHER_LAGS
    )
    calendar_columns = CALENDAR_EVENT_FEATURE_COLUMNS if calendar_event_features else ()
    return (*FEATURE_COLUMNS, *calendar_columns, *weather_lag_columns)


def create_features(
    data: pd.DataFrame,
    traffic_column: str = "traffic_volume",
    weather_columns: tuple[str, ...] = (),
    calendar_event_features: bool = False,
) -> pd.DataFrame:
    """Create one-hour-ahead target and features known at each timestamp.

    Every lag and the target is looked up by its exact timestamp, rather than
    by row position. This deliberately leaves features or targets missing when
    the hourly axis contains a gap, rather than allowing a value to jump over
    that gap. Calendar values use Europe/Oslo, while timestamps remain UTC.
    """
    required = {"timestamp", traffic_column, *weather_columns}
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
    features["local_timestamp"] = local_timestamp

    if calendar_event_features:
        features = add_norwegian_calendar_event_features(features)

    for hours in TRAFFIC_LAGS:
        features[f"traffic_{hours}h_ago"] = observed.reindex(
            timestamp - pd.Timedelta(hours=hours)
        ).to_numpy()

    features[TARGET_COLUMN] = observed.reindex(timestamp + pd.Timedelta(hours=1)).to_numpy()

    for column in weather_columns:
        observed_weather = pd.Series(features[column].to_numpy(), index=timestamp)
        for hours in WEATHER_LAGS:
            # The fixed one-hour minimum delay is a documented conservative
            # operational assumption. Exact timestamp lookup prevents a value
            # from being shifted across a missing weather observation.
            features[f"{column}_{hours}h_ago"] = observed_weather.reindex(
                timestamp - pd.Timedelta(hours=hours)
            ).to_numpy()
    return features
