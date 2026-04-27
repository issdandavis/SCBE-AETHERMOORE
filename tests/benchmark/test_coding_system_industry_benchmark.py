from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "coding_system_industry_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("coding_system_industry_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_coding_system_industry_benchmark_passes_after_dataset_build() -> None:
    build_spec = importlib.util.spec_from_file_location(
        "build_coding_system_full_sft_for_benchmark",
        ROOT / "scripts" / "build_coding_system_full_sft.py",
    )
    assert build_spec and build_spec.loader
    build_module = importlib.util.module_from_spec(build_spec)
    sys.modules[build_spec.name] = build_module
    build_spec.loader.exec_module(build_module)
    manifest = build_module.build()

    module = _load_module()
    report = module.build_report(Path(manifest["outputs"]["train"]), Path(manifest["outputs"]["holdout"]))

    assert report["decision"] == "PASS"
    assert report["summary"]["python_executable_pass_rate"] == 1.0
    assert report["summary"]["full_lane_pass"] is True
    assert report["lane_integrity"]["primary_coverage_ok"] is True
    assert report["lane_integrity"]["language_coverage_ok"] is True
    assert report["lane_integrity"]["music_mode_coverage_ok"] is True
    assert not report["lane_integrity"]["hash_failures"]
    assert not report["lane_integrity"]["hex_failures"]

    full = next(row for row in report["toolkit_comparison"] if row["toolkit"] == "scbe_full_coding_system_v1")
    assert full["score"] == 1.0


def test_coding_system_industry_benchmark_emits_serializable_report() -> None:
    module = _load_module()
    report = module.build_report(
        ROOT / "training-data" / "sft" / "coding_system_full_v1_train.sft.jsonl",
        ROOT / "training-data" / "sft" / "coding_system_full_v1_holdout.sft.jsonl",
    )
    encoded = json.dumps(report, sort_keys=True)
    assert "HumanEval_MBPP_style" in encoded
    assert "SWE_bench_Terminal_Bench_style" in encoded
