import pandas as pd

from src.features.weather_derivatives import SeasonalWeatherAnomaly, add_weather_derivatives


def test_weather_derivatives_use_exact_history_and_leave_a_gap_missing() -> None:
    timestamps = pd.date_range("2024-01-01", periods=30, freq="h", tz="UTC")
    features = pd.DataFrame(
        {
            "timestamp": timestamps,
            "hour": timestamps.tz_convert("Europe/Oslo").hour,
            "temperature_c": 5.0,
            "precipitation_mm": 1.0,
            "wind_speed_m_s": 3.0,
        }
    )
    features.loc[10, "precipitation_mm"] = None

    result = add_weather_derivatives(features)

    assert result.loc[25, "precipitation_previous_6h_mm"] == 6.0
    assert pd.isna(result.loc[16, "precipitation_previous_6h_mm"])
    assert result.loc[5, "rain_started_at_t_minus_1"] == 0


def test_seasonal_anomaly_is_fit_without_validation_values() -> None:
    train = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2023-01-01 01:00+00:00", "2023-01-02 01:00+00:00"]),
            "temperature_c_1h_ago": [2.0, 4.0],
            "wind_speed_m_s_1h_ago": [1.0, 3.0],
        }
    )
    validation = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 01:00+00:00"]),
            "temperature_c_1h_ago": [15.0],
            "wind_speed_m_s_1h_ago": [10.0],
        }
    )

    result = SeasonalWeatherAnomaly().fit(train).transform(validation)

    assert result.loc[0, "temperature_seasonal_anomaly_c"] == 12.0
    assert result.loc[0, "wind_speed_seasonal_anomaly_m_s"] == 8.0
