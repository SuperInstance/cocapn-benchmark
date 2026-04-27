"""BenchmarkSuite class that runs iterations and reports formatted results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .memory import MemoryResult, MemorySnapshot
from .timer import BenchmarkResult, Timer


@dataclass
class BenchmarkEntry:
    name: str
    fn: Callable[..., Any]
    timer_result: BenchmarkResult = field(default_factory=BenchmarkResult)
    memory_result: MemoryResult = field(default_factory=MemoryResult)


class BenchmarkSuite:
    """Collect and run a set of benchmarks."""

    def __init__(self) -> None:
        self._entries: List[BenchmarkEntry] = []

    def add(self, name: str, fn: Callable[..., Any]) -> BenchmarkSuite:
        """Register a benchmark callable."""
        self._entries.append(BenchmarkEntry(name=name, fn=fn))
        return self

    def run(self, iterations: int = 100) -> BenchmarkSuite:
        """Execute all registered benchmarks."""
        for entry in self._entries:
            for _ in range(iterations):
                with Timer(entry.timer_result):
                    with MemorySnapshot(entry.memory_result):
                        entry.fn()
        return self

    def report(self) -> str:
        """Return a formatted table of results."""
        lines: List[str] = []
        lines.append("-" * 90)
        header = (
            f"{'Benchmark':<20} {'Wall mean (s)':<15} {'Wall p95 (s)':<15} "
            f"{'CPU mean (s)':<15} {'Peak RSS (B)':<15}"
        )
        lines.append(header)
        lines.append("-" * 90)
        for entry in self._entries:
            t = entry.timer_result
            m = entry.memory_result
            peak = int(m.peak_rss_mean) if m.peak_rss else 0
            lines.append(
                f"{entry.name:<20} {t.wall_mean:<15.6f} {t.wall_p95:<15.6f} "
                f"{t.cpu_mean:<15.6f} {peak:<15}"
            )
        lines.append("-" * 90)
        return "\n".join(lines)
