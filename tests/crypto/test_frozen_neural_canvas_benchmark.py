"""Small deterministic integration check for the frozen-canvas benchmark."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "benchmark" / "frozen_neural_canvas_benchmark.py"
SPEC = importlib.util.spec_from_file_location("frozen_neural_canvas_benchmark", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)


def test_small_benchmark_is_deterministic_and_never_trains() -> None:
    first = BENCHMARK.run(instance_start=30_000, instances=3)
    second = BENCHMARK.run(instance_start=30_000, instances=3)
    first.pop("elapsed_seconds")
    second.pop("elapsed_seconds")
    assert first == second
    assert first["network"]["optimizer_steps"] == 0
    assert first["network"]["learned_readout"] is False
    assert first["network"]["adaptive_selection"] is False
    assert len(first["rows"]) == 3
    assert all(row["fixed_forward_calls"] == 3 * 34 for row in first["rows"])


def test_invalid_benchmark_bounds_fail_closed() -> None:
    for kwargs in ({"instance_start": -1, "instances": 1}, {"instance_start": 0, "instances": 0}):
        try:
            BENCHMARK.run(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid benchmark bounds were accepted")
