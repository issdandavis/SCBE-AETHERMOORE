from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "primeir_speed_coding_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("primeir_speed_coding_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_primeir_speed_coding_passes_python_javascript_pack(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(
        out_dir=tmp_path,
        run_id="pytest-primeir-speed",
        languages=("python", "javascript"),
    )

    summary = report["summary"]
    assert summary["decision"] == "PASS"
    assert summary["requested_cells"] == 10
    assert summary["primeir_passed_cells"] == 10
    assert summary["single_surface_baseline_cells"] == 5
    assert summary["coverage_gain_vs_single_surface"] == 2.0
    assert summary["authoring_compression_ratio"] == round(10 / 7, 3)
    assert report["collapse"]["collapse_ok"] is True
    assert (tmp_path / "pytest-primeir-speed" / "report.json").exists()
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_primeir_receipts_collapse_by_operation_not_language() -> None:
    module = _load_module()

    receipts = module.build_receipts(("python", "javascript", "rust"))
    by_op: dict[str, set[str]] = {}
    by_language: dict[str, set[int]] = {}
    for receipt in receipts:
        by_op.setdefault(receipt.op_id, set()).add(receipt.collapse_key)
        by_language.setdefault(receipt.language, set()).add(receipt.language_prime)

    assert all(len(keys) == 1 for keys in by_op.values())
    assert len({next(iter(keys)) for keys in by_op.values()}) == len(by_op)
    assert by_language == {"python": {2}, "javascript": {3}, "rust": {5}}


def test_primeir_rust_surface_is_generated_without_execution_dependency() -> None:
    module = _load_module()

    source = module.render_rust()

    assert "fn safe_divide" in source
    assert "fn should_retry" in source
    assert 'println!("primeir-rust-ok")' in source
