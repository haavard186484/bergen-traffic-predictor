import numpy as np
import pandas as pd

from src.evaluation.weather_error_analysis import add_weather_bands, daily_error_summary


def test_weather_bands_keep_missing_weather_explicit() -> None:
    data = pd.DataFrame(
        {
            "precipitation_mm_t_minus_1": [0.0, 0.2, np.nan],
            "wind_speed_m_s_t_minus_1": [3.9, 4.0, 8.0],
            "temperature_c_t_minus_1": [-0.1, 0.0, 10.0],
        }
    )

    result = add_weather_bands(data)

    assert result["rain"].tolist() == ["no_rain", "rain", pd.NA]
    assert result["wind_band"].astype("string").tolist() == ["under_4_m_s", "4_to_under_8_m_s", "8_m_s_or_more"]
    assert result["temperature_band"].astype("string").tolist() == ["below_0_c", "0_to_under_5_c", "10_c_or_more"]


def test_daily_error_summary_uses_target_local_date_and_excludes_incomplete_days() -> None:
    data = pd.DataFrame(
        {
            "target_local_timestamp": pd.date_range("2024-01-01", periods=23, freq="h", tz="Europe/Oslo").append(
                pd.date_range("2024-01-02", periods=20, freq="h", tz="Europe/Oslo")
            ),
            "absolute_error": [1.0] * 23 + [3.0] * 20,
            "signed_error": [-1.0] * 23 + [3.0] * 20,
        }
    )

    result = daily_error_summary(data, minimum_observations=20)

    assert result.index.tolist()[0].isoformat() == "2024-01-02"
    assert result.loc[pd.Timestamp("2024-01-02").date(), "mean_signed_error"] == 3.0
