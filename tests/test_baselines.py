import pandas as pd

from src.models.baselines import previous_week_baseline, previous_week_forecast_baseline


def test_previous_week_baseline_uses_exact_timestamp_not_row_position() -> None:
    timestamps = pd.date_range("2025-01-01", periods=180, freq="h", tz="UTC").delete(10)
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(len(timestamps))})

    prediction = previous_week_baseline(data)

    row_at_168_hours = data.index[data["timestamp"] == pd.Timestamp("2025-01-08 10:00", tz="UTC")][0]
    assert pd.isna(prediction.loc[row_at_168_hours])


def test_previous_week_baseline_keeps_missing_lag_as_missing_prediction() -> None:
    timestamps = pd.date_range("2025-01-01", periods=170, freq="h", tz="UTC")
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(170)})
    data.loc[0, "traffic_volume"] = float("nan")

    prediction = previous_week_baseline(data)

    assert pd.isna(prediction.iloc[168])
    assert prediction.iloc[169] == 1


def test_previous_week_forecast_baseline_predicts_next_hour_from_previous_week() -> None:
    timestamps = pd.date_range("2025-01-01", periods=170, freq="h", tz="UTC")
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(170)})

    prediction = previous_week_forecast_baseline(data)

    assert prediction.iloc[167] == 0
    assert pd.isna(prediction.iloc[166])
