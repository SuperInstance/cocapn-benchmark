"""High-level Benchmark class with setup, warmup, and measurement phases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, TypeVar

from .timer import BenchmarkResult, Timer
from .memory import MemoryResult, MemorySnapshot

T = TypeVar("T")


@dataclass
class BenchmarkConfig:
    """Configuration for a single benchmark run."""

    iterations: int = 100
    warmup_iterations: int = 5
    setup_fn: Optional[Callable[[], Any]] = None
    teardown_fn: Optional[Callable[[], Any]] = None
    track_memory: bool = False


class Benchmark:
    """Run a callable through setup → warmup → measurement phases."""

    def __init__(self, name: str, fn: Callable[..., Any], config: Optional[BenchmarkConfig] = None) -> None:
        self.name = name
        self.fn = fn
        self.config = config or BenchmarkConfig()
        self.warmup_result: BenchmarkResult = BenchmarkResult()
        self.result: BenchmarkResult = BenchmarkResult()
        self.memory_result: MemoryResult = MemoryResult()

    def run(self) -> Benchmark:
        """Execute the full benchmark pipeline: setup → warmup → measure → teardown."""
        cfg = self.config

        # Setup
        if cfg.setup_fn is not None:
            cfg.setup_fn()

        try:
            # Warmup phase — discard results, let JIT/cache settle
            for _ in range(cfg.warmup_iterations):
                self.fn()

            # Measurement phase
            for _ in range(cfg.iterations):
                if cfg.track_memory:
                    with Timer(self.result):
                        with MemorySnapshot(self.memory_result):
                            self.fn()
                else:
                    with Timer(self.result):
                        self.fn()
        finally:
            # Teardown
            if cfg.teardown_fn is not None:
                cfg.teardown_fn()

        return self

    def summary(self) -> str:
        """Return a human-readable summary of the benchmark result."""
        lines = [
            f"Benchmark: {self.name}",
            f"  Iterations: {self.config.iterations} (warmup: {self.config.warmup_iterations})",
            f"  Wall mean:  {self.result.wall_mean:.6f}s",
            f"  Wall p95:   {self.result.wall_p95:.6f}s",
            f"  Wall p99:   {self.result.wall_p99:.6f}s",
            f"  Wall stddev:{self.result.wall_stddev:.6f}s",
            f"  CPU mean:   {self.result.cpu_mean:.6f}s",
        ]
        if self.config.track_memory and self.memory_result.peak_rss:
            lines.append(f"  Peak RSS:   {self.memory_result.peak_rss_mean:.0f}B")
        return "\n".join(lines)
