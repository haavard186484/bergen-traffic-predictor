import pandas as pd

from src.config import TARGET_COLUMN
from src.evaluation.latency_robust_model_evaluation import CANDIDATES
from src.features.build_features import create_features, feature_columns


def test_latency_robust_candidates_exclude_recent_lags_and_require_daily_weekly_history() -> None:
    for candidate in CANDIDATES:
        assert 1 not in candidate.traffic_lags
        assert 2 not in candidate.traffic_lags
        assert 24 in candidate.traffic_lags
        assert 168 in candidate.traffic_lags


def test_create_features_accepts_a_latency_robust_lag_schema() -> None:
    timestamps = pd.date_range("2025-01-01", periods=170, freq="h", tz="UTC")
    result = create_features(
        pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(170)}),
        traffic_lags=(24, 168),
    )

    assert result.loc[168, "traffic_24h_ago"] == 144
    assert result.loc[168, "traffic_168h_ago"] == 0
    assert "traffic_1h_ago" not in result
    assert feature_columns(traffic_lags=(24, 168))[-2:] == (
        "traffic_24h_ago",
        "traffic_168h_ago",
    )
    assert result.loc[168, TARGET_COLUMN] == 169
