"""Download documented hourly Frost weather observations for Bergen - Florida."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import PROCESSED_DATA_DIR
from src.data.frost import (
    DEFAULT_STATION_ID,
    available_time_series,
    download_hourly_weather,
    write_weather_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station-id", default=DEFAULT_STATION_ID)
    parser.add_argument("--from", dest="start", default="2022-01-01T00:00:00Z")
    parser.add_argument("--to", dest="end", default="2026-01-01T00:00:00Z")
    parser.add_argument("--output", type=Path, default=PROCESSED_DATA_DIR / "weather_hourly.csv")
    args = parser.parse_args()

    availability = available_time_series(args.station_id, args.start, args.end)
    weather = download_hourly_weather(args.station_id, args.start, args.end)
    output = write_weather_dataset(
        weather, args.output, station_id=args.station_id, start=args.start, end=args.end,
        availability=availability,
    )
    print(f"Wrote {len(weather)} weather timestamps to {output}")
    print(f"Metadata: {output.with_suffix('.metadata.json')}")
    print("Forecast features use exact Frost observations lagged by at least one hour.")


if __name__ == "__main__":
    main()
