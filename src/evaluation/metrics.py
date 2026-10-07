"""Shared regression metrics."""

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


def regression_metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """Return MAE and RMSE for aligned, non-null observations."""
    comparison = pd.concat([actual.rename("actual"), predicted.rename("predicted")], axis=1).dropna()
    if comparison.empty:
        raise ValueError("No overlapping non-null predictions to evaluate")
    return {
        "mae": float(mean_absolute_error(comparison["actual"], comparison["predicted"])),
        "rmse": float(mean_squared_error(comparison["actual"], comparison["predicted"]) ** 0.5),
    }
