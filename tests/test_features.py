import pandas as pd

from src.config import TARGET_COLUMN
from src.features.build_features import create_features, feature_columns


def test_create_features_uses_past_traffic_and_next_hour_target() -> None:
    timestamps = pd.date_range("2025-01-01", periods=170, freq="h", tz="UTC")
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(170)})

    result = create_features(data)

    assert result.loc[168, "traffic_168h_ago"] == 0
    assert result.loc[10, TARGET_COLUMN] == 11
    assert pd.isna(result.loc[0, "traffic_1h_ago"])
    assert pd.isna(result.loc[169, TARGET_COLUMN])


def test_create_features_does_not_shift_values_across_missing_timestamp() -> None:
    timestamps = pd.date_range("2025-01-01", periods=30, freq="h", tz="UTC").delete(10)
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(len(timestamps))})

    result = create_features(data)
    row_at_11 = result.index[result["timestamp"] == pd.Timestamp("2025-01-01 11:00", tz="UTC")][0]
    row_at_9 = result.index[result["timestamp"] == pd.Timestamp("2025-01-01 09:00", tz="UTC")][0]

    assert pd.isna(result.loc[row_at_11, "traffic_1h_ago"])
    assert pd.isna(result.loc[row_at_9, TARGET_COLUMN])


def test_calendar_features_use_europe_oslo_not_utc() -> None:
    data = pd.DataFrame(
        {"timestamp": [pd.Timestamp("2025-01-01 23:00", tz="UTC")], "traffic_volume": [100]}
    )

    result = create_features(data)

    assert result.loc[0, "hour"] == 0
    assert result.loc[0, "day_of_week"] == 3


def test_weather_features_use_exact_conservative_lags() -> None:
    timestamps = pd.date_range("2025-01-01", periods=26, freq="h", tz="UTC")
    data = pd.DataFrame(
        {"timestamp": timestamps, "traffic_volume": range(26), "temperature_c": range(100, 126)}
    )

    result = create_features(data, weather_columns=("temperature_c",))

    assert result.loc[24, "temperature_c_1h_ago"] == 123
    assert result.loc[24, "temperature_c_2h_ago"] == 122
    assert result.loc[24, "temperature_c_24h_ago"] == 100
    assert "temperature_c" not in feature_columns(("temperature_c",))


def test_weather_lags_do_not_shift_across_a_missing_timestamp() -> None:
    timestamps = pd.date_range("2025-01-01", periods=30, freq="h", tz="UTC").delete(10)
    data = pd.DataFrame(
        {"timestamp": timestamps, "traffic_volume": range(len(timestamps)), "temperature_c": range(len(timestamps))}
    )

    result = create_features(data, weather_columns=("temperature_c",))
    row_at_11 = result.index[result["timestamp"] == pd.Timestamp("2025-01-01 11:00", tz="UTC")][0]

    assert pd.isna(result.loc[row_at_11, "temperature_c_1h_ago"])
