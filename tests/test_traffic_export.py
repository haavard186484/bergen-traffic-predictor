import pandas as pd

from src.data.traffic_export import feasibility_report, read_hourly_traffic_export


def test_read_hourly_export_prefers_total_rows(tmp_path) -> None:
    export = tmp_path / "traffic.csv"
    export.write_text(
        "Fra;Trafikkmengde;Felt\n"
        "2025-01-01T00:00:00Z;10;Totalt\n"
        "2025-01-01T00:00:00Z;4;Felt 1\n",
        encoding="utf-8",
    )

    result = read_hourly_traffic_export(export)

    assert result.to_dict("records") == [
        {"timestamp": pd.Timestamp("2025-01-01T00:00:00Z"), "traffic_volume": 10}
    ]


def test_feasibility_report_counts_missing_hours() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-01-01T00:00:00Z", "2025-01-01T02:00:00Z"]),
            "traffic_volume": [10, 11],
        }
    )

    report = feasibility_report(data)

    assert report["missing_hours"] == 1
    assert report["coverage_percent"] == 100.0
