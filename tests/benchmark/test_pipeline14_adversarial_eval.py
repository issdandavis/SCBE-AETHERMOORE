from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "pipeline14_adversarial_eval.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pipeline14_adversarial_eval_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pipeline14_eval_reports_asr_by_distance_bin() -> None:
    module = _load_module()
    report = module.run_eval()

    assert report["schema_version"] == "pipeline14_adversarial_eval_v1"
    assert report["summary"]["attacks"] >= 50
    assert report["summary"]["benign"] >= 5
    bins = report["attack_success_by_distance_bin"]
    assert bins["0.0-1.0"]["attacks"] > 0
    assert bins["2.0-4.0"]["attacks"] > 0
    assert bins["4.0+"]["attacks"] > 0
    assert bins["2.0-4.0"]["attack_success_rate"] == 0.0
    assert bins["4.0+"]["attack_success_rate"] == 0.0
    assert report["summary"]["false_positive_rate"] == 0.0
