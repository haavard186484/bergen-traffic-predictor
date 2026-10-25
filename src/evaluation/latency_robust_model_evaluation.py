"""Selection and final evaluation for the traffic-data latency-robust model."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.inspection import permutation_importance

from src.evaluation.calendar_model_evaluation import CALENDAR_CV_FOLDS
from src.evaluation.metrics import regression_metrics
from src.evaluation.model_evaluation import error_summary
from src.evaluation.traffic_eda import prepare_traffic_for_eda
from src.features.build_features import create_features, feature_columns
from src.models.baselines import previous_week_forecast_baseline
from src.models.train import train_model

MODEL_VERSION = "traffic-hgb-latency-robust-v1"
FINAL_TRAIN_END = "2026-01-01"
FINAL_EVALUATION_START = "2026-01-01"
FINAL_EVALUATION_END = "2026-07-01"


@dataclass(frozen=True)
class Candidate:
    """A predeclared HGB feature package available despite publication latency."""

    name: str
    traffic_lags: tuple[int, ...]
    columns: tuple[str, ...]


def _candidate(name: str, traffic_lags: tuple[int, ...]) -> Candidate:
    return Candidate(
        name=name,
        traffic_lags=traffic_lags,
        columns=feature_columns(calendar_event_features=True, traffic_lags=traffic_lags),
    )


# This small list is intentionally fixed before any 2022--2023 CV results are
# inspected.  Every package excludes t-1 and t-2, and includes the daily and
# weekly history that is available even when recent hourly data is delayed.
CANDIDATES = (
    _candidate("traffic_hgb_calendar_lags_24_168", (24, 168)),
    _candidate("traffic_hgb_calendar_lags_24_48_168", (24, 48, 168)),
    _candidate("traffic_hgb_calendar_lags_24_168_336", (24, 168, 336)),
)


def model_rows(data: pd.DataFrame, candidate: Candidate) -> pd.DataFrame:
    """Build candidate rows using only its explicitly available traffic lags."""
    prepared = prepare_traffic_for_eda(data)
    rows = create_features(
        prepared,
        calendar_event_features=True,
        traffic_lags=candidate.traffic_lags,
    )
    rows["target_local_timestamp"] = rows["local_timestamp"] + pd.Timedelta(hours=1)
    rows["target_hour"] = rows["target_local_timestamp"].dt.hour
    rows["target_day_of_week"] = rows["target_local_timestamp"].dt.dayofweek
    return rows.dropna(subset=[*candidate.columns, "target_traffic"]).copy()


def _fit_predict(train: pd.DataFrame, evaluation: pd.DataFrame, candidate: Candidate) -> pd.Series:
    model = train_model(train, candidate.columns, "hist_gradient_boosting")
    return pd.Series(model.predict(evaluation[list(candidate.columns)]), index=evaluation.index)


def chronological_cross_validation(data: pd.DataFrame) -> pd.DataFrame:
    """Select only among fixed candidates with expanding 2022--2023 CV."""
    results: list[dict[str, float | int | str]] = []
    for candidate in CANDIDATES:
        rows = model_rows(data, candidate)
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
    """Freeze the candidate with the lowest mean CV MAE."""
    selected_name = cv_results.groupby(level="model")["mae"].mean().idxmin()
    return next(candidate for candidate in CANDIDATES if candidate.name == selected_name)


def cross_validated_permutation_importance(
    data: pd.DataFrame,
    candidate: Candidate,
    *,
    n_repeats: int = 30,
    random_state: int = 42,
    n_jobs: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Measure held-out feature reliance across the existing chronological CV folds.

    With negative mean absolute error scoring, a positive delta is the increase
    in MAE, measured in vehicles per hour, after a feature is permuted.
    """
    if n_repeats < 1:
        raise ValueError("n_repeats must be positive")

    rows = model_rows(data, candidate)
    records: list[dict[str, float | int | str]] = []
    for fold_number, fold in enumerate(CALENDAR_CV_FOLDS):
        train_end = pd.Timestamp(fold.train_end, tz="Europe/Oslo")
        validation_start = pd.Timestamp(fold.validation_start, tz="Europe/Oslo")
        validation_end = pd.Timestamp(fold.validation_end, tz="Europe/Oslo")
        train = rows.loc[rows["target_local_timestamp"] < train_end]
        validation = rows.loc[
            (rows["target_local_timestamp"] >= validation_start)
            & (rows["target_local_timestamp"] < validation_end)
        ]
        model = train_model(train, candidate.columns, "hist_gradient_boosting")
        importance = permutation_importance(
            model,
            validation[list(candidate.columns)],
            validation["target_traffic"],
            scoring="neg_mean_absolute_error",
            n_repeats=n_repeats,
            random_state=random_state + fold_number,
            n_jobs=n_jobs,
        )
        for feature_number, feature in enumerate(candidate.columns):
            for repeat, delta_mae in enumerate(importance.importances[feature_number], start=1):
                records.append(
                    {
                        "feature": feature,
                        "fold": fold.name,
                        "repeat": repeat,
                        "delta_mae": float(delta_mae),
                    }
                )

    detailed = pd.DataFrame.from_records(records)
    summary = detailed.groupby("feature", sort=False).agg(
        mean_delta_mae=("delta_mae", "mean"),
        std_delta_mae=("delta_mae", "std"),
        folds=("fold", "nunique"),
        permutations=("delta_mae", "size"),
    )
    summary = summary.sort_values("mean_delta_mae", ascending=False).round(2)
    return detailed, summary


