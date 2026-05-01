from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_agent_endurance_pack_generates_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "agent-endurance-pack",
            "--round-id",
            "test-round-001",
            "--permission-mode",
            "workspace-write",
            "--output-dir",
            str(out_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_agent_endurance_pack_v1"
    assert payload["round_id"] == "test-round-001"
    assert payload["permission_mode"] == "workspace-write"

    regimen = Path(payload["paths"]["regimen"])
    taskset = Path(payload["paths"]["taskset"])
    run_report = Path(payload["paths"]["run_report"])
    manifest = Path(payload["paths"]["manifest"])
    for path in (regimen, taskset, run_report, manifest):
        assert path.exists(), f"missing generated file: {path}"

    regimen_payload = json.loads(regimen.read_text(encoding="utf-8"))
    taskset_payload = json.loads(taskset.read_text(encoding="utf-8"))
    run_payload = json.loads(run_report.read_text(encoding="utf-8"))
    assert regimen_payload["schema_version"] == "scbe_agent_endurance_regimen_v1"
    assert taskset_payload["schema_version"] == "scbe_agent_endurance_taskset_v1"
    assert run_payload["schema_version"] == "scbe_agent_endurance_run_report_v1"
    assert taskset_payload["regimen_id"] == regimen_payload["regimen_id"]
    assert run_payload["regimen_id"] == regimen_payload["regimen_id"]
    assert run_payload["taskset_id"] == taskset_payload["taskset_id"]
