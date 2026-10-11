"""Fetch the exact traffic history required for an operational forecast."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.config import TRAFFIC_POINT_ID
from src.data.traffic_api import download_hourly_traffic
from src.features.build_features import TRAFFIC_LAGS

TrafficDownloader = Callable[[str, str, str], pd.DataFrame]


def fetch_required_traffic_history(
    forecast_timestamp: pd.Timestamp,
    point_id: str = TRAFFIC_POINT_ID,
    downloader: TrafficDownloader = download_hourly_traffic,
) -> dict[int, float | None]:
    """Fetch traffic at the exact lag timestamps needed by the frozen model.

    The API interval is deliberately bounded to the oldest required lag through
    ``t``. Missing rows or volumes remain ``None`` and are handled explicitly
    by the prediction layer; they are never interpolated or shifted.
    """
    timestamp = pd.Timestamp(forecast_timestamp)
    if timestamp.tzinfo is None:
        raise ValueError("Forecast-tidspunktet må ha tidssone.")
    timestamp = timestamp.tz_convert("UTC")
    data = downloader(
        point_id,
        (timestamp - pd.Timedelta(hours=max(TRAFFIC_LAGS))).isoformat(),
        timestamp.isoformat(),
    )
    required_columns = {"Fra", "Trafikkmengde"}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise RuntimeError(f"Trafikkdata-API mangler kolonner: {sorted(missing_columns)}")

    observed = data.copy()
    observed["timestamp"] = pd.to_datetime(observed["Fra"], utc=True, errors="coerce")
    if observed["timestamp"].isna().any() or observed["timestamp"].duplicated().any():
        raise RuntimeError("Trafikkdata-API returnerte ugyldige eller dupliserte tidspunkter.")
    values = pd.to_numeric(observed["Trafikkmengde"], errors="coerce")
    by_timestamp = pd.Series(values.to_numpy(), index=observed["timestamp"])

    history: dict[int, float | None] = {}
    for lag in TRAFFIC_LAGS:
        value = by_timestamp.get(timestamp - pd.Timedelta(hours=lag))
        history[lag] = float(value) if value is not None and pd.notna(value) else None
    return history
