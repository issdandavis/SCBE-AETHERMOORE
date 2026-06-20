"""Deterministic SCBE governance scan primitives.

This module is intentionally small: SDK callers and REST endpoints can use it
without launching the full agent-bus runner. The output is a stable receipt that
can be stored now and rendered into compliance reports later.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

PHI = (1 + math.sqrt(5)) / 2

Decision = Literal["ALLOW", "QUARANTINE", "DENY"]


class GovernanceScan(TypedDict):
    schema_version: Literal["scbe-governance-scan-v1"]
    decision: Decision
    tier: Decision
    score: float
    d_H: float
    pattern_drift: float
    role: str
    action: str
    target: str
    command: str
    policy_version: str
    receipt_hash: str
    scanned_at: str
    explanation: dict[str, Any]


_ROLE_REACTIVITY: dict[str, float] = {
    "observe": 0.20,
    "measure": 0.25,
    "report": 0.20,
    "hold": 0.05,
    "compute": 0.65,
    "move": 0.70,
    "repair": 0.45,
    "transmit": 0.80,
}

_COMMAND_ROLES: dict[str, str] = {
    "cat": "observe",
    "head": "observe",
    "tail": "observe",
    "ls": "observe",
    "pwd": "observe",
    "whoami": "observe",
    "wc": "measure",
    "ps": "measure",
    "du": "measure",
    "df": "measure",
    "echo": "report",
    "printf": "report",
    "sleep": "hold",
    "python": "compute",
    "python3": "compute",
    "node": "compute",
    "npm": "compute",
    "pytest": "compute",
    "git": "repair",
    "pip": "repair",
    "mkdir": "move",
    "cp": "move",
    "mv": "move",
    "rm": "move",
    "chmod": "move",
    "curl": "transmit",
    "wget": "transmit",
    "ssh": "transmit",
    "scp": "transmit",
    "nc": "transmit",
}

_HARD_DANGER: list[tuple[str, float, float, str]] = [
    (r":\(\)\{.*:\|:&", 0.99, 0.95, "fork_bomb"),
    (r">/dev/(sda|hda|nvme)", 0.98, 0.92, "disk_wipe"),
    (r"\brm\s+-rf\s+/[^/]", 0.95, 0.88, "root_delete"),
    (r"nc\s+-e\s+/bin", 0.95, 0.88, "reverse_shell"),
    (r"curl.*\|\s*(ba)?sh", 0.90, 0.85, "remote_pipe_shell"),
    (r"wget.*\|\s*(ba)?sh", 0.90, 0.85, "remote_pipe_shell"),
    (r"base64.*decode.*\|.*sh", 0.85, 0.80, "encoded_shell"),
    (r"(dd|mkfs)\b.*\bif=", 0.85, 0.78, "raw_disk_operation"),
]

_SOFT_DANGER: list[tuple[str, float, str]] = [
    (r"\brm\s+-rf\b", 0.55, "recursive_delete"),
    (r"chmod\s+[+]?s\b", 0.80, "setuid_change"),
]

_ERROR_RE = re.compile(
    r"\b(error|errno|fail(ed)?|fatal|traceback|exception|denied|not found|no such file)\b",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _first_token(command: str) -> str:
    text = command.strip()
    if not text:
        return ""
    return text.split()[0].replace("\\", "/").rsplit("/", 1)[-1].lower()


def _role_for_command(command: str) -> str:
    return _COMMAND_ROLES.get(_first_token(command), "compute")


def _output_deviation(observed: str) -> float:
    if not observed:
        return 0.0
    lines = [line for line in observed.splitlines() if line.strip()]
    if not lines:
        return 0.0
    tail = "\n".join(lines[-8:])
    error_density = min(len(_ERROR_RE.findall(tail)) / 5, 1.0)
    volume_signal = min(len(observed) / 8000, 0.5)
    return min(error_density * 0.75 + volume_signal * 0.25, 1.0)


def harmonic_score(d_h: float, pattern_drift: float) -> float:
    """SCBE L12 score: H(d,pd)=1/(1+phi*d+2*pd)."""
    return 1.0 / (1.0 + PHI * d_h + 2.0 * pattern_drift)


def risk_tier(score: float) -> Decision:
    if score >= 0.60:
        return "ALLOW"
    if score >= 0.30:
        return "QUARANTINE"
    return "DENY"


def scan_command(
    command: str,
    *,
    action: str = "EXECUTE",
    target: str = "",
    observed: str = "",
    context: dict[str, Any] | None = None,
    policy_version: str = "scbe-governance-sdk-v1",
) -> GovernanceScan:
    """Scan one proposed agent command and return a receipt-ready decision."""
    command = str(command or "").strip()
    action = str(action or "EXECUTE").strip().upper()
    target = str(target or "").strip()
    ctx = dict(context or {})
    lowered = command.lower()

    role = _role_for_command(command)
    d_h = _ROLE_REACTIVITY.get(role, _ROLE_REACTIVITY["compute"])
    pattern_drift = _output_deviation(observed)
    reason_codes: list[str] = [f"ROLE_{role.upper()}"]

    for pattern, hard_d_h, hard_pd, reason in _HARD_DANGER:
        if re.search(pattern, lowered):
            d_h = max(d_h, hard_d_h)
            pattern_drift = max(pattern_drift, hard_pd)
            reason_codes.append(f"HARD_{reason.upper()}")
            break
    else:
        for pattern, soft_d_h, reason in _SOFT_DANGER:
            if re.search(pattern, lowered):
                d_h = max(d_h, soft_d_h)
                reason_codes.append(f"SOFT_{reason.upper()}")
                break

    score = round(harmonic_score(d_h, pattern_drift), 6)
    tier = risk_tier(score)
    scanned_at = _now_iso()
    receipt_material = {
        "schema_version": "scbe-governance-scan-v1",
        "action": action,
        "target": target,
        "command": command,
        "context": ctx,
        "policy_version": policy_version,
        "score": score,
        "tier": tier,
        "d_H": round(d_h, 6),
        "pattern_drift": round(pattern_drift, 6),
    }
    receipt_hash = _hash(receipt_material)
    return GovernanceScan(
        schema_version="scbe-governance-scan-v1",
        decision=tier,
        tier=tier,
        score=score,
        d_H=round(d_h, 6),
        pattern_drift=round(pattern_drift, 6),
        role=role,
        action=action,
        target=target,
        command=command,
        policy_version=policy_version,
        receipt_hash=receipt_hash,
        scanned_at=scanned_at,
        explanation={
            "formula": "1/(1+phi*d_H+2*pattern_drift)",
            "reason_codes": reason_codes + [f"DECISION_{tier}"],
            "context_sha256": _hash(ctx),
        },
    )


def scan_agent_request(
    *,
    action: str,
    target: str = "",
    command: str = "",
    observed: str = "",
    context: dict[str, Any] | None = None,
    policy_version: str = "scbe-governance-sdk-v1",
) -> GovernanceScan:
    """Scan a framework-agnostic agent action.

    If no explicit command is provided, the action and target are joined so
    LangChain/CrewAI/AutoGen/n8n callers can still get a tier decision.
    """
    material = command or " ".join(part for part in [action, target] if part).strip()
    return scan_command(
        material,
        action=action,
        target=target,
        observed=observed,
        context=context,
        policy_version=policy_version,
    )
