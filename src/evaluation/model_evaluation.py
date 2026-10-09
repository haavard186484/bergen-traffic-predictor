"""Evaluation helpers shared by the reproducible initial ML experiment."""

from collections.abc import Sequence

import pandas as pd

from src.config import TARGET_COLUMN
from src.evaluation.metrics import regression_metrics


def complete_model_rows(data: pd.DataFrame, feature_columns: Sequence[str]) -> pd.DataFrame:
    """Return only rows with an observed target and every required feature.

    Missing values are not imputed. In particular, rows touching a measurement
    gap remain unavailable to a model instead of being shifted across it.
    """
    required = [*feature_columns, TARGET_COLUMN]
    return data.dropna(subset=required).copy()


def error_summary(
    data: pd.DataFrame, actual: pd.Series, predicted: pd.Series, group: str
) -> pd.DataFrame:
    """Summarise absolute and squared forecast error by a calendar group."""
    comparison = pd.DataFrame(
        {group: data[group], "actual": actual, "predicted": predicted}, index=data.index
    ).dropna()
    comparison["absolute_error"] = (comparison["actual"] - comparison["predicted"]).abs()
    comparison["squared_error"] = (comparison["actual"] - comparison["predicted"]) ** 2
    return (
        comparison.groupby(group, observed=True)
        .agg(observations=("actual", "size"), mae=("absolute_error", "mean"), mse=("squared_error", "mean"))
        .assign(rmse=lambda summary: summary["mse"] ** 0.5)
        .drop(columns="mse")
        .round(2)
    )


def evaluate_predictions(actual: pd.Series, predicted: pd.Series) -> dict[str, float | int]:
    """Return comparable metrics and the number of valid forecast pairs."""
    valid = actual.notna() & predicted.notna()
    return {"evaluated_predictions": int(valid.sum()), **regression_metrics(actual, predicted)}
