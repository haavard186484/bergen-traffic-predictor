"""Final chronological selection of the frozen calendar and weather variants."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.evaluation.calendar_model_evaluation import CALENDAR_CV_FOLDS
from src.evaluation.metrics import regression_metrics
from src.evaluation.model_evaluation import complete_model_rows
from src.evaluation.traffic_eda import prepare_traffic_for_eda
from src.features.build_features import create_features, feature_columns
from src.features.weather_derivatives import (
    DERIVED_WEATHER_FEATURE_COLUMNS,
    SeasonalWeatherAnomaly,
    add_weather_derivatives,
)
from src.models.baselines import previous_week_forecast_baseline
from src.models.train import train_model

CALENDAR_COLUMNS = feature_columns(calendar_event_features=True)
WEATHER_COLUMNS = (*CALENDAR_COLUMNS, *DERIVED_WEATHER_FEATURE_COLUMNS)
MODEL_VERSION = "traffic-hgb-calendar-v1"


@dataclass(frozen=True)
class Candidate:
    """A fixed feature configuration considered by chronological CV."""

    name: str
    use_weather_derivatives: bool
    columns: tuple[str, ...]


CANDIDATES = (
    Candidate("traffic_hgb_with_calendar_events", False, CALENDAR_COLUMNS),
    Candidate("traffic_hgb_with_calendar_and_weather", True, WEATHER_COLUMNS),
)


def model_rows(data: pd.DataFrame) -> pd.DataFrame:
    """Build rows with deterministic calendar and conservative weather history."""
    prepared = prepare_traffic_for_eda(data)
    features = create_features(
        prepared,
        weather_columns=("temperature_c", "precipitation_mm", "wind_speed_m_s"),
        calendar_event_features=True,
    )
    features = add_weather_derivatives(features)
    features["target_local_timestamp"] = features["local_timestamp"] + pd.Timedelta(hours=1)
    # Weather gaps remain explicit in the derived columns. HGB supports missing
    # feature values natively; only traffic/calender requirements gate a row.
    return complete_model_rows(features, CALENDAR_COLUMNS)


def _fit_predict(train: pd.DataFrame, evaluation: pd.DataFrame, candidate: Candidate) -> pd.Series:
    """Fit a candidate using only its training period and predict later rows."""
    train_data = train
    evaluation_data = evaluation
    if candidate.use_weather_derivatives:
        transformer = SeasonalWeatherAnomaly().fit(train)
        train_data = transformer.transform(train)
        evaluation_data = transformer.transform(evaluation)
    model = train_model(train_data, candidate.columns, "hist_gradient_boosting")
    return pd.Series(model.predict(evaluation_data[list(candidate.columns)]), index=evaluation.index)


def chronological_cross_validation(data: pd.DataFrame) -> pd.DataFrame:
    """Compare frozen candidates solely on expanding 2022--2023 folds."""
    rows = model_rows(data)
    results: list[dict[str, float | int | str]] = []
    for candidate in CANDIDATES:
        for fold in CALENDAR_CV_FOLDS:
            train_end = pd.Timestamp(fold.train_end, tz="Europe/Oslo")
            validation_start = pd.Timestamp(fold.validation_start, tz="Europe/Oslo")
            validation_end = pd.Timestamp(fold.validation_end, tz="Europe/Oslo")
            train = rows.loc[rows["target_local_timestamp"] < train_end]
            validation = rows.loc[
                (rows["target_local_timestamp"] >= validation_start)
                & (rows["target_local_timestamp"] < validation_end)
            ]
            prediction = _fit_predict(train, validation, candidate)
            results.append(
                {
                    "model": candidate.name,
                    "fold": fold.name,
                    "evaluated_predictions": len(validation),
                    **regression_metrics(validation["target_traffic"], prediction),
                }
            )
    return pd.DataFrame(results).set_index(["model", "fold"]).round(2)


def select_by_cross_validation(cv_results: pd.DataFrame) -> Candidate:
    """Select one predeclared candidate by mean CV MAE only."""
    selected_name = cv_results.groupby(level="model")["mae"].mean().idxmin()
    return next(candidate for candidate in CANDIDATES if candidate.name == selected_name)


def evaluate_period(data: pd.DataFrame, candidate: Candidate, train_end: str, start: str, end: str) -> pd.DataFrame:
    """Train before ``train_end`` and evaluate exactly one later local period."""
    rows = model_rows(data)
    train = rows.loc[rows["target_local_timestamp"] < pd.Timestamp(train_end, tz="Europe/Oslo")]
    evaluation = rows.loc[
        (rows["target_local_timestamp"] >= pd.Timestamp(start, tz="Europe/Oslo"))
        & (rows["target_local_timestamp"] < pd.Timestamp(end, tz="Europe/Oslo"))
    ]
    prediction = _fit_predict(train, evaluation, candidate)
    baseline = previous_week_forecast_baseline(prepare_traffic_for_eda(data)).reindex(evaluation.index)
    return pd.DataFrame(
        [
            {
                "model": candidate.name,
                "evaluated_predictions": len(evaluation),
                **regression_metrics(evaluation["target_traffic"], prediction),
            },
            {
                "model": "previous_week_baseline",
                "evaluated_predictions": len(evaluation),
                **regression_metrics(evaluation["target_traffic"], baseline),
            },
        ]
    ).set_index("model").round(2)


def train_final_model(data: pd.DataFrame, candidate: Candidate):
    """Fit the frozen candidate on 2022--2024 and return model plus transform."""
    rows = model_rows(data)
    train = rows.loc[rows["target_local_timestamp"] < pd.Timestamp("2025-01-01", tz="Europe/Oslo")]
    transformer = None
    train_data = train
    if candidate.use_weather_derivatives:
        transformer = SeasonalWeatherAnomaly().fit(train)
        train_data = transformer.transform(train)
    return train_model(train_data, candidate.columns, "hist_gradient_boosting"), transformer, len(train)
