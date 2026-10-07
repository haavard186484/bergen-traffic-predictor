"""Print a feasibility report for a CSV exported from Trafikkdataportalen."""

import argparse
from pathlib import Path

from src.data.traffic_export import feasibility_report, read_hourly_traffic_export


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Path to the hourly traffic CSV export")
    args = parser.parse_args()

    report = feasibility_report(read_hourly_traffic_export(args.csv_path))
    for name, value in report.items():
        print(f"{name}: {value}")

    viable = (
        report["rows"] >= 24 * 28
        and report["coverage_percent"] >= 95
        and report["duplicate_timestamps"] == 0
    )
    print(f"result: {'GO' if viable else 'REVIEW'}")


if __name__ == "__main__":
    main()
