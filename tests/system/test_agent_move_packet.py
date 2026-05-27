from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_packet(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "scripts/system/agent_move_packet.py"],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def test_agent_move_packet_layers_shell_move_into_atomic_and_bijective_views() -> None:
    out = _run_packet(
        {
            "schema_version": "scbe_agent_move_packet_input_v1",
            "move": {
                "cmd": ":test npm test",
                "translated": "npm test && echo SCBE_TEST_PASS || echo SCBE_TEST_FAIL",
                "turn": 2,
                "objective": "verify the harness",
                "legal_moves": ["cmd", "files", "read", "patch", "test"],
                "path_policy": "non_optimal_correct",
            },
            "governance": {"decision": "ALLOW", "reason": "ok"},
        }
    )

    assert out["ok"] is True
    packet = out["packet"]
    assert packet["schema_version"] == "scbe_agent_move_packet_v1"
    assert packet["round_trip_ok"] is True
    assert packet["bijective_proof"]["ok"] is True
    assert set(packet["bijective_proof"]["tongues"]) == {
        "ko",
        "av",
        "ru",
        "ca",
        "um",
        "dr",
    }
    assert packet["tokens"][:2] == ["npm", "test"]
    assert packet["atomic_units"][0]["role"] == "compute"
    assert packet["atomic_units"][0]["hex"]
    assert packet["boundaries"]["not_claimed"].startswith(
        "not a source-to-source compiler"
    )


def test_agent_move_packet_rejects_missing_move() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/system/agent_move_packet.py"],
        cwd=REPO_ROOT,
        input=json.dumps({"schema_version": "bad"}),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert proc.returncode == 2
    out = json.loads(proc.stdout)
    assert out["ok"] is False
    assert "payload.move" in out["error"]
