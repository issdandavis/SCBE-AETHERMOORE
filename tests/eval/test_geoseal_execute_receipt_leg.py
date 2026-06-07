from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.eval.geoseal_execute_receipt_leg import (
    build_execute_receipt,
    extract_command,
    extract_policy_decision,
    main,
)


def test_extract_command_accepts_common_plan_shapes() -> None:
    plan = {"operation_panel": {"argv": ["python", "-c", "print('ok')"]}}

    assert extract_command(plan) == '"python" "-c" "print(\'ok\')"'


def test_execute_receipt_runs_allowed_plan_and_hashes_outputs(tmp_path: Path) -> None:
    command = f"{sys.executable} -c \"print('geo-ok')\""
    receipt = build_execute_receipt(
        plan={"decision": "ALLOW", "command": command},
        command=command,
        policy_decision="ALLOW",
        max_tier="QUARANTINE",
        cwd=tmp_path,
        timeout=5,
    )

    assert receipt["ok"] is True
    assert receipt["executed"] is True
    assert receipt["receipt"] == "SCBE_GEOSEAL_EXECUTE=1"
    assert receipt["gate_tier"] == "QUARANTINE"
    assert "geo-ok" in receipt["stdout_preview"]
    assert receipt["stdout_sha256"]
    assert receipt["command_sha256"]


def test_execute_receipt_fails_closed_when_plan_is_not_allow(tmp_path: Path) -> None:
    command = f"{sys.executable} -c \"print('should-not-run')\""
    receipt = build_execute_receipt(
        plan={"decision": "REVIEW", "command": command},
        command=command,
        policy_decision="REVIEW",
        max_tier="QUARANTINE",
        cwd=tmp_path,
        timeout=5,
    )

    assert receipt["ok"] is False
    assert receipt["executed"] is False
    assert receipt["receipt"] == "SCBE_GEOSEAL_EXECUTE=0"
    assert "not ALLOW" in receipt["reason"]


def test_execute_receipt_blocks_shell_metacharacters(tmp_path: Path) -> None:
    command = (
        f"{sys.executable} -c \"print('a')\" && {sys.executable} -c \"print('b')\""
    )
    receipt = build_execute_receipt(
        plan={"decision": "ALLOW", "command": command},
        command=command,
        policy_decision="ALLOW",
        max_tier="QUARANTINE",
        cwd=tmp_path,
        timeout=5,
    )

    assert receipt["ok"] is False
    assert receipt["executed"] is False
    assert receipt["gate_tier"] == "DENY"
    assert receipt["gate"]["allowed"] is False


def test_cli_writes_receipt_file_from_plan(tmp_path: Path, capsys) -> None:
    plan_path = tmp_path / "plan.json"
    out_path = tmp_path / "receipt.json"
    command = f"{sys.executable} -c \"print('cli-ok')\""
    plan_path.write_text(
        json.dumps({"policy": {"decision": "ALLOW"}, "command": command}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--max-tier",
            "QUARANTINE",
            "--cwd",
            str(tmp_path),
            "--out",
            str(out_path),
        ]
    )
    stdout_payload = json.loads(capsys.readouterr().out)
    written_payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_payload["ok"] is True
    assert written_payload["receipt"] == "SCBE_GEOSEAL_EXECUTE=1"
    assert "cli-ok" in written_payload["stdout_preview"]


def test_policy_decision_defaults_to_allow_for_bare_prototype_plan() -> None:
    assert extract_policy_decision({}) == "ALLOW"
