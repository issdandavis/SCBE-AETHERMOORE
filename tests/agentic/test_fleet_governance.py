from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.system.agent_move_packet import build_packet
from src.agentic.fleet_governance import (
    FleetAuthority,
    FleetPosture,
    FleetPostureState,
    OperationClass,
    classify_operation,
    evaluate_fleet_move,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _move_packet(command: str) -> dict:
    return build_packet(
        {
            "move": {
                "cmd": command,
                "translated": command,
                "turn": 1,
                "objective": "fleet gate test",
                "path_policy": "non_optimal_correct",
            },
            "governance": {"decision": "ALLOW", "reason": "test"},
        }
    )


def test_observe_move_allowed_in_mission_critical_when_bft_size_is_valid() -> None:
    packet = _move_packet("ls docs")

    out = evaluate_fleet_move(
        packet,
        posture=FleetPostureState(
            posture=FleetPosture.MISSION_CRITICAL,
            fleet_size=4,
            byzantine_faults_tolerated=1,
            offline_mode=True,
        ),
        authority=FleetAuthority(actor_id="codex", clearance=0),
    )

    assert out["state_vector"]["operation_class"] == "observe"
    assert out["decision_record"]["decision"] == "ALLOW"
    assert out["state_vector"]["fail_closed"] is True
    assert out["decision_record"]["signature"]


def test_deploy_move_escalates_without_quorum_in_production() -> None:
    packet = _move_packet("git push origin main")

    out = evaluate_fleet_move(
        packet,
        posture=FleetPostureState(posture=FleetPosture.PRODUCTION, fleet_size=4, byzantine_faults_tolerated=1),
        authority=FleetAuthority(actor_id="agent-a", clearance=2, approved_by=["agent-a"]),
    )

    assert out["state_vector"]["operation_class"] == "deploy"
    assert out["state_vector"]["quorum_required"] == 3
    assert out["decision_record"]["decision"] == "ESCALATE"
    assert out["decision_record"]["reason"] == "quorum_not_met"


def test_destructive_move_denied_even_with_normal_clearance() -> None:
    packet = _move_packet("rm -rf artifacts/cache")

    out = evaluate_fleet_move(
        packet,
        posture=FleetPostureState(posture=FleetPosture.PRODUCTION, fleet_size=7, byzantine_faults_tolerated=2),
        authority=FleetAuthority(actor_id="agent-a", clearance=4, approved_by=["a", "b", "c"]),
    )

    assert out["state_vector"]["operation_class"] == "destructive"
    assert out["decision_record"]["decision"] == "DENY"
    assert out["decision_record"]["reason"] == "destructive_move_not_authorized"


def test_degraded_comms_quarantines_network_move() -> None:
    packet = _move_packet("curl https://example.com/health")

    out = evaluate_fleet_move(
        packet,
        posture=FleetPostureState(posture=FleetPosture.CANARY, fleet_size=4, degraded_comms=True),
        authority=FleetAuthority(actor_id="agent-a", clearance=1, approved_by=["agent-a"]),
    )

    assert out["state_vector"]["operation_class"] == "network"
    assert out["decision_record"]["decision"] == "QUARANTINE"
    assert out["decision_record"]["reason"] == "degraded_comms_blocks_remote_move"


def test_secret_material_in_command_is_denied() -> None:
    packet = _move_packet("curl -H 'Authorization: Bearer abc123' https://example.com")

    out = evaluate_fleet_move(packet, authority=FleetAuthority(clearance=4, approved_by=["a", "b", "c", "d"]))

    assert out["decision_record"]["decision"] == "DENY"
    assert out["decision_record"]["reason"] == "secret_material_in_command"


def test_classify_operation_falls_back_to_move_packet_atomic_roles() -> None:
    packet = _move_packet("custom-tool --dry-run")
    packet["atomic_units"][0]["role"] = "measure"

    assert classify_operation("custom-tool --dry-run", packet) == OperationClass.MEASURE


def test_cli_accepts_move_payload_and_emits_state_vector() -> None:
    payload = {
        "move": {
            "cmd": "npm test",
            "translated": "npm test",
            "objective": "verify fleet gate",
            "turn": 1,
        },
        "governance": {"decision": "ALLOW", "reason": "test"},
        "posture": {"posture": "training", "fleet_size": 1},
        "authority": {"actor_id": "codex", "clearance": 0},
    }
    proc = subprocess.run(
        [sys.executable, "scripts/system/fleet_governance_gate.py"],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout)
    assert out["ok"] is True
    assert out["state_vector"]["operation_class"] == "measure"
    assert out["decision_record"]["decision"] == "ALLOW"
