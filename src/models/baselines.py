"""Simple, transparent forecasting baselines."""

import pandas as pd


def previous_week_baseline(data: pd.DataFrame, traffic_column: str = "traffic_volume") -> pd.Series:
    """Predict each timestamp from the observation exactly 168 hours earlier.

    The lookup is made by timestamp rather than by row position.  Consequently,
    an absent hour or an unknown observation at ``t - 168 hours`` results in a
    missing prediction; it is never replaced by the closest preceding row.
    """
    required = {"timestamp", traffic_column}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    timestamps = pd.to_datetime(data["timestamp"], utc=True)
    if timestamps.isna().any():
        raise ValueError("Timestamps must be valid")
    if timestamps.duplicated().any():
        raise ValueError("Timestamps must be unique for the previous-week baseline")

    observed = pd.Series(data[traffic_column].to_numpy(), index=timestamps)
    previous_week = observed.reindex(timestamps - pd.Timedelta(hours=168))
    return pd.Series(
        previous_week.to_numpy(), index=data.index, name="previous_week_prediction"
    )


def previous_week_forecast_baseline(
    data: pd.DataFrame, horizon_hours: int = 1, traffic_column: str = "traffic_volume"
) -> pd.Series:
    """Forecast ``t + horizon_hours`` from the same hour in the previous week.

    This is the comparable baseline for a one-hour-ahead feature row anchored
    at ``t``. As with :func:`previous_week_baseline`, both lookups are exact
    timestamps, so no observation can bridge a measurement gap.
    """
    if horizon_hours < 1:
        raise ValueError("horizon_hours must be at least one")
    required = {"timestamp", traffic_column}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    timestamps = pd.to_datetime(data["timestamp"], utc=True)
    if timestamps.isna().any() or timestamps.duplicated().any():
        raise ValueError("Timestamps must be valid and unique")
    observed = pd.Series(data[traffic_column].to_numpy(), index=timestamps)
    source_time = timestamps + pd.Timedelta(hours=horizon_hours - 168)
    return pd.Series(
        observed.reindex(source_time).to_numpy(),
        index=data.index,
        name="previous_week_forecast_prediction",
    )
