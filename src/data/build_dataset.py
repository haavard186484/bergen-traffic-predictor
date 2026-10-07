"""Combine validated traffic and weather data into one hourly dataset."""

import pandas as pd


def build_hourly_dataset(traffic: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Join traffic and weather observations on an hourly UTC timestamp.

    Both inputs must contain ``timestamp``. Traffic is retained even where no
    weather observation exists, making missing weather explicit for later
    handling.
    """
    for name, frame in {"traffic": traffic, "weather": weather}.items():
        if "timestamp" not in frame.columns:
            raise ValueError(f"{name} data must contain a 'timestamp' column")

    traffic = traffic.copy()
    weather = weather.copy()
    traffic["timestamp"] = pd.to_datetime(traffic["timestamp"], utc=True)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"], utc=True)

    return traffic.merge(weather, on="timestamp", how="left", validate="one_to_one")
