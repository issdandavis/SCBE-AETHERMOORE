"""Fleet-grade governance gate for SCBE agent moves.

This module sits after the agent move packet. It does not trust the model's
claim that a command is safe; it classifies the move, checks fleet posture,
requires quorum where appropriate, and emits a deterministic StateVector plus
DecisionRecord.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

SCHEMA_VERSION = "scbe_fleet_governance_gate_v1"


class FleetDecision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


class FleetPosture(str, Enum):
    TRAINING = "training"
    CANARY = "canary"
    PRODUCTION = "production"
    MISSION_CRITICAL = "mission_critical"


class OperationClass(str, Enum):
    OBSERVE = "observe"
    MEASURE = "measure"
    MODIFY = "modify"
    DEPLOY = "deploy"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class FleetAuthority:
    actor_id: str = "unknown"
    clearance: int = 0
    approved_by: list[str] = field(default_factory=list)
    human_confirmed: bool = False
    emergency_rollback: bool = False


@dataclass(frozen=True)
class FleetPostureState:
    posture: FleetPosture = FleetPosture.TRAINING
    fleet_size: int = 1
    byzantine_faults_tolerated: int = 0
    degraded_comms: bool = False
    offline_mode: bool = True


@dataclass(frozen=True)
class StateVector:
    schema_version: str
    operation_class: str
    posture: str
    clearance: int
    required_clearance: int
    quorum_observed: int
    quorum_required: int
    bft_min_nodes: int
    fleet_size: int
    degraded_comms: bool
    fail_closed: bool
    move_id: str
    command_hash: str


@dataclass(frozen=True)
class DecisionRecord:
    decision: str
    reason: str
    timestamp: float
    signature: str
    confidence: float
    findings: list[str] = field(default_factory=list)


_DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bRemove-Item\b.*\b-Recurse\b.*\b-Force\b",
    r"\bdel\s+/[sq]\b",
    r"\bformat\b",
    r"\bdrop\s+database\b",
    r"\bkubectl\s+delete\b",
]

_DEPLOY_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgh\s+pr\s+merge\b",
    r"\bnpm\s+publish\b",
    r"\btwine\s+upload\b",
    r"\bvercel\s+--prod\b",
    r"\bkubectl\s+(apply|rollout|set)\b",
]

_NETWORK_PATTERNS = [
    r"\bcurl\b",
    r"\bwget\b",
    r"\bInvoke-WebRequest\b",
    r"\bgh\s+api\b",
    r"\bssh\b",
    r"\bscp\b",
]

_MODIFY_PATTERNS = [
    r"\bpatch\b",
    r"\bapply_patch\b",
    r"\bgit\s+(commit|add)\b",
    r"\bpython\b.*\b(write|format|black)\b",
    r"\bnpx\s+prettier\s+--write\b",
]

_MEASURE_PATTERNS = [
    r"\btest\b",
    r"\bpytest\b",
    r"\bnpm\s+(test|run\s+test|run\s+lint|run\s+typecheck)\b",
    r"\bnode\s+--check\b",
    r"\bgh\s+pr\s+checks\b",
]

_SECRET_PATTERNS = [
    r"(?i)(api[_-]?key|secret|password|token|bearer)\s*=",
    r"(?i)authorization:\s*bearer",
]

_CLEARANCE_BY_OPERATION = {
    OperationClass.OBSERVE: 0,
    OperationClass.MEASURE: 0,
    OperationClass.MODIFY: 1,
    OperationClass.NETWORK: 1,
    OperationClass.DEPLOY: 2,
    OperationClass.DESTRUCTIVE: 4,
}

_POSTURE_QUORUM = {
    FleetPosture.TRAINING: {
        OperationClass.OBSERVE: 0,
        OperationClass.MEASURE: 0,
        OperationClass.MODIFY: 0,
        OperationClass.NETWORK: 1,
        OperationClass.DEPLOY: 2,
        OperationClass.DESTRUCTIVE: 999,
    },
    FleetPosture.CANARY: {
        OperationClass.OBSERVE: 0,
        OperationClass.MEASURE: 0,
        OperationClass.MODIFY: 1,
        OperationClass.NETWORK: 1,
        OperationClass.DEPLOY: 2,
        OperationClass.DESTRUCTIVE: 999,
    },
    FleetPosture.PRODUCTION: {
        OperationClass.OBSERVE: 0,
        OperationClass.MEASURE: 0,
        OperationClass.MODIFY: 2,
        OperationClass.NETWORK: 2,
        OperationClass.DEPLOY: 3,
        OperationClass.DESTRUCTIVE: 999,
    },
    FleetPosture.MISSION_CRITICAL: {
        OperationClass.OBSERVE: 0,
        OperationClass.MEASURE: 1,
        OperationClass.MODIFY: 3,
        OperationClass.NETWORK: 3,
        OperationClass.DEPLOY: 4,
        OperationClass.DESTRUCTIVE: 999,
    },
}


def classify_operation(command: str, move_packet: dict[str, Any] | None = None) -> OperationClass:
    """Classify a shell move into a fleet governance operation class."""
    normalized = command.strip()
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _DESTRUCTIVE_PATTERNS):
        return OperationClass.DESTRUCTIVE
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _DEPLOY_PATTERNS):
        return OperationClass.DEPLOY
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _NETWORK_PATTERNS):
        return OperationClass.NETWORK
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _MODIFY_PATTERNS):
        return OperationClass.MODIFY
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _MEASURE_PATTERNS):
        return OperationClass.MEASURE

    roles = {
        str(unit.get("role", "")).lower()
        for unit in (move_packet or {}).get("atomic_units", [])
        if isinstance(unit, dict)
    }
    if "repair" in roles:
        return OperationClass.MODIFY
    if "transmit" in roles:
        return OperationClass.NETWORK
    if "measure" in roles:
        return OperationClass.MEASURE
    return OperationClass.OBSERVE


def _unique_quorum(approved_by: list[str]) -> int:
    return len({actor.strip().lower() for actor in approved_by if actor.strip()})


def _bft_min_nodes(faults: int) -> int:
    return max(1, (3 * max(0, int(faults))) + 1)


def _command_from_move(move_packet: dict[str, Any]) -> str:
    move = move_packet.get("move") if isinstance(move_packet, dict) else None
    if isinstance(move, dict):
        return str(move.get("translated") or move.get("cmd") or "")
    return ""


def _stable_signature(state: StateVector, decision: str, reason: str, findings: list[str]) -> str:
    payload = {
        "state": asdict(state),
        "decision": decision,
        "reason": reason,
        "findings": findings,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def evaluate_fleet_move(
    move_packet: dict[str, Any],
    *,
    posture: FleetPostureState | None = None,
    authority: FleetAuthority | None = None,
) -> dict[str, Any]:
    """Evaluate one agent move under fleet-grade command authority rules."""
    posture = posture or FleetPostureState()
    authority = authority or FleetAuthority()
    command = _command_from_move(move_packet)
    op_class = classify_operation(command, move_packet)
    required_clearance = _CLEARANCE_BY_OPERATION[op_class]
    quorum_required = _POSTURE_QUORUM[posture.posture][op_class]
    quorum_observed = _unique_quorum(authority.approved_by)
    bft_min_nodes = _bft_min_nodes(posture.byzantine_faults_tolerated)
    command_hash = hashlib.sha256(command.encode("utf-8")).hexdigest()
    move_id = str(move_packet.get("move_id") or command_hash[:16])

    findings: list[str] = []
    decision = FleetDecision.ALLOW
    reason = "fleet_gate_clear"

    if not command:
        decision = FleetDecision.DENY
        reason = "missing_command"
        findings.append("move packet did not contain a translated command")
    if not move_packet.get("round_trip_ok", False):
        decision = FleetDecision.DENY
        reason = "move_packet_not_bijective"
        findings.append("move packet failed Sacred Tongue transport round trip")
    if any(re.search(pattern, command, re.IGNORECASE) for pattern in _SECRET_PATTERNS):
        decision = FleetDecision.DENY
        reason = "secret_material_in_command"
        findings.append("command appears to carry secret material")
    if posture.fleet_size < bft_min_nodes:
        decision = FleetDecision.ESCALATE if decision == FleetDecision.ALLOW else decision
        reason = "insufficient_bft_fleet_size" if decision == FleetDecision.ESCALATE else reason
        findings.append(f"fleet_size={posture.fleet_size} below bft_min_nodes={bft_min_nodes}")
    if authority.clearance < required_clearance:
        decision = FleetDecision.ESCALATE if decision == FleetDecision.ALLOW else decision
        reason = "insufficient_clearance" if decision == FleetDecision.ESCALATE else reason
        findings.append(f"clearance={authority.clearance} below required={required_clearance}")
    if quorum_required >= 999:
        if not (authority.emergency_rollback and authority.human_confirmed and quorum_observed >= 4):
            decision = FleetDecision.DENY
            reason = "destructive_move_not_authorized"
            findings.append("destructive commands require emergency rollback, human confirmation, and 4 approvals")
    elif quorum_observed < quorum_required:
        decision = FleetDecision.ESCALATE if decision == FleetDecision.ALLOW else decision
        reason = "quorum_not_met" if decision == FleetDecision.ESCALATE else reason
        findings.append(f"quorum={quorum_observed} below required={quorum_required}")
    if posture.degraded_comms and op_class in {OperationClass.DEPLOY, OperationClass.NETWORK}:
        decision = FleetDecision.QUARANTINE if decision == FleetDecision.ALLOW else decision
        reason = "degraded_comms_blocks_remote_move" if decision == FleetDecision.QUARANTINE else reason
        findings.append("degraded comms forbids remote/network/deploy moves")

    state = StateVector(
        schema_version=SCHEMA_VERSION,
        operation_class=op_class.value,
        posture=posture.posture.value,
        clearance=authority.clearance,
        required_clearance=required_clearance,
        quorum_observed=quorum_observed,
        quorum_required=quorum_required,
        bft_min_nodes=bft_min_nodes,
        fleet_size=posture.fleet_size,
        degraded_comms=posture.degraded_comms,
        fail_closed=True,
        move_id=move_id,
        command_hash=command_hash,
    )
    signature = _stable_signature(state, decision.value, reason, findings)
    confidence = 0.98 if decision == FleetDecision.ALLOW else 0.93
    if findings:
        confidence = max(0.70, confidence - (0.03 * math.log1p(len(findings))))
    record = DecisionRecord(
        decision=decision.value,
        reason=reason,
        timestamp=time.time(),
        signature=signature,
        confidence=round(confidence, 4),
        findings=findings,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "state_vector": asdict(state),
        "decision_record": asdict(record),
    }


def posture_from_dict(data: dict[str, Any] | None) -> FleetPostureState:
    data = data or {}
    return FleetPostureState(
        posture=FleetPosture(str(data.get("posture", FleetPosture.TRAINING.value))),
        fleet_size=int(data.get("fleet_size", 1)),
        byzantine_faults_tolerated=int(data.get("byzantine_faults_tolerated", 0)),
        degraded_comms=bool(data.get("degraded_comms", False)),
        offline_mode=bool(data.get("offline_mode", True)),
    )


def authority_from_dict(data: dict[str, Any] | None) -> FleetAuthority:
    data = data or {}
    return FleetAuthority(
        actor_id=str(data.get("actor_id", "unknown")),
        clearance=int(data.get("clearance", 0)),
        approved_by=[str(actor) for actor in data.get("approved_by", [])],
        human_confirmed=bool(data.get("human_confirmed", False)),
        emergency_rollback=bool(data.get("emergency_rollback", False)),
    )


__all__ = [
    "FleetAuthority",
    "FleetDecision",
    "FleetPosture",
    "FleetPostureState",
    "OperationClass",
    "classify_operation",
    "evaluate_fleet_move",
    "posture_from_dict",
    "authority_from_dict",
]
