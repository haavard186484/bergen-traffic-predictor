import pandas as pd

from src.evaluation.traffic_eda import (
    assign_chronological_split,
    missing_value_gaps,
    prepare_traffic_for_eda,
)


def test_missing_value_gaps_reports_contiguous_runs_in_local_time() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
            "traffic_volume": [1.0, None, None, 4.0, None],
        }
    )

    gaps = missing_value_gaps(prepare_traffic_for_eda(data))

    assert gaps["hours"].tolist() == [2, 1]
    assert gaps.loc[0, "start"] == pd.Timestamp("2024-01-01 02:00", tz="Europe/Oslo")
    assert gaps.loc[0, "end"] == pd.Timestamp("2024-01-01 03:00", tz="Europe/Oslo")


def test_chronological_split_uses_local_calendar_boundaries() -> None:
    data = pd.DataFrame(
        {
            "timestamp": [
                "2023-12-31T22:00:00Z",  # 23:00 in Oslo, train
                "2023-12-31T23:00:00Z",  # 00:00 in Oslo, validation
                "2024-12-31T23:00:00Z",  # 00:00 in Oslo, test
            ],
            "traffic_volume": [1, 2, 3],
        }
    )

    splits = assign_chronological_split(prepare_traffic_for_eda(data))

    assert splits.tolist() == ["train", "validation", "test"]