def final_evaluation(
    data: pd.DataFrame, candidate: Candidate
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate the CV-frozen candidate once on the reserved 2026 H1 period."""
    rows = model_rows(data, candidate)
    train = rows.loc[
        rows["target_local_timestamp"] < pd.Timestamp(FINAL_TRAIN_END, tz="Europe/Oslo")
    ]
    evaluation = rows.loc[
        (rows["target_local_timestamp"] >= pd.Timestamp(FINAL_EVALUATION_START, tz="Europe/Oslo"))
        & (rows["target_local_timestamp"] < pd.Timestamp(FINAL_EVALUATION_END, tz="Europe/Oslo"))
    ].copy()
    evaluation["prediction"] = _fit_predict(train, evaluation, candidate)
    baseline = previous_week_forecast_baseline(prepare_traffic_for_eda(data))
    evaluation["previous_week_prediction"] = baseline.reindex(evaluation.index)
    # Both scores use exactly these forecast rows; a baseline gap cannot give
    # it an easier or harder sample than the model.
    shared = evaluation.dropna(subset=["target_traffic", "prediction", "previous_week_prediction"])
    metrics = (
        pd.DataFrame(
            [
                {
                    "model": candidate.name,
                    "evaluated_predictions": len(shared),
                    **regression_metrics(shared["target_traffic"], shared["prediction"]),
                },
                {
                    "model": "previous_week_baseline",
                    "evaluated_predictions": len(shared),
                    **regression_metrics(
                        shared["target_traffic"], shared["previous_week_prediction"]
                    ),
                },
            ]
        )
        .set_index("model")
        .round(2)
    )
    hourly = error_summary(shared, shared["target_traffic"], shared["prediction"], "target_hour")
    weekday = error_summary(
        shared, shared["target_traffic"], shared["prediction"], "target_day_of_week"
    )
    return metrics, hourly, weekday


def train_final_model(data: pd.DataFrame, candidate: Candidate):
    """Fit the CV-frozen configuration through 2025 after selection is complete."""
    rows = model_rows(data, candidate)
    train = rows.loc[
        rows["target_local_timestamp"] < pd.Timestamp(FINAL_TRAIN_END, tz="Europe/Oslo")
    ]
    return train_model(train, candidate.columns, "hist_gradient_boosting"), len(train)
