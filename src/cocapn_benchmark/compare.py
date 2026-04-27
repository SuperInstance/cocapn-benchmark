"""Compare two benchmark results, show % difference and winner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .timer import BenchmarkResult


@dataclass
class Comparison:
    """Result of comparing two BenchmarkResult objects."""

    baseline: BenchmarkResult
    contender: BenchmarkResult
    wall_diff_pct: float = 0.0
    cpu_diff_pct: float = 0.0
    winner: Optional[str] = None

    def __post_init__(self) -> None:
        self.wall_diff_pct = _pct_diff(self.baseline.wall_mean, self.contender.wall_mean)
        self.cpu_diff_pct = _pct_diff(self.baseline.cpu_mean, self.contender.cpu_mean)
        if self.wall_diff_pct < 0:
            self.winner = "contender"
        elif self.wall_diff_pct > 0:
            self.winner = "baseline"
        else:
            self.winner = "tie"

    def summary(self) -> str:
        lines = [
            "Comparison Summary",
            f"  Wall time: {self.wall_diff_pct:+.2f}% (baseline -> contender)",
            f"  CPU time:  {self.cpu_diff_pct:+.2f}% (baseline -> contender)",
            f"  Winner:    {self.winner}",
        ]
        return "\n".join(lines)


def _pct_diff(baseline: float, contender: float) -> float:
    if baseline == 0:
        return 0.0 if contender == 0 else float("inf")
    return ((contender - baseline) / baseline) * 100.0


def compare_results(baseline: BenchmarkResult, contender: BenchmarkResult) -> Comparison:
    """Compare two benchmark results and return a Comparison."""
    return Comparison(baseline=baseline, contender=contender)


class CompareSuite:
    """A/B testing across named benchmarks."""

    def __init__(self) -> None:
        self.baselines: Dict[str, BenchmarkResult] = {}
        self.contenders: Dict[str, BenchmarkResult] = {}

    def add_baseline(self, name: str, result: BenchmarkResult) -> CompareSuite:
        self.baselines[name] = result
        return self

    def add_contender(self, name: str, result: BenchmarkResult) -> CompareSuite:
        self.contenders[name] = result
        return self

    def compare(self, name: str) -> Comparison:
        if name not in self.baselines:
            raise KeyError(f"No baseline for '{name}'")
        if name not in self.contenders:
            raise KeyError(f"No contender for '{name}'")
        return compare_results(self.baselines[name], self.contenders[name])

    def report(self) -> str:
        lines: List[str] = []
        lines.append("-" * 80)
        lines.append(f"{'Benchmark':<20} {'Wall %Δ':<15} {'CPU %Δ':<15} {'Winner':<15}")
        lines.append("-" * 80)
        for name in sorted(set(self.baselines) & set(self.contenders)):
            comp = self.compare(name)
            lines.append(
                f"{name:<20} {comp.wall_diff_pct:<+15.2f} {comp.cpu_diff_pct:<+15.2f} {comp.winner or 'tie':<15}"
            )
        lines.append("-" * 80)
        return "\n".join(lines)
