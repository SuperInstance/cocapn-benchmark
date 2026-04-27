"""Memory profiler using tracemalloc."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MemoryResult:
    """Aggregated memory measurements."""

    peak_rss: List[int] = field(default_factory=list)
    current_allocs: List[int] = field(default_factory=list)

    @property
    def peak_rss_mean(self) -> float:
        return sum(self.peak_rss) / len(self.peak_rss) if self.peak_rss else 0.0

    @property
    def current_allocs_mean(self) -> float:
        return sum(self.current_allocs) / len(self.current_allocs) if self.current_allocs else 0.0


class MemorySnapshot:
    """Context manager that records memory usage via tracemalloc."""

    def __init__(self, result: Optional[MemoryResult] = None) -> None:
        self.result = result or MemoryResult()
        self.peak: int = 0
        self.current: int = 0

    def __enter__(self) -> MemorySnapshot:
        tracemalloc.start()
        return self

    def __exit__(self, *args) -> None:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.peak = peak
        self.current = current
        self.result.peak_rss.append(peak)
        self.result.current_allocs.append(current)
