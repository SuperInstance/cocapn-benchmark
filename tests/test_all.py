"""Comprehensive tests for cocapn_benchmark."""

import time

import pytest

from cocapn_benchmark.timer import BenchmarkResult, Timer
from cocapn_benchmark.memory import MemorySnapshot, MemoryResult
from cocapn_benchmark.benchmark import Benchmark, BenchmarkConfig
from cocapn_benchmark.suite import BenchmarkSuite
from cocapn_benchmark.compare import CompareSuite, compare_results, Comparison
from cocapn_benchmark.report import BenchmarkReport, RegressionConfig, RegressionResult
from cocapn_benchmark.edge_profile import EdgeProfiler, EdgeConstraints, EdgeProfileResult


# ── Timer tests ──────────────────────────────────────────────────────────────

class TestBenchmarkResult:
    def test_empty_stats(self):
        r = BenchmarkResult()
        assert r.wall_mean == 0.0
        assert r.wall_median == 0.0
        assert r.wall_p95 == 0.0
        assert r.wall_p99 == 0.0
        assert r.wall_stddev == 0.0
        assert r.cpu_mean == 0.0
        assert r.cpu_stddev == 0.0

    def test_single_sample_stddev(self):
        r = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        assert r.wall_stddev == 0.0
        assert r.cpu_stddev == 0.0

    def test_percentile_exact(self):
        r = BenchmarkResult(wall_times=[1.0, 2.0, 3.0, 4.0, 5.0], cpu_times=[1.0])
        assert r.wall_p95 == pytest.approx(4.8)
        assert r.wall_p99 == pytest.approx(4.96)

    def test_mean_and_median(self):
        r = BenchmarkResult(wall_times=[1.0, 2.0, 3.0])
        assert r.wall_mean == pytest.approx(2.0)
        assert r.wall_median == pytest.approx(2.0)


class TestTimer:
    def test_context_manager(self):
        r = BenchmarkResult()
        with Timer(r) as t:
            time.sleep(0.001)
        assert t.wall_elapsed > 0
        assert t.cpu_elapsed >= 0
        assert len(r.wall_times) == 1

    def test_benchmark_classmethod(self):
        r = Timer.benchmark(lambda: None, iterations=20)
        assert len(r.wall_times) == 20
        assert r.wall_mean >= 0

    def test_default_result(self):
        t = Timer()
        with t:
            pass
        assert t.result is not None
        assert len(t.result.wall_times) == 1


# ── Memory tests ─────────────────────────────────────────────────────────────

class TestMemorySnapshot:
    def test_records_memory(self):
        r = MemoryResult()
        with MemorySnapshot(r):
            _ = [i * 2 for i in range(1000)]
        assert len(r.peak_rss) == 1
        assert r.peak_rss[0] > 0

    def test_multiple_snapshots(self):
        r = MemoryResult()
        for _ in range(3):
            with MemorySnapshot(r):
                pass
        assert len(r.peak_rss) == 3

    def test_mean_properties(self):
        r = MemoryResult(peak_rss=[100, 200], current_allocs=[50, 150])
        assert r.peak_rss_mean == pytest.approx(150.0)
        assert r.current_allocs_mean == pytest.approx(100.0)

    def test_empty_mean(self):
        r = MemoryResult()
        assert r.peak_rss_mean == 0.0


# ── Benchmark tests ──────────────────────────────────────────────────────────

class TestBenchmark:
    def test_basic_run(self):
        b = Benchmark("simple", lambda: None)
        b.run()
        assert len(b.result.wall_times) == b.config.iterations

    def test_custom_config(self):
        cfg = BenchmarkConfig(iterations=5, warmup_iterations=2)
        b = Benchmark("custom", lambda: None, config=cfg)
        b.run()
        assert len(b.result.wall_times) == 5

    def test_setup_and_teardown(self):
        log = []
        cfg = BenchmarkConfig(
            iterations=3,
            warmup_iterations=1,
            setup_fn=lambda: log.append("setup"),
            teardown_fn=lambda: log.append("teardown"),
        )
        b = Benchmark("hooks", lambda: log.append("run"), config=cfg)
        b.run()
        assert log[0] == "setup"
        assert log[-1] == "teardown"
        # warmup (1) + iterations (3) = 4 runs total
        assert log.count("run") == 4

    def test_teardown_called_on_exception(self):
        log = []
        cfg = BenchmarkConfig(
            iterations=1,
            teardown_fn=lambda: log.append("teardown"),
        )

        def boom():
            raise RuntimeError("boom")

        b = Benchmark("fail", boom, config=cfg)
        with pytest.raises(RuntimeError):
            b.run()
        assert "teardown" in log

    def test_summary(self):
        b = Benchmark("sumtest", lambda: time.sleep(0.001), config=BenchmarkConfig(iterations=3))
        b.run()
        s = b.summary()
        assert "sumtest" in s
        assert "Wall mean" in s

    def test_memory_tracking(self):
        cfg = BenchmarkConfig(iterations=2, track_memory=True)
        b = Benchmark("mem", lambda: None, config=cfg)
        b.run()
        assert len(b.memory_result.peak_rss) == 2


