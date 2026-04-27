"""Simulate edge device constraints and estimate inference times."""

from __future__ import annotations

import functools
import resource
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, TypeVar

from .timer import BenchmarkResult

T = TypeVar("T")

# Approximate scaling factor from a modern x86_64 CPU to Jetson Orin Nano.
# This is a heuristic: Orin Nano ~ 67 INT8 TOPS, typical desktop CPU ~ 1-2 TFLOPS FP32.
# For simple Python ops we assume CPU-bound workloads run ~8-15x slower on Orin.
JETSON_ORIN_SCALING_FACTOR = 10.0


@dataclass
class EdgeConstraints:
    """Simulated edge device constraints."""

    memory_limit_mb: Optional[int] = None
    max_ops: Optional[int] = None


class EdgeProfiler:
    """Profile workloads under simulated edge constraints."""

    def __init__(self, constraints: Optional[EdgeConstraints] = None) -> None:
        self.constraints = constraints or EdgeConstraints()
        self.op_count: int = 0
        self._original_rlimit: Optional[tuple] = None

    def set_memory_limit(self, limit_mb: int) -> None:
        """Set a soft memory limit (best effort via resource.RLIMIT_AS)."""
        self.constraints.memory_limit_mb = limit_mb
        if sys.platform != "win32":
            limit_bytes = limit_mb * 1024 * 1024
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            self._original_rlimit = (soft, hard)
            new_soft = min(limit_bytes, hard) if hard != resource.RLIM_INFINITY else limit_bytes
            resource.setrlimit(resource.RLIMIT_AS, (new_soft, hard))

    def reset_memory_limit(self) -> None:
        """Restore the original memory limit if it was changed."""
        if self._original_rlimit is not None and sys.platform != "win32":
            resource.setrlimit(resource.RLIMIT_AS, self._original_rlimit)
            self._original_rlimit = None

    def count_ops(self, fn: Callable[..., T], *args, **kwargs) -> T:
        """Wrap a callable to count primitive operations (calls)."""
        self.op_count += 1
        return fn(*args, **kwargs)

    def estimate_jetson_orin_time(self, cpu_result: BenchmarkResult) -> BenchmarkResult:
        """Estimate Jetson Orin inference time by scaling CPU benchmark times."""
        scaled = BenchmarkResult()
        scaled.wall_times = [t * JETSON_ORIN_SCALING_FACTOR for t in cpu_result.wall_times]
        scaled.cpu_times = [t * JETSON_ORIN_SCALING_FACTOR for t in cpu_result.cpu_times]
        return scaled

    def estimate_ops_per_second(self, iterations: int, elapsed_wall: float) -> float:
        """Rough ops/sec estimate based on iteration count."""
        if elapsed_wall <= 0:
            return 0.0
        return iterations / elapsed_wall

    def profile(
        self,
        fn: Callable[..., T],
        *args,
        iterations: int = 100,
        **kwargs,
    ) -> EdgeProfileResult:
        """Run a benchmark under edge constraints and return metrics."""
        from .timer import Timer
        from .memory import MemorySnapshot, MemoryResult

        timer_result = BenchmarkResult()
        memory_result = MemoryResult()

        self.op_count = 0
        for _ in range(iterations):
            with Timer(timer_result):
                with MemorySnapshot(memory_result):
                    fn(*args, **kwargs)
            self.op_count += 1

        return EdgeProfileResult(
            timer=timer_result,
            memory=memory_result,
            op_count=self.op_count,
            estimated_orin=self.estimate_jetson_orin_time(timer_result),
            ops_per_sec=self.estimate_ops_per_second(iterations, timer_result.wall_mean),
        )


@dataclass
class EdgeProfileResult:
    """Aggregated results from an edge profile run."""

    timer: BenchmarkResult
    memory: "MemoryResult"
    op_count: int
    estimated_orin: BenchmarkResult
    ops_per_sec: float
