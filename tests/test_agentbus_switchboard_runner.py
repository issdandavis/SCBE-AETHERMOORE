from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "system" / "agentbus_switchboard_runner.py"
WORKFLOW = ROOT / "config" / "system" / "agent_bus_switchboard_free_v1.json"


def test_switchboard_dry_run_writes_receipts(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--workflow",
            str(WORKFLOW),
            "--output-root",
            str(tmp_path),
            "--run-id",
            "pytest-switchboard-dry",
            "--max-steps",
            "3",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "pytest-switchboard-dry" / "report.json").read_text(encoding="utf-8"))
    assert report["overall_status"] == "dry_run"
    assert report["steps_executed"] == 3
    assert report["rows"][0]["step_id"] == "deployment_check"
    assert Path(report["rows"][0]["receipt"]).exists()


def test_switchboard_limited_real_run_uses_free_policy(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--workflow",
            str(WORKFLOW),
            "--output-root",
            str(tmp_path),
            "--run-id",
            "pytest-switchboard-real",
            "--start",
            "scope_route",
            "--max-steps",
            "1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=90,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "pytest-switchboard-real" / "report.json").read_text(encoding="utf-8"))
    assert report["overall_status"] == "partial_pass"
    assert report["policy"]["dispatch_provider"] == "offline"
    assert report["policy"]["budget_cents"] == 0
    assert report["rows"][0]["step_id"] == "scope_route"
    receipt = json.loads(Path(report["rows"][0]["receipt"]).read_text(encoding="utf-8"))
    assert receipt["ok"] is True
    parsed = receipt["parsed_stdout"]
    assert parsed["dispatch"]["provider"] == "offline"
