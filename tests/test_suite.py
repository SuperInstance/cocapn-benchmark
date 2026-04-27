"""Tests for cocapn_benchmark.suite and compare."""

import time

from cocapn_benchmark.suite import BenchmarkSuite
from cocapn_benchmark.compare import CompareSuite, compare_results
from cocapn_benchmark.timer import BenchmarkResult


def fast_fn():
    pass


def slow_fn():
    time.sleep(0.002)


def test_suite_add_and_run():
    suite = BenchmarkSuite()
    suite.add("fast", fast_fn).add("slow", slow_fn)
    suite.run(iterations=3)
    assert len(suite._entries) == 2
    assert len(suite._entries[0].timer_result.wall_times) == 3


def test_suite_report():
    suite = BenchmarkSuite()
    suite.add("fast", fast_fn)
    suite.run(iterations=2)
    report = suite.report()
    assert "Benchmark" in report
    assert "fast" in report


def test_compare_results():
    baseline = BenchmarkResult(wall_times=[1.0, 1.0], cpu_times=[1.0, 1.0])
    contender = BenchmarkResult(wall_times=[2.0, 2.0], cpu_times=[2.0, 2.0])
    comp = compare_results(baseline, contender)
    assert comp.wall_diff_pct == 100.0
    assert comp.winner == "contender"


def test_compare_suite():
    cs = CompareSuite()
    cs.add_baseline("a", BenchmarkResult(wall_times=[1.0], cpu_times=[1.0]))
    cs.add_contender("a", BenchmarkResult(wall_times=[0.5], cpu_times=[0.5]))
    comp = cs.compare("a")
    assert comp.winner == "baseline"
    report = cs.report()
    assert "a" in report
