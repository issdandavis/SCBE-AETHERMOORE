from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "hard_agentic_benchmark_pretest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("hard_agentic_benchmark_pretest", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_target_matrix_includes_hard_public_benchmarks() -> None:
    module = _load_module()

    ids = {target.benchmark_id for target in module.TARGETS}

    assert "terminal_bench" in ids
    assert "swe_bench_verified_readiness" in ids
    assert "arc_agi_2" in ids
    assert "mle_bench" in ids
    assert "browsecomp" in ids
    assert "gaia" in ids
    assert "webarena_visualwebarena" in ids
    assert "osworld" in ids
    assert "vending_bench" in ids
    assert "scbe_pathfinding_suite" in ids


def test_pretest_report_writes_filtered_result(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(
        tmp_path,
        timeout=30,
        filter_ids={"browsecomp"},
    )
    payload = report["payload"]

    assert payload["schema_version"] == "scbe_hard_agentic_benchmark_pretest_v1"
    assert payload["summary"]["target_count"] == 1
    assert payload["results"][0]["benchmark_id"] == "browsecomp"
    assert payload["results"][0]["missing_link"]
    assert Path(report["json"]).exists()
    assert Path(report["markdown"]).exists()


def test_pretest_cli_filter_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/hard_agentic_benchmark_pretest.py",
            "--filter",
            "browsecomp",
            "--out-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    assert "ready_or_pass=" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()
