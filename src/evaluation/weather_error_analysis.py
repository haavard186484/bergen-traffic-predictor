"""Leakage-safe, weather-conditioned error analysis for the traffic HGB."""

from __future__ import annotations

import pandas as pd

from scripts.run_initial_ml_model import _predict
from src.data.frost import WEATHER_COLUMNS
from src.evaluation.model_evaluation import complete_model_rows, error_summary
from src.evaluation.traffic_eda import assign_chronological_split, prepare_traffic_for_eda
from src.features.build_features import FEATURE_COLUMNS, create_features, feature_columns

WEATHER_AT_T_MINUS_1 = tuple(f"{column}_t_minus_1" for column in WEATHER_COLUMNS)


def _add_weather_at_t_minus_1(features: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    """Attach diagnostic weather observed at t-1 using exact UTC timestamps.

    These values are not model inputs in the selected traffic-only HGB.  They
    are grouped only after its forecasts have been made, and remain missing
    when Frost has no observation for the exact hour.
    """
    weather = data.copy()
    weather["timestamp"] = pd.to_datetime(weather["timestamp"], utc=True)
    observed = weather.set_index("timestamp")[list(WEATHER_COLUMNS)]
    lookup_times = pd.to_datetime(features["timestamp"], utc=True) - pd.Timedelta(hours=1)
    result = features.copy()
    for column in WEATHER_COLUMNS:
        result[f"{column}_t_minus_1"] = observed[column].reindex(lookup_times).to_numpy()
    return result


def validation_error_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return 2024 traffic-HGB forecast errors with diagnostic weather groups.

    The HGB is fit only on 2022--2023.  The target timestamp controls the
    split, so each returned row predicts its target one hour ahead.
    """
    prepared = prepare_traffic_for_eda(data)
    features = create_features(prepared)
    target_times = prepared.copy()
    target_times["local_timestamp"] += pd.Timedelta(hours=1)
    features["split"] = assign_chronological_split(target_times)
    rows = complete_model_rows(features, FEATURE_COLUMNS)
    train_rows = rows.loc[rows["split"].eq("train")]
    validation_rows = rows.loc[rows["split"].eq("validation")].copy()
    validation_rows["prediction"] = _predict(
        validation_rows, "hist_gradient_boosting", train_rows
    )
    validation_rows["target_timestamp"] = validation_rows["timestamp"] + pd.Timedelta(hours=1)
    validation_rows["target_local_timestamp"] = validation_rows["local_timestamp"] + pd.Timedelta(hours=1)
    validation_rows["absolute_error"] = (
        validation_rows["target_traffic"] - validation_rows["prediction"]
    ).abs()
    validation_rows["signed_error"] = validation_rows["prediction"] - validation_rows["target_traffic"]
    return _add_weather_at_t_minus_1(validation_rows, prepared)


def add_weather_bands(data: pd.DataFrame) -> pd.DataFrame:
    """Add documented rain, wind and temperature groups without filling gaps."""
    result = data.copy()
    precipitation = result["precipitation_mm_t_minus_1"]
    result["rain"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result.loc[precipitation.eq(0), "rain"] = "no_rain"
    result.loc[precipitation.gt(0), "rain"] = "rain"
    result["wind_band"] = pd.cut(
        result["wind_speed_m_s_t_minus_1"],
        bins=[float("-inf"), 4, 8, float("inf")],
        labels=["under_4_m_s", "4_to_under_8_m_s", "8_m_s_or_more"],
        right=False,
    )
    result["temperature_band"] = pd.cut(
        result["temperature_c_t_minus_1"],
        bins=[float("-inf"), 0, 5, 10, float("inf")],
        labels=["below_0_c", "0_to_under_5_c", "5_to_under_10_c", "10_c_or_more"],
        right=False,
    )
    return result


def daily_error_summary(data: pd.DataFrame, minimum_observations: int = 20) -> pd.DataFrame:
    """Return complete local dates with the largest daily mean absolute error."""
    daily = (
        data.assign(date=data["target_local_timestamp"].dt.date)
        .groupby("date", observed=True)
        .agg(
            observations=("absolute_error", "size"),
            mae=("absolute_error", "mean"),
            rmse=("absolute_error", lambda values: (values.pow(2).mean()) ** 0.5),
            mean_signed_error=("signed_error", "mean"),
            maximum_absolute_error=("absolute_error", "max"),
        )
        .query("observations >= @minimum_observations")
        .sort_values("mae", ascending=False)
        .round(2)
    )
    return daily


def calendar_error_summaries(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Summarise full validation errors in target-local calendar time."""
    groups = {
        "hour": data["target_local_timestamp"].dt.hour,
        "weekday": data["target_local_timestamp"].dt.day_name(),
        "month": data["target_local_timestamp"].dt.month_name(),
    }
    return {
        name: error_summary(data.assign(**{name: values}), data["target_traffic"], data["prediction"], name)
        for name, values in groups.items()
    }


def weather_error_summaries(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Summarise errors by conservative t-1 weather, retaining missingness."""
    banded = add_weather_bands(data)
    return {
        group: error_summary(banded, banded["target_traffic"], banded["prediction"], group)
        for group in ("rain", "wind_band", "temperature_band")
    }


def weather_model_condition_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Compare existing traffic/weather HGB forecasts by t-1 weather condition.

    This is a diagnostic re-expression of the already evaluated 2024 weather
    experiment, not a new model-selection procedure.  It uses only rows with
    all conservative weather lags and does not inspect the 2025 test period.
    """
    prepared = prepare_traffic_for_eda(data)
    traffic_features = create_features(prepared)
    weather_features = create_features(prepared, weather_columns=WEATHER_COLUMNS)
    target_times = prepared.copy()
    target_times["local_timestamp"] += pd.Timedelta(hours=1)
    split = assign_chronological_split(target_times)
    traffic_features["split"] = split
    weather_features["split"] = split
    traffic_rows = complete_model_rows(traffic_features, FEATURE_COLUMNS)
    weather_columns = feature_columns(WEATHER_COLUMNS)
    weather_rows = complete_model_rows(weather_features, weather_columns)
    index = traffic_rows.index.intersection(weather_rows.index)
    index = index[traffic_rows.loc[index, "split"].eq("validation")]
    traffic_prediction = _predict(
        traffic_rows.loc[index], "hist_gradient_boosting", traffic_rows.loc[traffic_rows["split"].eq("train")]
    )
    weather_prediction = _predict(
        weather_rows.loc[index], "hist_gradient_boosting", weather_rows.loc[weather_rows["split"].eq("train")], weather_columns
    )
    comparison = _add_weather_at_t_minus_1(traffic_rows.loc[index], prepared)
    comparison = add_weather_bands(comparison)
    comparison["traffic_absolute_error"] = (comparison["target_traffic"] - traffic_prediction).abs()
    comparison["weather_absolute_error"] = (comparison["target_traffic"] - weather_prediction).abs()
    summaries = []
    for group in ("rain", "wind_band", "temperature_band"):
        summary = (
            comparison.groupby(group, observed=True)
            .agg(
                observations=("target_traffic", "size"),
                traffic_hgb_mae=("traffic_absolute_error", "mean"),
                weather_hgb_mae=("weather_absolute_error", "mean"),
            )
            .assign(
                weather_minus_traffic_mae=lambda values: values["weather_hgb_mae"]
                - values["traffic_hgb_mae"]
            )
            .reset_index(names="condition")
        )
        summary.insert(0, "weather_group", group)
        summaries.append(summary)
    return pd.concat(summaries, ignore_index=True).set_index(["weather_group", "condition"]).round(2)
