import numpy as np
import pandas as pd

from scripts.run_weather_model import evaluate_weather_against_traffic


def test_weather_comparison_uses_same_2024_forecast_rows_for_every_model() -> None:
    timestamps = pd.date_range("2022-01-01", "2026-01-01", freq="h", inclusive="left", tz="UTC")
    data = pd.DataFrame(
        {
            "timestamp": timestamps,
            "traffic_volume": 500 + 100 * np.sin(np.arange(len(timestamps)) / 24),
            "temperature_c": 5 + np.sin(np.arange(len(timestamps)) / 100),
            "precipitation_mm": 0.0,
            "wind_speed_m_s": 3.0,
        }
    )

    result = evaluate_weather_against_traffic(data)

    assert set(result.index) == {
        "traffic_only_hist_gradient_boosting",
        "weather_augmented_hist_gradient_boosting",
        "previous_week_baseline",
    }
    assert result["evaluated_predictions"].nunique() == 1
    assert result["evaluated_predictions"].iloc[0] > 8_000
