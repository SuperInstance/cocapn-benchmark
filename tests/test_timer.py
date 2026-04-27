"""Tests for cocapn_benchmark.timer."""

import time

import pytest

from cocapn_benchmark.timer import BenchmarkResult, Timer


def dummy_work():
    time.sleep(0.001)


def test_timer_records_elapsed():
    result = BenchmarkResult()
    with Timer(result) as t:
        dummy_work()
    assert t.wall_elapsed > 0
    assert t.cpu_elapsed >= 0
    assert len(result.wall_times) == 1
    assert len(result.cpu_times) == 1


def test_benchmark_runs_iterations():
    result = Timer.benchmark(dummy_work, iterations=10)
    assert len(result.wall_times) == 10
    assert len(result.cpu_times) == 10
    assert result.wall_mean > 0


def test_percentile():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = BenchmarkResult(wall_times=data, cpu_times=data)
    assert result.wall_p95 == 4.8
    assert result.wall_p99 == 4.96


def test_empty_result_stats():
    result = BenchmarkResult()
    assert result.wall_mean == 0.0
    assert result.wall_median == 0.0
    assert result.wall_p95 == 0.0
    assert result.wall_p99 == 0.0
    assert result.wall_stddev == 0.0


def test_stddev_single_sample():
    result = BenchmarkResult(wall_times=[1.0], cpu_times=[1.0])
    assert result.wall_stddev == 0.0
