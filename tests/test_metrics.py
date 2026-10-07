import pandas as pd

from src.evaluation.metrics import regression_metrics


def test_regression_metrics_returns_mae_and_rmse() -> None:
    metrics = regression_metrics(pd.Series([10, 20]), pd.Series([12, 18]))

    assert metrics == {"mae": 2.0, "rmse": 2.0}
