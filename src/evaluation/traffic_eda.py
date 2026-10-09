"""Reproducible summaries for the hourly traffic time series."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.config import TIMEZONE


@dataclass(frozen=True)
class TimeSplit:
    """A named, half-open chronological time interval in local time."""

    name: str
    start: str
    end: str


CHRONOLOGICAL_SPLITS = (
    TimeSplit("train", "2022-01-01", "2024-01-01"),
    TimeSplit("validation", "2024-01-01", "2025-01-01"),
    TimeSplit("test", "2025-01-01", "2026-01-01"),
)


def prepare_traffic_for_eda(data: pd.DataFrame) -> pd.DataFrame:
    """Validate timestamps and add local calendar columns without changing gaps."""
    required = {"timestamp", "traffic_volume"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    prepared = data.copy()
    prepared["timestamp"] = pd.to_datetime(prepared["timestamp"], utc=True)
    if prepared["timestamp"].isna().any() or prepared["timestamp"].duplicated().any():
        raise ValueError("Timestamps must be valid and unique")
    prepared = prepared.sort_values("timestamp").reset_index(drop=True)
    local_time = prepared["timestamp"].dt.tz_convert(TIMEZONE)
    prepared["local_timestamp"] = local_time
    prepared["hour"] = local_time.dt.hour
    prepared["weekday"] = local_time.dt.day_name()
    prepared["month"] = local_time.dt.month_name()
    prepared["is_weekend"] = local_time.dt.dayofweek >= 5
    return prepared


def assign_chronological_split(data: pd.DataFrame) -> pd.Series:
    """Assign the fixed 2022--2025 local-calendar train/validation/test split."""
    if "local_timestamp" not in data:
        raise ValueError("local_timestamp is required; call prepare_traffic_for_eda first")

    labels = pd.Series(pd.NA, index=data.index, dtype="string")
    for split in CHRONOLOGICAL_SPLITS:
        start = pd.Timestamp(split.start, tz=TIMEZONE)
        end = pd.Timestamp(split.end, tz=TIMEZONE)
        labels.loc[(data["local_timestamp"] >= start) & (data["local_timestamp"] < end)] = split.name
    return labels.rename("split")


def missing_value_gaps(data: pd.DataFrame) -> pd.DataFrame:
    """Return contiguous runs where the traffic value is unknown, unchanged."""
    missing = data["traffic_volume"].isna()
    starts = missing & ~missing.shift(fill_value=False)
    groups = starts.cumsum().where(missing)
    gaps = (
        data.loc[missing]
        .groupby(groups.loc[missing], sort=False)
        .agg(
            start=("local_timestamp", "min"),
            end=("local_timestamp", "max"),
            hours=("traffic_volume", "size"),
        )
        .reset_index(drop=True)
    )
    return gaps


def grouped_volume_summary(data: pd.DataFrame, column: str) -> pd.DataFrame:
    """Summarise observed hourly volume by one calendar grouping."""
    return (
        data.groupby(column, observed=True)["traffic_volume"]
        .agg(observations="count", mean="mean", median="median", minimum="min", maximum="max")
        .round(2)
    )


def traffic_quality_summary(data: pd.DataFrame) -> dict[str, float | int]:
    """Report zeroes and IQR-defined extremes while retaining missing values."""
    volume = data["traffic_volume"]
    observed = volume.dropna()
    first_quartile, third_quartile = observed.quantile([0.25, 0.75])
    iqr = third_quartile - first_quartile
    lower_bound = first_quartile - 1.5 * iqr
    upper_bound = third_quartile + 1.5 * iqr
    return {
        "hours": len(data),
        "observed_hours": int(observed.size),
        "missing_hours": int(volume.isna().sum()),
        "zero_hours": int((observed == 0).sum()),
        "minimum": float(observed.min()),
        "maximum": float(observed.max()),
        "p01": float(observed.quantile(0.01)),
        "p99": float(observed.quantile(0.99)),
        "iqr_lower_bound": float(lower_bound),
        "iqr_upper_bound": float(upper_bound),
        "iqr_extreme_hours": int(((observed < lower_bound) | (observed > upper_bound)).sum()),
    }
