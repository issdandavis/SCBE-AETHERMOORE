from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "eval" / "compare_functional_benchmark_reports.py"


def load_module():
    spec = importlib.util.spec_from_file_location("_compare_functional_benchmark_reports_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compare_reports_emits_pass_rate_delta():
    module = load_module()

    baseline = {
        "results": [
            {"adapter": "BASE", "summary": {"tasks": 4, "passed": 2, "pass_rate": 0.5}},
        ]
    }
    candidate = {
        "results": [
            {"adapter": "BASE", "summary": {"tasks": 4, "passed": 3, "pass_rate": 0.75}},
        ]
    }

    payload = module.compare_reports(candidate, baseline)

    assert payload["schema"] == "scbe_functional_coding_agent_report_compare_v1"
    assert payload["deltas"][0]["adapter"] == "BASE"
    assert payload["deltas"][0]["delta_pass_rate"] == 0.25
