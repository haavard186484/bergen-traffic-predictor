import pandas as pd

from src.data.traffic_history import fetch_required_traffic_history


def test_fetches_exact_required_lags_without_filling_gaps() -> None:
    calls: list[tuple[str, str, str]] = []

    def downloader(point_id: str, start: str, end: str) -> pd.DataFrame:
        calls.append((point_id, start, end))
        return pd.DataFrame(
            {
                "Fra": [
                    "2024-12-25T12:00:00Z",
                    "2025-01-01T10:00:00Z",
                    "2025-01-01T11:00:00Z",
                ],
                "Trafikkmengde": [168, 2, 1],
            }
        )

    history = fetch_required_traffic_history(
        pd.Timestamp("2025-01-01T12:00:00Z"), downloader=downloader
    )

    assert history == {1: 1.0, 2: 2.0, 24: None, 168: 168.0}
    assert calls == [("14630V805616", "2024-12-25T12:00:00+00:00", "2025-01-01T12:00:00+00:00")]
