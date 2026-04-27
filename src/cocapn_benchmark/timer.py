"""Precise timer context manager using time.perf_counter."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class BenchmarkResult:
    """Aggregated timing results from multiple iterations."""

    wall_times: List[float] = field(default_factory=list)
    cpu_times: List[float] = field(default_factory=list)

    @property
    def wall_mean(self) -> float:
        return statistics.mean(self.wall_times) if self.wall_times else 0.0

    @property
    def wall_median(self) -> float:
        return statistics.median(self.wall_times) if self.wall_times else 0.0

    @property
    def wall_p95(self) -> float:
        return self._percentile(self.wall_times, 0.95)

    @property
    def wall_p99(self) -> float:
        return self._percentile(self.wall_times, 0.99)

    @property
    def wall_stddev(self) -> float:
        return statistics.stdev(self.wall_times) if len(self.wall_times) > 1 else 0.0

    @property
    def cpu_mean(self) -> float:
        return statistics.mean(self.cpu_times) if self.cpu_times else 0.0

    @property
    def cpu_median(self) -> float:
        return statistics.median(self.cpu_times) if self.cpu_times else 0.0

    @property
    def cpu_p95(self) -> float:
        return self._percentile(self.cpu_times, 0.95)

    @property
    def cpu_p99(self) -> float:
        return self._percentile(self.cpu_times, 0.99)

    @property
    def cpu_stddev(self) -> float:
        return statistics.stdev(self.cpu_times) if len(self.cpu_times) > 1 else 0.0

    @staticmethod
    def _percentile(data: List[float], p: float) -> float:
        if not data:
            return 0.0
        s = sorted(data)
        k = (len(s) - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < len(s) else f
        if f == c:
            return s[f]
        return s[f] * (c - k) + s[c] * (k - f)


class Timer:
    """Context manager that records a single timing sample."""

    def __init__(self, result: Optional[BenchmarkResult] = None) -> None:
        self.result = result or BenchmarkResult()
        self._wall_start: float = 0.0
        self._cpu_start: float = 0.0
        self.wall_elapsed: float = 0.0
        self.cpu_elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self._wall_start = time.perf_counter()
        self._cpu_start = time.process_time()
        return self

    def __exit__(self, *args) -> None:
        self.wall_elapsed = time.perf_counter() - self._wall_start
        self.cpu_elapsed = time.process_time() - self._cpu_start
        self.result.wall_times.append(self.wall_elapsed)
        self.result.cpu_times.append(self.cpu_elapsed)

    @classmethod
    def benchmark(
        cls,
        fn: Callable[..., T],
        *args,
        iterations: int = 100,
        **kwargs,
    ) -> BenchmarkResult:
        """Run *fn* *iterations* times and return a BenchmarkResult."""
        result = BenchmarkResult()
        for _ in range(iterations):
            with cls(result):
                fn(*args, **kwargs)
        return result
