"""Derived, conservative weather features for one-hour-ahead forecasts."""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd

from src.config import TIMEZONE

DERIVED_WEATHER_FEATURE_COLUMNS = (
    "precipitation_previous_6h_mm",
    "precipitation_previous_24h_mm",
    "rain_started_at_t_minus_1",
    "rain_during_rush_hour",
    "temperature_seasonal_anomaly_c",
    "wind_speed_seasonal_anomaly_m_s",
)


def _lagged_weather(features: pd.DataFrame, column: str, hours: int) -> pd.Series:
    """Look up one weather value at an exact prior UTC timestamp."""
    timestamp = pd.to_datetime(features["timestamp"], utc=True)
    observed = pd.Series(features[column].to_numpy(), index=timestamp)
    return pd.Series(
        observed.reindex(timestamp - pd.Timedelta(hours=hours)).to_numpy(), index=features.index
    )


def add_weather_derivatives(features: pd.DataFrame) -> pd.DataFrame:
    """Add weather history features available no later than ``t - 1``.

    Aggregate values remain missing when any exact hourly observation in their
    window is missing. No weather value is imputed or shifted over a gap.
    """
    required = {"timestamp", "hour", "precipitation_mm", "temperature_c", "wind_speed_m_s"}
    missing = required.difference(features.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    result = features.copy()
    precipitation = pd.concat(
        [_lagged_weather(result, "precipitation_mm", hours) for hours in range(1, 25)], axis=1
    )
    precipitation.columns = range(1, 25)
    result["precipitation_previous_6h_mm"] = precipitation.loc[:, 1:6].sum(
        axis=1, min_count=6
    )
    result["precipitation_previous_24h_mm"] = precipitation.sum(axis=1, min_count=24)
    one_hour_ago = precipitation[1]
    two_hours_ago = precipitation[2]
    rain_start = pd.Series(np.nan, index=result.index)
    known_transition = one_hour_ago.notna() & two_hours_ago.notna()
    rain_start.loc[known_transition] = (
        one_hour_ago.loc[known_transition].gt(0) & two_hours_ago.loc[known_transition].eq(0)
    ).astype(int)
    result["rain_started_at_t_minus_1"] = rain_start
    rain_indicator = pd.Series(np.nan, index=result.index)
    rain_indicator.loc[one_hour_ago.notna()] = one_hour_ago.loc[one_hour_ago.notna()].gt(0).astype(int)
    is_rush_hour = result["hour"].isin((6, 7, 8, 14, 15, 16)).astype(int)
    result["rain_during_rush_hour"] = rain_indicator * is_rush_hour
    return result


class SeasonalWeatherAnomaly:
    """Fit seasonal weather medians on training rows and apply them later.

    Normals are keyed by local calendar month and local hour of the weather
    observation at ``t - 1``. They are fitted separately in every chronological
    training fold, so validation and test weather cannot affect the normal.
    """

    _RAW_COLUMNS: ClassVar[dict[str, str]] = {
        "temperature_c_1h_ago": "temperature_seasonal_anomaly_c",
        "wind_speed_m_s_1h_ago": "wind_speed_seasonal_anomaly_m_s",
    }

    def fit(self, data: pd.DataFrame) -> SeasonalWeatherAnomaly:
        weather_time = pd.to_datetime(data["timestamp"], utc=True) - pd.Timedelta(hours=1)
        local_time = weather_time.dt.tz_convert(TIMEZONE)
        grouped = pd.DataFrame(
            {
                "month": local_time.dt.month,
                "hour": local_time.dt.hour,
                **{column: data[column] for column in self._RAW_COLUMNS},
            }
        )
        self.normals_ = grouped.groupby(["month", "hour"], observed=True).median()
        self.global_normals_ = grouped[list(self._RAW_COLUMNS)].median()
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        if not hasattr(self, "normals_"):
            raise RuntimeError("SeasonalWeatherAnomaly must be fitted before transform")
        result = data.copy()
        weather_time = pd.to_datetime(result["timestamp"], utc=True) - pd.Timedelta(hours=1)
        local_time = weather_time.dt.tz_convert(TIMEZONE)
        keys = pd.MultiIndex.from_arrays([local_time.dt.month, local_time.dt.hour])
        for raw_column, anomaly_column in self._RAW_COLUMNS.items():
            normal = self.normals_[raw_column].reindex(keys).to_numpy()
            normal = pd.Series(normal, index=result.index).fillna(self.global_normals_[raw_column])
            result[anomaly_column] = result[raw_column] - normal
        return result
