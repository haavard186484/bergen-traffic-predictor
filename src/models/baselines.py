"""Simple, transparent forecasting baselines."""

import pandas as pd


def previous_week_baseline(data: pd.DataFrame, traffic_column: str = "traffic_volume") -> pd.Series:
    """Predict each hour from the observed volume 168 rows earlier."""
    if traffic_column not in data.columns:
        raise ValueError(f"Missing traffic column: {traffic_column}")
    return data[traffic_column].shift(168).rename("previous_week_prediction")
