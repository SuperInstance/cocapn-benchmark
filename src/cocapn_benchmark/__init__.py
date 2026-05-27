"""Cocapn Benchmark Suite - Pure Python benchmarking for Cocapn fleet packages."""

__version__ = "0.2.0"

from .timer import BenchmarkResult, Timer
from .memory import MemorySnapshot, MemoryResult
from .benchmark import Benchmark, BenchmarkConfig
from .suite import BenchmarkSuite
from .compare import CompareSuite, compare_results
from .report import BenchmarkReport, RegressionConfig, RegressionResult
from .edge_profile import EdgeProfiler

__all__ = [
    "__version__",
    "BenchmarkResult",
    "Timer",
    "MemorySnapshot",
    "MemoryResult",
    "Benchmark",
    "BenchmarkConfig",
    "BenchmarkSuite",
    "CompareSuite",
    "compare_results",
    "BenchmarkReport",
    "RegressionConfig",
    "RegressionResult",
    "EdgeProfiler",
]
