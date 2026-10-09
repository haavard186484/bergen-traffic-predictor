"""Download hourly traffic data from the Traffic Data API."""

import argparse
from pathlib import Path

from src.config import RAW_DATA_DIR
from src.data.traffic_api import download_hourly_traffic, write_api_export


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--point-id", required=True, help="Traffic registration point ID")
    parser.add_argument("--from", dest="start", required=True, help="ISO-8601 start timestamp")
    parser.add_argument("--to", dest="end", required=True, help="ISO-8601 end timestamp")
    parser.add_argument(
        "--output", type=Path, default=RAW_DATA_DIR / "traffic_api_export.csv", help="Raw CSV output"
    )
    args = parser.parse_args()

    data = download_hourly_traffic(args.point_id, args.start, args.end)
    output = write_api_export(data, args.point_id, args.start, args.end, args.output)
    print(f"Downloaded {len(data)} hourly rows to {output}")
    print(f"Metadata: {output.with_suffix('.metadata.json')}")


if __name__ == "__main__":
    main()
