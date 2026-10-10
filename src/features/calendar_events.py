"""Norwegian calendar-event features calculated from local timestamps."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

CALENDAR_EVENT_FEATURE_COLUMNS = (
    "is_public_holiday",
    "is_day_before_public_holiday",
    "is_day_after_public_holiday",
    "is_christmas_new_year_period",
    "is_constitution_day",
)


def easter_sunday(year: int) -> date:
    """Return Gregorian Easter Sunday using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def norwegian_public_holidays(year: int) -> set[date]:
    """Return nationwide Norwegian public holidays needed by this project."""
    easter = easter_sunday(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=3),  # Maundy Thursday
        easter - timedelta(days=2),  # Good Friday
        easter + timedelta(days=1),  # Easter Monday
        date(year, 5, 1),
        date(year, 5, 17),
        easter + timedelta(days=39),  # Ascension Day
        easter + timedelta(days=50),  # Whit Monday
        date(year, 12, 25),
        date(year, 12, 26),
    }


def add_norwegian_calendar_event_features(data: pd.DataFrame) -> pd.DataFrame:
    """Add binary event features from timezone-aware ``local_timestamp``.

    The event flags are deterministic calendar information available before a
    forecast is made.  They do not alter timestamps or fill measurement gaps.
    """
    if "local_timestamp" not in data:
        raise ValueError("local_timestamp is required for calendar event features")
    result = data.copy()
    local_timestamp = pd.to_datetime(result["local_timestamp"])
    if local_timestamp.dt.tz is None:
        raise ValueError("local_timestamp must preserve its timezone")
    local_dates = local_timestamp.dt.date
    years = set(local_timestamp.dt.year.unique()) | {int(local_timestamp.dt.year.max()) + 1}
    holidays = set().union(*(norwegian_public_holidays(year) for year in years))
    result["is_public_holiday"] = local_dates.isin(holidays).astype(int)
    result["is_day_before_public_holiday"] = local_dates.map(
        lambda value: int(value + timedelta(days=1) in holidays)
    )
    result["is_day_after_public_holiday"] = local_dates.map(
        lambda value: int(value - timedelta(days=1) in holidays)
    )
    result["is_christmas_new_year_period"] = local_dates.map(
        lambda value: int((value.month == 12 and value.day >= 23) or (value.month == 1 and value.day == 1))
    )
    result["is_constitution_day"] = local_dates.map(
        lambda value: int(value.month == 5 and value.day == 17)
    )
    return result
