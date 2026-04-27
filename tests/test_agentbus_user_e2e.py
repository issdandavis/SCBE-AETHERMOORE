from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"
PIPE = ROOT / "scripts" / "system" / "agentbus_pipe.mjs"


def test_user_cli_agentbus_run_shapes_dispatch_tracks_and_watches() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(ROOT),
            "agentbus",
            "run",
            "--task",
            "Black-box user asks for a shaped coding review.",
            "--operation-command",
            "korah aelin dahru",
            "--task-type",
            "coding",
            "--series-id",
            "pytest-agentbus-user-e2e",
            "--privacy",
            "local_only",
            "--budget-cents",
            "0",
            "--dispatch",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_agentbus_user_run_v1"
    assert payload["selected_provider"] in {"offline", "ollama"}
    assert payload["operation_shape"]["root_value"] == 12026
    assert payload["dispatch"]["enabled"] is True
    assert payload["dispatch"]["provider"] == "offline"
    assert payload["dispatch"]["event_id"]
    assert payload["rehearsal_gate"]["status"] == "pass"
    assert payload["geoseal_agentbus"]["route_tongue"] == "ca"
    assert payload["geoseal_agentbus"]["dual_tokenizer_roundtrip_ok"] is True
    assert payload["geoseal_agentbus"]["verify_ok"] is True
    assert (ROOT / payload["artifacts"]["latest_round"]).exists()
    assert (ROOT / payload["artifacts"]["watcher"]).exists()
    assert (ROOT / payload["artifacts"]["summary"]).exists()
    assert (ROOT / payload["artifacts"]["rehearsal_gate"]).exists()
    assert (ROOT / payload["artifacts"]["geoseal_agentbus_envelope"]).exists()
    assert (ROOT / payload["artifacts"]["geoseal_agentbus_ledger"]).exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_node_agentbus_pipe_processes_workflow_event() -> None:
    event = {
        "task": "Pipe event routes a shaped coding task through the bus.",
        "operation_command": "korah aelin dahru",
        "task_type": "coding",
        "series_id": "pytest-agentbus-pipe-e2e",
        "privacy": "local_only",
        "budget_cents": 0,
        "dispatch": True,
    }

    result = subprocess.run(
        ["node", str(PIPE), "--repo-root", str(ROOT)],
        input=json.dumps(event),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == "scbe-agentbus-pipe-result-v1"
    assert row["ok"] is True
    assert row["event"]["series_id"] == "pytest-agentbus-pipe-e2e"
    assert (
        row["result"]["operation_shape"]["signature_hex"]
        == "c176ca9a2f3473c6d643c1ef8b000c7a"
    )
    assert row["result"]["geoseal_agentbus"]["route_tongue"] == "ca"
    assert row["result"]["geoseal_agentbus"]["verify_ok"] is True
    assert row["result"]["artifacts"]["watcher"].endswith("observable_state.json")
