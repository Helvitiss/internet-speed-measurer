"""Command-line entry point for the internet speed measurer."""

from __future__ import annotations

import argparse
import math
import sys
from urllib.parse import urlparse

from speed_test import DownloadError, Measurement, measure_downloads


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0")
    return number


def http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be an absolute http:// or https:// URL")
    return value


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1_000 or unit == "TB":
            return f"{value:.2f} {unit}"
        value /= 1_000
    return f"{value:.2f} TB"


def print_summary(measurement: Measurement) -> None:
    print("\nSummary:")
    print(f"  Successful requests:    {len(measurement.requests)}")
    print(f"  Average request time:   {measurement.average_request_seconds:.3f} s")
    print(f"  Total downloaded:       {format_bytes(measurement.total_bytes)} ({measurement.total_bytes} bytes)")
    print(f"  Total elapsed time:     {measurement.elapsed_seconds:.3f} s")
    print(
        "  Average download speed: "
        f"{measurement.megabits_per_second:.2f} Mbit/s "
        f"({measurement.megabytes_per_second:.2f} MB/s)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure download speed by fetching a URL sequentially."
    )
    parser.add_argument("url", type=http_url, help="direct URL of a file to download")
    parser.add_argument("--count", type=positive_int, default=10, help="number of sequential downloads (default: 10)")
    parser.add_argument("--timeout", type=positive_float, default=30.0, help="timeout per download in seconds (default: 30)")
    args = parser.parse_args()

    try:
        measurement = measure_downloads(args.url, args.count, args.timeout)
    except DownloadError as exc:
        print(
            f"Request {exc.request_number}/{exc.total_requests} failed: {exc.cause}",
            file=sys.stderr,
        )
        return 1

    for index, result in enumerate(measurement.requests, start=1):
        print(
            f"Request {index:>2}/{len(measurement.requests)}: "
            f"{result.elapsed_seconds:.3f} s, {format_bytes(result.bytes_downloaded)}"
        )

    print_summary(measurement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
