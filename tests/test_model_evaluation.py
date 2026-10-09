import pandas as pd

from src.config import TARGET_COLUMN
from src.evaluation.model_evaluation import complete_model_rows, error_summary


def test_complete_model_rows_drops_missing_features_and_targets_without_imputation() -> None:
    data = pd.DataFrame(
        {"feature": [1.0, None, 3.0], TARGET_COLUMN: [10.0, 20.0, None]}
    )

    result = complete_model_rows(data, ["feature"])

    assert result.index.tolist() == [0]


def test_error_summary_reports_mae_and_rmse_by_group() -> None:
    data = pd.DataFrame({"hour": [8, 8, 9]})
    actual = pd.Series([10.0, 20.0, 30.0])
    predicted = pd.Series([12.0, 18.0, 33.0])

    result = error_summary(data, actual, predicted, "hour")

    assert result.loc[8, "observations"] == 2
    assert result.loc[8, "mae"] == 2.0
    assert result.loc[9, "rmse"] == 3.0
