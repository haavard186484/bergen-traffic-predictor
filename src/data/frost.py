"""Reproducible retrieval and validation of hourly MET Norway Frost data.

Frost observations are archived measurements. Their ``referenceTime`` is the
time being measured. The feature pipeline applies a documented one-hour
minimum lag before using these values in a forecast.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

FROST_OBSERVATIONS_URL = "https://frost.met.no/observations/v0.jsonld"
FROST_AVAILABLE_SERIES_URL = "https://frost.met.no/observations/availableTimeSeries/v0.jsonld"
DEFAULT_STATION_ID = "SN50540"  # Bergen - Florida; availability is verified on download.
FROST_ELEMENTS = {
    "air_temperature": "temperature_c",
    "sum(precipitation_amount PT1H)": "precipitation_mm",
    "wind_speed": "wind_speed_m_s",
}
WEATHER_COLUMNS = tuple(FROST_ELEMENTS.values())
JsonRequest = Callable[[Request], dict[str, Any]]


def frost_client_id_from_environment() -> str:
    """Read the Frost client ID without accepting credentials in code or CLI args."""
    client_id = os.environ.get("FROST_CLIENT_ID")
    if not client_id:
        raise RuntimeError("FROST_CLIENT_ID must be set in the environment")
    return client_id


def _get_json(request: Request) -> dict[str, Any]:
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def _request(url: str, client_id: str, send_request: JsonRequest) -> dict[str, Any]:
    token = base64.b64encode(f"{client_id}:".encode()).decode("ascii")
    request = Request(url, headers={"Accept": "application/json", "Authorization": f"Basic {token}"})
    try:
        payload = send_request(request)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Frost API call failed: {error}") from error
    if "error" in payload:
        error = payload["error"]
        raise RuntimeError(f"Frost API returned an error: {error}")
    return payload


def _month_intervals(start: str, end: str) -> Iterable[tuple[pd.Timestamp, pd.Timestamp]]:
    """Yield bounded UTC intervals so four years do not become one huge request."""
    current = pd.to_datetime(start, utc=True)
    finish = pd.to_datetime(end, utc=True)
    if current >= finish:
        raise ValueError("start must be before end")
    while current < finish:
        next_month = current.normalize() + pd.offsets.MonthBegin(1)
        interval_end = min(next_month, finish)
        yield current, interval_end
        current = interval_end


def _observation_url(station_id: str, start: pd.Timestamp, end: pd.Timestamp) -> str:
    # Frost interval endpoints are inclusive.  Use the last whole instant in
    # this half-open interval, avoiding duplicated month-boundary observations.
    inclusive_end = end - pd.Timedelta(hours=1)
    params = {
        "sources": station_id,
        "referencetime": f"{start.isoformat()}/{inclusive_end.isoformat()}",
        "elements": ",".join(FROST_ELEMENTS),
        "timeoffsets": "default",
        "levels": "default",
        "qualities": "0,1,2,3,4",
    }
    return f"{FROST_OBSERVATIONS_URL}?{urlencode(params)}"


def parse_hourly_observations(payloads: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Turn Frost response objects into one explicit, UTC hourly row per time.

    Multiple sensors for one requested element are rejected instead of being
    silently picked.  Users can then constrain the source/sensor deliberately.
    Missing element values stay missing.
    """
    records: list[dict[str, Any]] = []
    for payload in payloads:
        for item in payload.get("data", []):
            timestamp = pd.to_datetime(item["referenceTime"], utc=True)
            values: dict[str, float] = {}
            for observation in item.get("observations", []):
                element = observation.get("elementId")
                column = FROST_ELEMENTS.get(element)
                if column is None or "value" not in observation:
                    continue
                if column in values:
                    raise ValueError(
                        f"Multiple {element!r} observations at {timestamp}; constrain Frost sensor settings"
                    )
                values[column] = float(observation["value"])
            if values:
                records.append({"timestamp": timestamp, **values})
    if not records:
        return pd.DataFrame(columns=["timestamp", *WEATHER_COLUMNS])
    weather = pd.DataFrame(records).groupby("timestamp", as_index=False).first()
    weather = weather.sort_values("timestamp").reset_index(drop=True)
    if weather["timestamp"].duplicated().any():
        raise ValueError("Frost data contains duplicate timestamps")
    return weather.reindex(columns=["timestamp", *WEATHER_COLUMNS])


def download_hourly_weather(
    station_id: str,
    start: str,
    end: str,
    send_request: JsonRequest = _get_json,
) -> pd.DataFrame:
    """Download selected hourly observations in bounded requests from Frost."""
    credentials = frost_client_id_from_environment()
    payloads = [
        _request(_observation_url(station_id, interval_start, interval_end), credentials, send_request)
        for interval_start, interval_end in _month_intervals(start, end)
    ]
    return parse_hourly_observations(payloads)


def available_time_series(
    station_id: str, start: str, end: str, send_request: JsonRequest = _get_json,
) -> dict[str, Any]:
    """Return Frost's station/element availability response for audit metadata."""
    credentials = frost_client_id_from_environment()
    params = {"sources": station_id, "referencetime": f"{start}/{end}", "elements": ",".join(FROST_ELEMENTS)}
    return _request(f"{FROST_AVAILABLE_SERIES_URL}?{urlencode(params)}", credentials, send_request)


def weather_coverage_summary(weather: pd.DataFrame, start: str, end: str) -> dict[str, int]:
    """Count hourly observations and explicit missing values on a full UTC axis."""
    axis = pd.date_range(pd.to_datetime(start, utc=True), pd.to_datetime(end, utc=True), freq="h", inclusive="left")
    indexed = weather.set_index("timestamp").reindex(axis)
    return {column: int(indexed[column].notna().sum()) for column in WEATHER_COLUMNS} | {
        f"{column}_missing": int(indexed[column].isna().sum()) for column in WEATHER_COLUMNS
    }


def write_weather_dataset(
    weather: pd.DataFrame, output_path: str | Path, *, station_id: str, start: str, end: str,
    availability: dict[str, Any] | None = None,
) -> Path:
    """Write local generated weather data and auditable, secret-free metadata."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    weather.to_csv(output, index=False)
    metadata = {
        "source": FROST_OBSERVATIONS_URL,
        "station_id": station_id,
        "requested_from": start,
        "requested_to": end,
        "elements": FROST_ELEMENTS,
        "fetched_at": datetime.now(UTC).isoformat(),
        "coverage": weather_coverage_summary(weather, start, end),
        "availability_response": availability,
        "feature_availability_assumption": (
            "Forecast features use only exact weather observations at least one hour old. "
            "This is a conservative project assumption; Frost referenceTime is not a publication timestamp."
        ),
    }
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output