# ── Suite tests ──────────────────────────────────────────────────────────────

class TestBenchmarkSuite:
    def test_add_and_run(self):
        suite = BenchmarkSuite()
        suite.add("fast", lambda: None).add("slow", lambda: time.sleep(0.001))
        suite.run(iterations=3)
        assert len(suite._entries) == 2
        assert len(suite._entries[0].timer_result.wall_times) == 3

    def test_report_contains_names(self):
        suite = BenchmarkSuite()
        suite.add("alpha", lambda: None)
        suite.run(iterations=2)
        report = suite.report()
        assert "alpha" in report

    def test_chaining(self):
        suite = BenchmarkSuite().add("a", lambda: None).add("b", lambda: None)
        suite.run(iterations=1)
        assert len(suite._entries) == 2


# ── Compare tests ────────────────────────────────────────────────────────────

class TestCompare:
    def test_contender_faster(self):
        base = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        cont = BenchmarkResult(wall_times=[0.5], cpu_times=[0.5])
        comp = compare_results(base, cont)
        assert comp.winner == "contender"
        assert comp.wall_diff_pct == pytest.approx(-50.0)

    def test_baseline_faster(self):
        base = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        cont = BenchmarkResult(wall_times=[2.0], cpu_times=[2.0])
        comp = compare_results(base, cont)
        assert comp.winner == "baseline"
        assert comp.wall_diff_pct == pytest.approx(100.0)

    def test_tie(self):
        r = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        comp = compare_results(r, r)
        assert comp.winner == "tie"
        assert comp.wall_diff_pct == pytest.approx(0.0)

    def test_zero_baseline(self):
        base = BenchmarkResult(wall_times=[0.0], cpu_times=[0.0])
        cont = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        comp = compare_results(base, cont)
        assert comp.wall_diff_pct == float("inf")

    def test_comparison_summary(self):
        base = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        cont = BenchmarkResult(wall_times=[2.0], cpu_times=[2.0])
        comp = compare_results(base, cont)
        s = comp.summary()
        assert "Comparison Summary" in s


class TestCompareSuite:
    def test_compare_suite(self):
        cs = CompareSuite()
        cs.add_baseline("a", BenchmarkResult(wall_times=[1.0], cpu_times=[1.0]))
        cs.add_contender("a", BenchmarkResult(wall_times=[0.5], cpu_times=[0.5]))
        comp = cs.compare("a")
        assert comp.winner == "contender"

    def test_compare_missing_baseline(self):
        cs = CompareSuite()
        with pytest.raises(KeyError):
            cs.compare("missing")

    def test_report(self):
        cs = CompareSuite()
        cs.add_baseline("x", BenchmarkResult(wall_times=[1.0], cpu_times=[1.0]))
        cs.add_contender("x", BenchmarkResult(wall_times=[1.0], cpu_times=[1.0]))
        report = cs.report()
        assert "x" in report


# ── Report tests ─────────────────────────────────────────────────────────────

