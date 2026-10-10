"""Chronological CV for deterministic Norwegian calendar-event features."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from scripts.run_initial_ml_model import _predict
from src.evaluation.metrics import regression_metrics
from src.evaluation.model_evaluation import complete_model_rows
from src.evaluation.traffic_eda import prepare_traffic_for_eda
from src.features.build_features import FEATURE_COLUMNS, create_features, feature_columns


@dataclass(frozen=True)
class CrossValidationFold:
    """A chronological training and validation interval in target-local time."""

    name: str
    train_end: str
    validation_start: str
    validation_end: str


CALENDAR_CV_FOLDS = (
    CrossValidationFold("2022_h2", "2022-07-01", "2022-07-01", "2023-01-01"),
    CrossValidationFold("2023_h1", "2023-01-01", "2023-01-01", "2023-07-01"),
    CrossValidationFold("2023_h2", "2023-07-01", "2023-07-01", "2024-01-01"),
)


def _model_rows(data: pd.DataFrame, use_calendar_events: bool) -> pd.DataFrame:
    prepared = prepare_traffic_for_eda(data)
    features = create_features(prepared, calendar_event_features=use_calendar_events)
    features["target_local_timestamp"] = features["local_timestamp"] + pd.Timedelta(hours=1)
    columns = feature_columns(calendar_event_features=use_calendar_events)
    return complete_model_rows(features, columns)


def chronological_cross_validation(data: pd.DataFrame) -> pd.DataFrame:
    """Compare traffic HGB variants on 2022--2023 chronological folds only."""
    variants = {
        "traffic_hgb": (False, FEATURE_COLUMNS),
        "traffic_hgb_with_calendar_events": (True, feature_columns(calendar_event_features=True)),
    }
    results: list[dict[str, float | int | str]] = []
    for model, (use_calendar_events, columns) in variants.items():
        rows = _model_rows(data, use_calendar_events)
        for fold in CALENDAR_CV_FOLDS:
            train_end = pd.Timestamp(fold.train_end, tz="Europe/Oslo")
            validation_start = pd.Timestamp(fold.validation_start, tz="Europe/Oslo")
            validation_end = pd.Timestamp(fold.validation_end, tz="Europe/Oslo")
            train = rows.loc[rows["target_local_timestamp"] < train_end]
            validation = rows.loc[
                (rows["target_local_timestamp"] >= validation_start)
                & (rows["target_local_timestamp"] < validation_end)
            ]
            prediction = _predict(validation, "hist_gradient_boosting", train, columns)
            results.append(
                {
                    "model": model,
                    "fold": fold.name,
                    "evaluated_predictions": len(validation),
                    **regression_metrics(validation["target_traffic"], prediction),
                }
            )
    return pd.DataFrame(results).set_index(["model", "fold"]).round(2)


def select_by_cross_validation(cv_results: pd.DataFrame) -> str:
    """Return the model with the lowest mean fold MAE, without 2024 data."""
    return cv_results.groupby(level="model")["mae"].mean().idxmin()


def evaluate_selected_on_2024(data: pd.DataFrame, selected: str) -> pd.DataFrame:
    """Fit the preselected variant on 2022--2023 and report 2024 once."""
    if selected not in {"traffic_hgb", "traffic_hgb_with_calendar_events"}:
        raise ValueError(f"Unknown model: {selected}")
    use_calendar_events = selected == "traffic_hgb_with_calendar_events"
    columns = feature_columns(calendar_event_features=use_calendar_events)
    rows = _model_rows(data, use_calendar_events)
    train = rows.loc[rows["target_local_timestamp"] < pd.Timestamp("2024-01-01", tz="Europe/Oslo")]
    validation = rows.loc[
        (rows["target_local_timestamp"] >= pd.Timestamp("2024-01-01", tz="Europe/Oslo"))
        & (rows["target_local_timestamp"] < pd.Timestamp("2025-01-01", tz="Europe/Oslo"))
    ]
    prediction = _predict(validation, "hist_gradient_boosting", train, columns)
    return pd.DataFrame(
        [{"model": selected, "evaluated_predictions": len(validation), **regression_metrics(validation["target_traffic"], prediction)}]
    ).set_index("model").round(2)
