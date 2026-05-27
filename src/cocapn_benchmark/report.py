"""BenchmarkReport — percentile stats, regression detection, and formatted output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .timer import BenchmarkResult
from .benchmark import Benchmark


@dataclass
class RegressionResult:
    """Outcome of a regression check on a single metric."""

    metric: str
    baseline_value: float
    current_value: float
    diff_pct: float
    threshold_pct: float
    is_regression: bool

    def summary(self) -> str:
        flag = " ⚠️ REGRESSION" if self.is_regression else " ✅ OK"
        return (
            f"  {self.metric}: {self.baseline_value:.6f} → {self.current_value:.6f} "
            f"({self.diff_pct:+.2f}%, threshold: {self.threshold_pct:.1f}%){flag}"
        )


@dataclass
class RegressionConfig:
    """Thresholds for regression detection."""

    wall_mean_threshold_pct: float = 10.0
    wall_p95_threshold_pct: float = 15.0
    cpu_mean_threshold_pct: float = 10.0


class BenchmarkReport:
    """Collect benchmark results and produce reports with regression detection."""

    def __init__(self, regression_config: Optional[RegressionConfig] = None) -> None:
        self.regression_config = regression_config or RegressionConfig()
        self._results: Dict[str, BenchmarkResult] = {}
        self._baselines: Dict[str, BenchmarkResult] = {}

    def add_result(self, name: str, result: BenchmarkResult) -> BenchmarkReport:
        """Add a benchmark result to the report."""
        self._results[name] = result
        return self

    def add_benchmark(self, benchmark: Benchmark) -> BenchmarkReport:
        """Add a Benchmark object to the report."""
        self._results[benchmark.name] = benchmark.result
        return self

    def set_baseline(self, name: str, result: BenchmarkResult) -> BenchmarkReport:
        """Set a baseline result for regression detection."""
        self._baselines[name] = result
        return self

    def check_regression(self, name: str) -> List[RegressionResult]:
        """Check a named result against its baseline for regressions."""
        if name not in self._results:
            raise KeyError(f"No result for '{name}'")
        if name not in self._baselines:
            raise KeyError(f"No baseline for '{name}'")

        current = self._results[name]
        baseline = self._baselines[name]
        cfg = self.regression_config
        results: List[RegressionResult] = []

        checks: List[Tuple[str, float, float, float]] = [
            ("wall_mean", baseline.wall_mean, current.wall_mean, cfg.wall_mean_threshold_pct),
            ("wall_p95", baseline.wall_p95, current.wall_p95, cfg.wall_p95_threshold_pct),
            ("cpu_mean", baseline.cpu_mean, current.cpu_mean, cfg.cpu_mean_threshold_pct),
        ]

        for metric_name, base_val, cur_val, threshold in checks:
            diff = _pct_diff(base_val, cur_val)
            results.append(RegressionResult(
                metric=metric_name,
                baseline_value=base_val,
                current_value=cur_val,
                diff_pct=diff,
                threshold_pct=threshold,
                is_regression=diff > threshold,
            ))

        return results

    def check_all_regressions(self) -> Dict[str, List[RegressionResult]]:
        """Check all results that have baselines."""
        out: Dict[str, List[RegressionResult]] = {}
        for name in sorted(set(self._results) & set(self._baselines)):
            out[name] = self.check_regression(name)
        return out

    def percentile_table(self) -> str:
        """Produce a percentile stats table for all results."""
        lines: List[str] = []
        lines.append("=" * 100)
        lines.append(
            f"{'Benchmark':<20} {'Mean (s)':<12} {'Median (s)':<12} "
            f"{'P95 (s)':<12} {'P99 (s)':<12} {'StdDev':<12} {'Samples':<8}"
        )
        lines.append("=" * 100)
        for name in sorted(self._results):
            r = self._results[name]
            lines.append(
                f"{name:<20} {r.wall_mean:<12.6f} {r.wall_median:<12.6f} "
                f"{r.wall_p95:<12.6f} {r.wall_p99:<12.6f} "
                f"{r.wall_stddev:<12.6f} {len(r.wall_times):<8}"
            )
        lines.append("=" * 100)
        return "\n".join(lines)

    def regression_report(self) -> str:
        """Produce a full regression report."""
        all_checks = self.check_all_regressions()
        if not all_checks:
            return "No baselines set — nothing to compare."

        lines: List[str] = ["Regression Report", "=" * 60]
        any_regression = False
        for name, checks in all_checks.items():
            lines.append(f"\n{name}:")
            for check in checks:
                lines.append(check.summary())
                if check.is_regression:
                    any_regression = True

        if any_regression:
            lines.append("\n⚠️  Performance regressions detected!")
        else:
            lines.append("\n✅ No regressions detected.")

        return "\n".join(lines)

    def full_report(self) -> str:
        """Percentile table + regression report."""
        parts = [self.percentile_table()]
        if self._baselines:
            parts.append(self.regression_report())
        return "\n\n".join(parts)


def _pct_diff(baseline: float, current: float) -> float:
    if baseline == 0:
        return 0.0 if current == 0 else float("inf")
    return ((current - baseline) / baseline) * 100.0
