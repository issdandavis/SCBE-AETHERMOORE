from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "setup_public_agentic_benchmarks.py"
CONFIG_PATH = ROOT / "config" / "eval" / "public_agentic_benchmark_sources.v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("setup_public_agentic_benchmarks", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_agentic_benchmark_sources_load() -> None:
    module = _load_module()
    source_root, sources = module.load_sources(CONFIG_PATH)

    assert source_root == ROOT / "external" / "benchmarks"
    assert {source.benchmark_id for source in sources} == {
        "terminal_bench",
        "swe_bench",
        "aider_polyglot",
    }
    assert all(source.repo_url.startswith("https://github.com/") for source in sources)


def test_setup_public_agentic_benchmarks_plan_report(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(CONFIG_PATH, tmp_path, download=False, run_dry=False)
    payload = report["payload"]

    assert payload["schema_version"] == "scbe_public_agentic_benchmark_setup_v1"
    assert payload["ok"] is True
    assert payload["full_run_ready"] is False
    assert len(payload["results"]) == 3
    assert Path(report["json"]).exists()
    assert Path(report["markdown"]).exists()


def test_setup_public_agentic_benchmarks_cli_dry_run() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/setup_public_agentic_benchmarks.py",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=90,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["full_run_ready"] is False
    assert payload["next_steps"]
