import pandas as pd
import pytest

from src.features.build_features import feature_columns
from src.models.prediction import (
    CALENDAR_COLUMNS,
    PredictionInputError,
    build_prediction_features,
    forecast_timestamp,
)


def test_prediction_features_reuse_frozen_calendar_schema() -> None:
    result = build_prediction_features(
        pd.Timestamp("2025-01-02 12:00"), {1: 101, 2: 102, 24: 103, 168: 104}
    )

    assert tuple(result.columns) == CALENDAR_COLUMNS
    assert CALENDAR_COLUMNS == feature_columns(calendar_event_features=True)
    assert result.iloc[0]["traffic_1h_ago"] == 101
    assert result.iloc[0]["traffic_168h_ago"] == 104
    assert result.iloc[0]["hour"] == 12


def test_prediction_requires_every_traffic_lag() -> None:
    with pytest.raises(PredictionInputError, match="t−24"):
        build_prediction_features(
            pd.Timestamp("2025-01-02 12:00"), {1: 101, 2: 102, 24: None, 168: 104}
        )


def test_naive_timestamp_is_interpreted_in_oslo() -> None:
    result = forecast_timestamp(pd.Timestamp("2025-01-02 12:00"))

    assert result == pd.Timestamp("2025-01-02 12:00", tz="Europe/Oslo")


def test_prediction_timestamp_must_be_an_exact_hour() -> None:
    with pytest.raises(PredictionInputError, match="hel time"):
        forecast_timestamp(pd.Timestamp("2025-01-02 12:30"))
