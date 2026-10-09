"""Client for Statens vegvesen's Traffic Data GraphQL API."""

import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


API_URL = "https://trafikkdata-api.atlas.vegvesen.no"
PAGE_SIZE = 100
POINT_ID_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
JsonRequest = Callable[[Request], dict[str, Any]]


def _query(point_id: str, start: str, end: str, cursor: str | None) -> str:
    """Build a bounded hourly-volume query, optionally after a cursor."""
    after = f", after: {json.dumps(cursor)}" if cursor else ""
    return f"""
    {{
      trafficData(trafficRegistrationPointId: {json.dumps(point_id)}) {{
        volume {{
          byHour(from: {json.dumps(start)}, to: {json.dumps(end)}, first: {PAGE_SIZE}{after}) {{
            edges {{
              cursor
              node {{
                from
                total {{
                  volumeNumbers {{ volume }}
                  coverage {{ percentage }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """


def _post_json(request: Request) -> dict[str, Any]:
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed public API URL
        return json.load(response)


def _fetch_page(query: str, send_request: JsonRequest) -> dict[str, Any]:
    request = Request(
        API_URL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        payload = send_request(request)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Trafikkdata-API-kallet feilet: {error}") from error

    if payload.get("errors"):
        raise RuntimeError(f"Trafikkdata-API returnerte feil: {payload['errors']}")
    return payload


def download_hourly_traffic(
    point_id: str,
    start: str,
    end: str,
    send_request: JsonRequest = _post_json,
) -> pd.DataFrame:
    """Download all hourly total-volume observations for a point and period.

    The API limits each page to 100 hours. This function follows the cursor
    until every page in the requested period has been collected.
    """
    if not POINT_ID_PATTERN.fullmatch(point_id):
        raise ValueError("Ugyldig trafikkregistreringspunkt-ID")

    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload = _fetch_page(_query(point_id, start, end, cursor), send_request)
        edges = payload["data"]["trafficData"]["volume"]["byHour"]["edges"]
        if not edges:
            break

        for edge in edges:
            node = edge["node"]
            total = node.get("total") or {}
            volume_numbers = total.get("volumeNumbers") or {}
            coverage = total.get("coverage") or {}
            rows.append(
                {
                    "Trafikkregistreringspunkt": point_id,
                    "Fra": node["from"],
                    "Trafikkmengde": volume_numbers.get("volume"),
                    "Felt": "Totalt",
                    "Dekningsgrad (%)": coverage.get("percentage"),
                }
            )

        next_cursor = edges[-1]["cursor"]
        if next_cursor == cursor:
            raise RuntimeError("API-pagineringen stoppet uten å gå fremover")
        cursor = next_cursor
        time.sleep(0.05)

    return pd.DataFrame(rows)


def write_api_export(
    data: pd.DataFrame, point_id: str, start: str, end: str, output_path: str | Path
) -> Path:
    """Save an API download in the same raw format accepted by the pipeline."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, sep=";", decimal=",", index=False)
    metadata = {
        "source": API_URL,
        "traffic_point_id": point_id,
        "from": start,
        "to": end,
        "fetched_at": datetime.now(UTC).isoformat(),
        "rows": len(data),
    }
    output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return output
