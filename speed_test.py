"""Download measurement logic for the internet speed CLI."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CHUNK_SIZE = 64 * 1024
USER_AGENT = "internet-speed-measurer/1.0"


@dataclass(frozen=True)
class RequestResult:
    """Measurements from one completed download."""

    elapsed_seconds: float
    bytes_downloaded: int


@dataclass(frozen=True)
class Measurement:
    """Measurements from a complete sequence of downloads."""

    requests: tuple[RequestResult, ...]
    elapsed_seconds: float

    @property
    def total_bytes(self) -> int:
        return sum(result.bytes_downloaded for result in self.requests)

    @property
    def average_request_seconds(self) -> float:
        return sum(result.elapsed_seconds for result in self.requests) / len(self.requests)

    @property
    def megabits_per_second(self) -> float:
        return self.total_bytes * 8 / 1_000_000 / self.elapsed_seconds

    @property
    def megabytes_per_second(self) -> float:
        return self.total_bytes / 1_000_000 / self.elapsed_seconds


class DownloadError(Exception):
    """A failed download, annotated with its position in the sequence."""

    def __init__(self, request_number: int, total_requests: int, cause: Exception) -> None:
        self.request_number = request_number
        self.total_requests = total_requests
        self.cause = cause
        super().__init__(str(cause))


def _download_once(url: str, timeout: float) -> RequestResult:
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    started = time.perf_counter()
    downloaded = 0

    with urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            downloaded += len(chunk)

    return RequestResult(time.perf_counter() - started, downloaded)


def measure_downloads(url: str, count: int = 10, timeout: float = 30.0) -> Measurement:
    """Download a URL sequentially and return the measurements."""
    if count < 1:
        raise ValueError("count must be at least 1")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a finite number greater than 0")

    results: list[RequestResult] = []
    started = time.perf_counter()

    for request_number in range(1, count + 1):
        try:
            results.append(_download_once(url, timeout))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise DownloadError(request_number, count, exc) from exc

    return Measurement(tuple(results), time.perf_counter() - started)
