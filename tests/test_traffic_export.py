import pandas as pd
import pytest

from src.data.prepare_traffic import (
    prepare_traffic_dataset,
    prepare_traffic_datasets,
    write_traffic_dataset,
)
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


def test_prepare_traffic_dataset_writes_normalized_data_and_metadata(tmp_path) -> None:
    export = tmp_path / "traffic.csv"
    export.write_text(
        "Trafikkregistreringspunkt;Fra;Trafikkmengde;Felt\n"
        "14630V805616;2025-01-01T00:00:00Z;10;Totalt\n"
        "14630V805616;2025-01-01T01:00:00Z;11;Totalt\n",
        encoding="utf-8",
    )

    data, report = prepare_traffic_dataset(export)
    output = write_traffic_dataset(data, report, export, tmp_path / "processed.csv")

    assert output.exists()
    assert output.with_suffix(".metadata.json").exists()
    assert pd.read_csv(output)["traffic_volume"].tolist() == [10, 11]


def test_prepare_traffic_dataset_rejects_missing_hours(tmp_path) -> None:
    export = tmp_path / "traffic.csv"
    export.write_text(
        "Fra;Trafikkmengde;Felt\n"
        "2025-01-01T00:00:00Z;10;Totalt\n"
        "2025-01-01T02:00:00Z;11;Totalt\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing_hours=1"):
        prepare_traffic_dataset(export)


def test_prepare_traffic_dataset_preserves_missing_hours_when_requested(tmp_path) -> None:
    export = tmp_path / "traffic.csv"
    export.write_text(
        "Fra;Trafikkmengde;Felt\n"
        "2025-01-01T00:00:00Z;10;Totalt\n"
        "2025-01-01T02:00:00Z;11;Totalt\n",
        encoding="utf-8",
    )

    data, report = prepare_traffic_dataset(export, allow_gaps=True)

    assert len(data) == 3
    assert pd.isna(data.loc[1, "traffic_volume"])
    assert report["missing_hours"] == 1


def test_prepare_traffic_datasets_combines_yearly_exports(tmp_path) -> None:
    first = tmp_path / "traffic_2022.csv"
    second = tmp_path / "traffic_2023.csv"
    first.write_text(
        "Fra;Trafikkmengde;Felt\n2025-01-01T00:00:00Z;10;Totalt\n",
        encoding="utf-8",
    )
    second.write_text(
        "Fra;Trafikkmengde;Felt\n2025-01-01T01:00:00Z;11;Totalt\n",
        encoding="utf-8",
    )

    data, report = prepare_traffic_datasets([second, first])

    assert data["traffic_volume"].tolist() == [10, 11]
    assert report["missing_hours"] == 0
