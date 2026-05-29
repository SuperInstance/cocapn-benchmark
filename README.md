# cocapn-benchmark — Fleet Performance Testing

**Benchmark fleet packages, detect regressions, profile edge hardware. Pure Python.**

## What This Gives You

- **Timer benchmarks** — high-resolution timing with statistical analysis (mean, median, p95, p99, std dev)
- **Memory profiling** — track memory allocation during benchmark runs
- **Benchmark suites** — group and run benchmarks together with setup/teardown lifecycle
- **Regression detection** — compare runs against baselines, flag regressions automatically
- **Edge profiler** — profile performance on edge/constrained hardware targets
- **Comparison reports** — side-by-side results in markdown, JSON, or terminal tables

## Quick Start

```bash
pip install cocapn-benchmark
```

```python
from cocapn_benchmark import Benchmark, BenchmarkSuite, BenchmarkReport

# Benchmark a function
bench = Benchmark("json_parse", lambda: __import__("json").loads('{"key": "value"}'))
bench.run()
print(bench.result)  # BenchmarkResult with timing stats

# Build a suite
suite = BenchmarkSuite("fleet-core")
suite.add(Benchmark("tile_create", lambda: Tile("Q", "A")))
suite.add(Benchmark("room_query", lambda: room.ask("test")))
results = suite.run_all()

# Generate a report
report = BenchmarkReport(suite_results=results)
print(report.to_markdown())

# Regression check
from cocapn_benchmark import RegressionConfig
config = RegressionConfig(max_slowdown_pct=10.0)
regressions = report.check_regressions(baseline, config)
```

## API Reference

### `Benchmark(name, fn, config=None)`
Runs `fn` through setup → warmup → measurement → teardown.

### `BenchmarkConfig(iterations=100, warmup=5, track_memory=False)`
### `BenchmarkSuite(name)` — Group benchmarks, run together
### `BenchmarkReport` — Markdown/JSON report generation
### `RegressionConfig` — Threshold-based regression detection
### `EdgeProfiler` — Constrained-device profiling
### `Timer` — Raw high-resolution timer
### `MemorySnapshot` — Memory tracking

## How It Fits
- [OpenConstruct Documentation](https://github.com/SuperInstance/openconstruct-docs) — ecosystem-wide docs and guides

Performance backbone for the [SuperInstance fleet](https://github.com/SuperInstance). Every package runs through `cocapn-benchmark` before release.

- **[cocapn](https://github.com/SuperInstance/cocapn)** — Core agent infrastructure
- **[cocapn-health-rs](https://github.com/SuperInstance/cocapn-health-rs)** — Fleet health (Rust)
- **[cocapn-cli](https://github.com/SuperInstance/cocapn-cli)** — Terminal output formatting

## Testing

```bash
pip install pytest
pytest tests/
```

## Installation

```bash
pip install cocapn-benchmark
```

Python 3.10+. MIT license.
