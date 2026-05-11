from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "public_agentic_cli_suite.py"
CONFIG_PATH = ROOT / "config" / "eval" / "public_agentic_cli_suite.v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("public_agentic_cli_suite", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_agentic_cli_suite_config_validates() -> None:
    module = _load_module()
    validation = module.validate_config(CONFIG_PATH)
    assert validation["ok"], validation
    assert validation["track_count"] >= 4


def test_public_agentic_cli_suite_required_tracks_and_claim_guardrails() -> None:
    module = _load_module()
    config = module.load_config(CONFIG_PATH)
    tracks = module.load_tracks(config)
    track_ids = {track.track_id for track in tracks}

    assert {
        "geoseal_cli_competitive",
        "terminal_bench",
        "swe_bench_verified_or_lite",
        "aider_polyglot",
    }.issubset(track_ids)
    assert any("all-around best coding agent" in item for item in config["claim_policy"]["forbidden_now"])
    required_core = {
        "geoseal_cli_competitive",
        "terminal_bench",
        "swe_bench_verified_or_lite",
        "aider_polyglot",
    }
    assert all(
        track.required_for_public_all_around_claim
        for track in tracks
        if track.track_id in required_core
    )


def test_public_agentic_cli_suite_plan_report_does_not_overclaim(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(CONFIG_PATH, tmp_path, execute=False, timeout=60)
    payload = report["payload"]

    assert payload["schema_version"] == "scbe_public_agentic_cli_suite_report_v1"
    assert payload["summary"]["all_required_public_ready"] is False
    assert set(payload["summary"]["external_required_not_ready"]) == {
        "terminal_bench",
        "swe_bench_verified_or_lite",
        "aider_polyglot",
    }
    assert "external_setup_evidence" in payload["summary"]
    assert "public superiority claim" in payload["summary"]["publishable_claim"].lower()
    assert Path(report["json"]).exists()
    assert Path(report["markdown"]).exists()


def test_public_agentic_cli_suite_execute_smoke(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(CONFIG_PATH, tmp_path, execute=True, timeout=120)
    payload = report["payload"]
    by_id = {row["track_id"]: row for row in payload["results"]}

    assert payload["ok"] is True
    assert by_id["geoseal_cli_competitive"]["command"]["returncode"] == 0
    assert by_id["geoseal_cli_competitive"]["score"]["score"] == 1.0
    assert by_id["terminal_bench"]["command"]["returncode"] == 0
    assert by_id["terminal_bench"]["public_claim_ready"] is False


def test_public_agentic_cli_suite_cli_validate_only() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/public_agentic_cli_suite.py", "--validate-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
