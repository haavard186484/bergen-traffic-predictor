from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pandas as pd
import pytest

from src.data.frost import (
    download_hourly_weather,
    parse_hourly_observations,
    write_weather_dataset,
)


def test_download_weather_uses_frost_basic_auth_and_requested_elements(monkeypatch) -> None:
    requests: list[Request] = []
    monkeypatch.setenv("FROST_CLIENT_ID", "client-id")

    def send_request(request: Request) -> dict:
        requests.append(request)
        return {
            "data": [
                {
                    "referenceTime": "2025-01-01T00:00:00Z",
                    "observations": [
                        {"elementId": "air_temperature", "value": 3.5},
                        {"elementId": "sum(precipitation_amount PT1H)", "value": 1.2},
                        {"elementId": "wind_speed", "value": 4.0},
                    ],
                }
            ]
        }

    weather = download_hourly_weather(
        "SN50540", "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z", send_request=send_request
    )

    query = parse_qs(urlparse(requests[0].full_url).query)
    auth = requests[0].get_header("Authorization")
    assert base64.b64decode(auth.removeprefix("Basic ")).decode() == "client-id:"
    assert query["sources"] == ["SN50540"]
    assert set(query["elements"][0].split(",")) == {
        "air_temperature", "sum(precipitation_amount PT1H)", "wind_speed"
    }
    assert weather.loc[0, "temperature_c"] == 3.5
    assert weather.loc[0, "precipitation_mm"] == 1.2
    assert weather.loc[0, "wind_speed_m_s"] == 4.0


def test_download_weather_requires_environment_client_id(monkeypatch) -> None:
    monkeypatch.delenv("FROST_CLIENT_ID", raising=False)

    with pytest.raises(RuntimeError, match="FROST_CLIENT_ID"):
        download_hourly_weather("SN50540", "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z")


def test_parse_weather_preserves_missing_elements() -> None:
    result = parse_hourly_observations(
        [{"data": [{"referenceTime": "2025-01-01T00:00:00Z", "observations": [{"elementId": "wind_speed", "value": 2}]}]}]
    )

    assert pd.isna(result.loc[0, "temperature_c"])
    assert pd.isna(result.loc[0, "precipitation_mm"])
    assert result.loc[0, "wind_speed_m_s"] == 2


def test_parse_weather_rejects_ambiguous_same_element() -> None:
    payload = {
        "data": [{"referenceTime": "2025-01-01T00:00:00Z", "observations": [
            {"elementId": "air_temperature", "value": 1}, {"elementId": "air_temperature", "value": 2}
        ]}]
    }
    with pytest.raises(ValueError, match="Multiple"):
        parse_hourly_observations([payload])


def test_weather_metadata_records_coverage_without_credentials(tmp_path) -> None:
    weather = pd.DataFrame({"timestamp": [pd.Timestamp("2025-01-01T00:00:00Z")], "temperature_c": [1.0], "precipitation_mm": [None], "wind_speed_m_s": [2.0]})
    output = write_weather_dataset(weather, tmp_path / "weather.csv", station_id="SN50540", start="2025-01-01T00:00:00Z", end="2025-01-01T02:00:00Z")

    metadata = json.loads(output.with_suffix(".metadata.json").read_text())
    assert metadata["coverage"] == {"temperature_c": 1, "precipitation_mm": 0, "wind_speed_m_s": 1, "temperature_c_missing": 1, "precipitation_mm_missing": 2, "wind_speed_m_s_missing": 1}
    assert "client" not in json.dumps(metadata).lower()

