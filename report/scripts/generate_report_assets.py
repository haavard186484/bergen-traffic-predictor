"""Generate compact report data from the repository's documented final results."""

from __future__ import annotations

import csv
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1]
SOURCE = REPORT_DIR.parent / "docs" / "latency-robust-model-evaluation.md"
OUTPUT = REPORT_DIR / "figures" / "error_by_hour.csv"


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


def main() -> None:
    rows = extract_hourly_error_table(SOURCE.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("hour", "observations", "mae", "rmse"))
        writer.writerows(rows)


if __name__ == "__main__":
    main()
