from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "cli_competitive_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cli_competitive_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_geoseal_doctor_outputs_machine_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "doctor", "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["version"]
    assert "status" in payload["api_commands"]
    assert payload["python_modules"]


def test_api_only_command_without_service_returns_actionable_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "status", "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["error"] == "api_command_requires_service"
    assert "geoseal doctor --json" in payload["fixes"]


def test_cli_competitive_report_contains_scbe_and_peers() -> None:
    module = _load_module()
    report = module.build_report()
    assert report["schema_version"] == "scbe_cli_competitive_benchmark_v1"
    assert report["scbe"]["name"] == "scbe-geoseal"
    assert report["scbe"]["capabilities"]["doctor"] is True
    assert {peer["name"] for peer in report["peers"]} >= {"codex", "claude", "gemini", "aider"}
    assert report["ranking"]
