from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "longform_cli_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("longform_cli_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_longform_benchmark_requires_dispatch_and_headed_headless_parity() -> None:
    module = _load_module()
    report = module.run_benchmark()

    execution = report["checks"]["execution_depth"]
    parity = report["checks"]["headed_headless_parity"]

    assert execution["actual_tool_or_bus_dispatch"] is True
    assert execution["dispatched_stage_count"] == execution["stage_complete_count"]
    assert execution["dispatch_enabled_count"] == execution["stage_complete_count"]
    assert execution["stubbed_stage_count"] == 0
    assert parity["ok"] is True
    assert report["score"]["score_percent"] == 100.0
    assert report["score"]["blockers"] == []
