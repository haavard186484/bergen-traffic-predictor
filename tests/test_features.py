import pandas as pd

from src.config import TARGET_COLUMN
from src.features.build_features import create_features


def test_create_features_uses_past_traffic_and_next_hour_target() -> None:
    timestamps = pd.date_range("2025-01-01", periods=170, freq="h", tz="UTC")
    data = pd.DataFrame({"timestamp": timestamps, "traffic_volume": range(170)})

    result = create_features(data)

    assert result.loc[168, "traffic_168h_ago"] == 0
    assert result.loc[10, TARGET_COLUMN] == 11
    assert pd.isna(result.loc[0, "traffic_1h_ago"])
    assert pd.isna(result.loc[169, TARGET_COLUMN])
