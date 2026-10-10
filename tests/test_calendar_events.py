from datetime import date

import pandas as pd

from src.features.build_features import create_features, feature_columns
from src.features.calendar_events import (
    add_norwegian_calendar_event_features,
    easter_sunday,
    norwegian_public_holidays,
)


def test_norwegian_public_holidays_include_movable_and_fixed_dates() -> None:
    assert easter_sunday(2024) == date(2024, 3, 31)
    holidays = norwegian_public_holidays(2024)
    assert {date(2024, 4, 1), date(2024, 5, 9), date(2024, 5, 17)}.issubset(holidays)


def test_calendar_event_features_are_local_and_keep_timezone() -> None:
    data = pd.DataFrame(
        {"local_timestamp": pd.to_datetime(["2024-05-16 12:00", "2024-05-17 12:00", "2024-05-18 12:00"]).tz_localize("Europe/Oslo")}
    )

    result = add_norwegian_calendar_event_features(data)

    assert result["local_timestamp"].dt.tz is not None
    assert result["is_day_before_public_holiday"].tolist() == [1, 0, 0]
    assert result["is_public_holiday"].tolist() == [0, 1, 0]
    assert result["is_day_after_public_holiday"].tolist() == [0, 0, 1]


def test_feature_builder_adds_calendar_events_only_when_requested() -> None:
    timestamps = pd.date_range("2024-05-16", periods=30, freq="h", tz="UTC")
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(len(timestamps))})

    result = create_features(data, calendar_event_features=True)

    assert "is_public_holiday" in result
    assert "is_public_holiday" in feature_columns(calendar_event_features=True)