class TestBenchmarkReport:
    def test_percentile_table(self):
        report = BenchmarkReport()
        report.add_result("test", BenchmarkResult(wall_times=[0.1, 0.2, 0.3]))
        table = report.percentile_table()
        assert "test" in table
        assert "Mean" in table

    def test_regression_detection_pass(self):
        cfg = RegressionConfig(wall_mean_threshold_pct=50.0, wall_p95_threshold_pct=50.0, cpu_mean_threshold_pct=50.0)
        report = BenchmarkReport(regression_config=cfg)
        base = BenchmarkResult(wall_times=[1.0, 1.0], cpu_times=[1.0, 1.0])
        cur = BenchmarkResult(wall_times=[1.1, 1.1], cpu_times=[1.1, 1.1])
        report.set_baseline("ok", base)
        report.add_result("ok", cur)
        checks = report.check_regression("ok")
        assert all(not c.is_regression for c in checks)

    def test_regression_detection_fail(self):
        cfg = RegressionConfig(wall_mean_threshold_pct=5.0)
        report = BenchmarkReport(regression_config=cfg)
        base = BenchmarkResult(wall_times=[1.0, 1.0], cpu_times=[1.0, 1.0])
        cur = BenchmarkResult(wall_times=[2.0, 2.0], cpu_times=[2.0, 2.0])
        report.set_baseline("bad", base)
        report.add_result("bad", cur)
        checks = report.check_regression("bad")
        wall_check = [c for c in checks if c.metric == "wall_mean"][0]
        assert wall_check.is_regression

    def test_check_all_regressions(self):
        report = BenchmarkReport(regression_config=RegressionConfig(wall_mean_threshold_pct=5.0))
        base = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        cur = BenchmarkResult(wall_times=[2.0], cpu_times=[2.0])
        report.set_baseline("x", base)
        report.add_result("x", cur)
        report.set_baseline("y", base)
        report.add_result("y", cur)
        all_checks = report.check_all_regressions()
        assert "x" in all_checks
        assert "y" in all_checks

    def test_regression_missing_result(self):
        report = BenchmarkReport()
        report.set_baseline("x", BenchmarkResult(wall_times=[1.0]))
        with pytest.raises(KeyError):
            report.check_regression("x")

    def test_regression_missing_baseline(self):
        report = BenchmarkReport()
        report.add_result("x", BenchmarkResult(wall_times=[1.0]))
        with pytest.raises(KeyError):
            report.check_regression("x")

    def test_regression_report_output(self):
        cfg = RegressionConfig(wall_mean_threshold_pct=5.0)
        report = BenchmarkReport(regression_config=cfg)
        base = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        cur = BenchmarkResult(wall_times=[2.0], cpu_times=[2.0])
        report.set_baseline("r", base)
        report.add_result("r", cur)
        text = report.regression_report()
        assert "REGRESSION" in text

    def test_regression_report_no_baselines(self):
        report = BenchmarkReport()
        text = report.regression_report()
        assert "No baselines" in text

    def test_full_report(self):
        report = BenchmarkReport()
        report.add_result("f", BenchmarkResult(wall_times=[0.1, 0.2]))
        report.set_baseline("f", BenchmarkResult(wall_times=[0.1]))
        text = report.full_report()
        assert "f" in text

    def test_add_benchmark_object(self):
        b = Benchmark("bm", lambda: None, config=BenchmarkConfig(iterations=2))
        b.run()
        report = BenchmarkReport()
        report.add_benchmark(b)
        table = report.percentile_table()
        assert "bm" in table


# ── Edge Profile tests ───────────────────────────────────────────────────────

class TestEdgeProfiler:
    def test_estimate_jetson_orin_time(self):
        profiler = EdgeProfiler()
        result = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
        scaled = profiler.estimate_jetson_orin_time(result)
        assert scaled.wall_times[0] == pytest.approx(10.0)

    def test_estimate_ops_per_second(self):
        profiler = EdgeProfiler()
        ops = profiler.estimate_ops_per_second(100, 0.5)
        assert ops == pytest.approx(200.0)

    def test_estimate_ops_zero_time(self):
        profiler = EdgeProfiler()
        assert profiler.estimate_ops_per_second(100, 0.0) == 0.0

    def test_count_ops(self):
        profiler = EdgeProfiler()
        profiler.count_ops(lambda: None)
        assert profiler.op_count == 1

    def test_profile(self):
        profiler = EdgeProfiler()
        result = profiler.profile(lambda: None, iterations=5)
        assert isinstance(result, EdgeProfileResult)
        assert result.op_count == 5
        assert len(result.timer.wall_times) == 5

    def test_constraints_default(self):
        profiler = EdgeProfiler()
        assert profiler.constraints.memory_limit_mb is None


# ── Integration test ─────────────────────────────────────────────────────────

class TestIntegration:
    def test_full_workflow(self):
        """End-to-end: suite → compare → report."""
        # Run benchmarks
        suite = BenchmarkSuite()
        suite.add("sort", lambda: sorted(range(1000, 0, -1)))
        suite.add("noop", lambda: None)
        suite.run(iterations=10)

        # Build report
        report = BenchmarkReport()
        for entry in suite._entries:
            report.add_result(entry.name, entry.timer_result)

        # Baselines for regression
        report.set_baseline("sort", BenchmarkResult(wall_times=[0.0001], cpu_times=[0.0001]))
        report.set_baseline("noop", BenchmarkResult(wall_times=[0.0001], cpu_times=[0.0001]))

        full = report.full_report()
        assert "sort" in full
        assert "noop" in full

        # Compare
        cs = CompareSuite()
        cs.add_baseline("sort", suite._entries[0].timer_result)
        contender = BenchmarkResult(wall_times=[0.0001], cpu_times=[0.0001])
        cs.add_contender("sort", contender)
        comp = cs.compare("sort")
        assert comp.winner is not None
