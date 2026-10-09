"""Create a validated, model-ready hourly traffic dataset."""

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from src.data.traffic_export import feasibility_report, read_hourly_traffic_export


def prepare_traffic_dataset(
    source_path: str | Path, allow_gaps: bool = False
) -> tuple[pd.DataFrame, dict[str, int | float | str]]:
    """Read one portal export and reject invalid, duplicate, or missing data."""
    return prepare_traffic_datasets([source_path], allow_gaps=allow_gaps)


def prepare_traffic_datasets(
    source_paths: Iterable[str | Path], allow_gaps: bool = False
) -> tuple[pd.DataFrame, dict[str, int | float | str]]:
    """Combine exports and optionally preserve unknown hourly values as missing."""
    sources = [Path(path) for path in source_paths]
    if not sources:
        raise ValueError("Minst én kildefil må oppgis")

    data = pd.concat(
        [read_hourly_traffic_export(source) for source in sources], ignore_index=True
    ).sort_values("timestamp", ignore_index=True)
    report = feasibility_report(data)
    invalid_timestamps = int(data["timestamp"].isna().sum())
    negative_volumes = int((data["traffic_volume"] < 0).sum())
    issues = {}
    if invalid_timestamps:
        issues["invalid_timestamps"] = invalid_timestamps
    if negative_volumes:
        issues["negative_volumes"] = negative_volumes
    if report["duplicate_timestamps"]:
        issues["duplicate_timestamps"] = report["duplicate_timestamps"]
    if report["missing_hours"] and not allow_gaps:
        issues["missing_hours"] = report["missing_hours"]
    if issues:
        details = ", ".join(f"{key}={value}" for key, value in issues.items())
        raise ValueError(f"Kan ikke bygge datasett før datakvaliteten er løst: {details}")

    if "traffic_point_id" in data.columns and data["traffic_point_id"].nunique() != 1:
        raise ValueError("Én datasettfil kan bare inneholde ett trafikkregistreringspunkt")

    if allow_gaps:
        complete_index = pd.date_range(
            data["timestamp"].min(), data["timestamp"].max(), freq="h", tz="UTC"
        )
        data = (
            data.set_index("timestamp")
            .reindex(complete_index)
            .rename_axis("timestamp")
            .reset_index()
        )

    return data, report


def write_traffic_dataset(
    data: pd.DataFrame,
    report: dict[str, int | float | str],
    source_paths: str | Path | Iterable[str | Path],
    output_path: str | Path,
) -> Path:
    """Write the normalized dataset and sidecar metadata for reproducibility."""
    sources = (
        [Path(source_paths)]
        if isinstance(source_paths, (str, Path))
        else [Path(source) for source in source_paths]
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False)

    source_metadata = []
    for source in sources:
        with source.open("rb") as source_file:
            source_sha256 = hashlib.file_digest(source_file, "sha256").hexdigest()
        source_metadata.append({"file": source.name, "sha256": source_sha256})

    metadata = {
        "source_files": source_metadata,
        "quality_report": report,
        "columns": list(data.columns),
    }
    output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output
