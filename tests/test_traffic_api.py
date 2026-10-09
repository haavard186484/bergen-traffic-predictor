from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

from src.data.traffic_api import download_hourly_traffic, write_api_export


def test_download_hourly_traffic_follows_api_cursors(tmp_path) -> None:
    calls: list[dict[str, Any]] = []
    responses = iter(
        [
            {
                "data": {
                    "trafficData": {
                        "volume": {
                            "byHour": {
                                "edges": [
                                    {
                                        "cursor": "first-cursor",
                                        "node": {
                                            "from": "2025-01-01T00:00:00+01:00",
                                            "total": {
                                                "volumeNumbers": {"volume": 10},
                                                "coverage": {"percentage": 100.0},
                                            },
                                        },
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            {
                "data": {
                    "trafficData": {
                        "volume": {
                            "byHour": {
                                "edges": [
                                    {
                                        "cursor": "second-cursor",
                                        "node": {
                                            "from": "2025-01-01T01:00:00+01:00",
                                            "total": {
                                                "volumeNumbers": {"volume": 12},
                                                "coverage": {"percentage": 99.0},
                                            },
                                        },
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            {"data": {"trafficData": {"volume": {"byHour": {"edges": []}}}}},
        ]
    )

    def send_request(request: Request) -> dict[str, Any]:
        calls.append(json.loads(request.data.decode("utf-8")))
        return next(responses)

    data = download_hourly_traffic(
        "14630V805616", "2025-01-01T00:00:00+01:00", "2025-01-01T02:00:00+01:00", send_request
    )
    output = write_api_export(data, "14630V805616", "start", "end", tmp_path / "traffic.csv")

    assert data["Trafikkmengde"].tolist() == [10, 12]
    assert "after" not in calls[0]["query"]
    assert "first-cursor" in calls[1]["query"]
    assert output.with_suffix(".metadata.json").exists()
