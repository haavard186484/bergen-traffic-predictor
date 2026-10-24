"""Read and validate hourly CSV exports from Trafikkdataportalen."""

from pathlib import Path

import pandas as pd

TIMESTAMP_COLUMN = "Fra"
VOLUME_COLUMNS = ("Trafikkmengde", "Volum")


def read_hourly_traffic_export(path: str | Path) -> pd.DataFrame:
    """Return a normalized hourly traffic series from a portal CSV export.

    The traffic portal uses Norwegian column names. When a ``Felt == Totalt``
    row is present, it is preferred so the model represents the full
    registration point rather than a single traffic direction.
    """
    # Trafikkdataportalen uses semicolons because numeric quality values use a
    # decimal comma. Automatic delimiter detection can therefore choose comma.
    raw = pd.read_csv(path, sep=";", decimal=",")
    volume_column = next((column for column in VOLUME_COLUMNS if column in raw.columns), None)
    if TIMESTAMP_COLUMN not in raw.columns or volume_column is None:
        raise ValueError(
            "CSV-en mangler forventede kolonner: Fra og Trafikkmengde"
        )

    if "Felt" in raw.columns and (raw["Felt"].astype(str) == "Totalt").any():
        raw = raw.loc[raw["Felt"].astype(str) == "Totalt"].copy()
    else:
        raw = raw.copy()

    result = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(raw[TIMESTAMP_COLUMN], errors="coerce", utc=True),
            "traffic_volume": pd.to_numeric(raw[volume_column], errors="coerce"),
        }
    )
    optional_columns = {
        "Trafikkregistreringspunkt": "traffic_point_id",
        "Navn": "traffic_point_name",
        "Vegreferanse": "road_reference",
        "Dekningsgrad (%)": "coverage_percent",
    }
    for source_column, target_column in optional_columns.items():
        if source_column in raw.columns:
            result[target_column] = raw[source_column].to_numpy()
    return result.sort_values("timestamp").reset_index(drop=True)


def feasibility_report(data: pd.DataFrame) -> dict[str, int | float | str]:
    """Summarize whether an hourly traffic series is suitable for the MVP."""
    if data.empty:
        raise ValueError("Ingen rader å validere")

    valid_timestamps = data["timestamp"].notna()
    valid_volume = data["traffic_volume"].notna() & (data["traffic_volume"] >= 0)
    valid_rows = valid_timestamps & valid_volume
    duplicate_timestamps = int(data.loc[valid_timestamps, "timestamp"].duplicated().sum())

    ordered = data.loc[valid_rows].sort_values("timestamp")
    expected_hours = (
        int((ordered["timestamp"].iloc[-1] - ordered["timestamp"].iloc[0]).total_seconds() / 3600)
        + 1
        if not ordered.empty
        else 0
    )
    missing_hours = max(expected_hours - int(ordered["timestamp"].nunique()), 0)

    return {
        "rows": len(data),
        "start": str(data["timestamp"].min()),
        "end": str(data["timestamp"].max()),
        "invalid_rows": int((~valid_rows).sum()),
        "duplicate_timestamps": duplicate_timestamps,
        "missing_hours": missing_hours,
        "coverage_percent": round(100 * valid_rows.mean(), 2),
    }
