"""Build a validated, normalized traffic dataset from a portal CSV export."""

import argparse
from pathlib import Path

from src.config import PROCESSED_DATA_DIR
from src.data.prepare_traffic import prepare_traffic_datasets, write_traffic_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_paths",
        type=Path,
        nargs="+",
        help="One or more hourly traffic CSV exports, in any order",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DATA_DIR / "traffic_hourly.csv",
        help="Path for the normalized dataset",
    )
    parser.add_argument(
        "--allow-gaps",
        action="store_true",
        help="Preserve unknown traffic volumes as missing values on a complete hourly index",
    )
    args = parser.parse_args()

    data, report = prepare_traffic_datasets(args.csv_paths, allow_gaps=args.allow_gaps)
    output = write_traffic_dataset(data, report, args.csv_paths, args.output)
    print(f"Wrote {len(data)} hourly rows to {output}")
    print(f"Metadata: {output.with_suffix('.metadata.json')}")


if __name__ == "__main__":
    main()
