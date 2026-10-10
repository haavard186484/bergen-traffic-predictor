import pandas as pd

from src.evaluation.final_model_evaluation import select_by_cross_validation


def test_selection_uses_only_lowest_mean_cv_mae() -> None:
    results = pd.DataFrame(
        {
            "model": [
                "traffic_hgb_with_calendar_events",
                "traffic_hgb_with_calendar_events",
                "traffic_hgb_with_calendar_and_weather",
                "traffic_hgb_with_calendar_and_weather",
            ],
            "fold": ["first", "second", "first", "second"],
            "mae": [100.0, 120.0, 109.0, 109.0],
        }
    ).set_index(["model", "fold"])

    selected = select_by_cross_validation(results)

    assert selected.name == "traffic_hgb_with_calendar_and_weather"
