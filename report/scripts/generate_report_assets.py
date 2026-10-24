"""Generate compact report data from the repository's documented final results."""

from __future__ import annotations

import csv
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1]
SOURCE = REPORT_DIR.parent / "docs" / "latency-robust-model-evaluation.md"
ERROR_OUTPUT = REPORT_DIR / "figures" / "error_by_hour.csv"
IMPORTANCE_OUTPUT = REPORT_DIR / "figures" / "feature_importance.csv"
FEATURE_LABELS = {
    "traffic_168h_ago": "Traffic t-168",
    "hour_cos": "Hour cosine",
    "traffic_24h_ago": "Traffic t-24",
    "day_of_week": "Day of week",
    "hour": "Hour",
    "hour_sin": "Hour sine",
    "is_public_holiday": "Public holiday",
    "month": "Month",
    "traffic_48h_ago": "Traffic t-48",
    "is_christmas_new_year_period": "Christmas/New Year",
    "is_day_before_public_holiday": "Day before holiday",
    "is_day_after_public_holiday": "Day after holiday",
    "is_weekend": "Weekend",
    "is_constitution_day": "Constitution Day",
}


def extract_hourly_error_table(markdown: str) -> list[tuple[int, int, float, float]]:
    """Read the final model's hourly error table from the generated Markdown report."""
    section = markdown.split("## Feilanalyse etter forecast-time", 1)[1].split("## ", 1)[0]
    rows: list[tuple[int, int, float, float]] = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        rows.append((int(cells[0]), int(cells[1]), float(cells[2]), float(cells[3])))
    if len(rows) != 24:
        raise ValueError(f"Expected 24 hourly rows, found {len(rows)}")
    return rows


def extract_feature_importance_table(markdown: str) -> list[tuple[str, float, float]]:
    """Read the cross-validated permutation-importance table."""
    section = markdown.split(
        "## Cross-validated permutation feature importance",
        1,
    )[1].split("## ", 1)[0]
    rows: list[tuple[str, float, float]] = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in {"feature", "---"}:
            continue
        try:
            rows.append((cells[0], float(cells[1]), float(cells[2])))
        except ValueError:
            continue
    if len(rows) != 14:
        raise ValueError(f"Expected 14 feature-importance rows, found {len(rows)}")
    return rows


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    error_rows = extract_hourly_error_table(markdown)
    importance_rows = extract_feature_importance_table(markdown)
    ERROR_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("hour", "observations", "mae", "rmse"))
        writer.writerows(error_rows)
    with IMPORTANCE_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("feature", "label", "mean_delta_mae", "std_delta_mae"))
        writer.writerows(
            (feature, FEATURE_LABELS[feature], mean_delta_mae, std_delta_mae)
            for feature, mean_delta_mae, std_delta_mae in importance_rows
        )


if __name__ == "__main__":
    main()
