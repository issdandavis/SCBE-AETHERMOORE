"""Build a compact SCBE move packet for agent shell commands.

This is a bridge layer, not a universal code translator. It preserves the
move across synchronized views: shell command, token roles, byte/hex structure,
atomic workflow units, and Sacred Tongue transport bijection.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crypto.sacred_tongue_payload_bijection import canonical_json_bytes, prove_dict
from src.tokenizer.atomic_workflow_units import build_atomic_workflow_unit

SCHEMA_VERSION = "scbe_agent_move_packet_v1"

ROLE_BY_HEAD = {
    "cat": "observe",
    "dir": "observe",
    "find": "observe",
    "grep": "observe",
    "head": "observe",
    "ls": "observe",
    "rg": "observe",
    "sed": "observe",
    "type": "observe",
    "where": "observe",
    "git": "measure",
    "gh": "transmit",
    "node": "compute",
    "npm": "compute",
    "npx": "compute",
    "python": "compute",
    "python3": "compute",
    "pytest": "measure",
    "vitest": "measure",
    "patch": "repair",
    "black": "repair",
    "eslint": "repair",
    "prettier": "repair",
    "ruff": "repair",
}


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("expected JSON on stdin")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def _tokens(command: str) -> list[str]:
    try:
        parts = shlex.split(command, posix=True)
    except ValueError:
        parts = command.split()
    return [part for part in parts if part][:32]


def _role_for(index: int, token: str, head_role: str) -> str:
    if index == 0:
        return head_role
    lowered = token.lower()
    if lowered in {"&&", "||", "|", ";"}:
        return "gate"
    if lowered.startswith("-"):
        return "gate"
    if any(marker in lowered for marker in ("test", "check", "verify", "status")):
        return "measure"
    if any(marker in lowered for marker in ("fix", "patch", "format", "lint")):
        return "repair"
    return "compute"


def _compact_unit(unit: dict[str, Any]) -> dict[str, Any]:
    byte_sig = unit["chemistry_lane"]["byte_signature"]
    return {
        "unit_id": unit["unit_id"],
        "token": unit["token"],
        "role": unit["semantic_lane"]["role"],
        "phase": unit["semantic_lane"]["phase"],
        "stability": unit["semantic_lane"]["stability"],
        "chemistry_mode": unit["chemistry_lane"]["mode"],
        "byte_count": byte_sig["byte_count"],
        "hex": byte_sig["hex"],
        "byte_sha256": byte_sig["byte_sha256"],
        "resource_cost": unit["resource_cost"],
    }


def build_packet(input_payload: dict[str, Any]) -> dict[str, Any]:
    move = input_payload.get("move")
    if not isinstance(move, dict):
        raise ValueError("payload.move must be an object")

    command = str(move.get("cmd") or "").strip()
    translated = str(move.get("translated") or command).strip()
    if not translated:
        raise ValueError("payload.move.translated or payload.move.cmd is required")

    tokens = _tokens(translated)
    head = Path(tokens[0]).name.lower() if tokens else ""
    head_role = ROLE_BY_HEAD.get(head, "compute")
    atomic_units = [
        _compact_unit(build_atomic_workflow_unit(token, explicit_role=_role_for(index, token, head_role)))
        for index, token in enumerate(tokens)
    ]

    packet_base = {
        "schema_version": SCHEMA_VERSION,
        "move": {
            "cmd": command,
            "translated": translated,
            "turn": move.get("turn"),
            "path_policy": move.get("path_policy", "non_optimal_correct"),
            "objective_sha256": hashlib.sha256(str(move.get("objective") or "").encode("utf-8")).hexdigest(),
        },
        "governance": input_payload.get("governance") or {},
        "tokens": tokens,
        "atomic_units": atomic_units,
        "boundaries": {
            "semantic": "agent move intent and workflow roles",
            "transport": "canonical JSON bytes encoded losslessly through all Sacred Tongues",
            "not_claimed": "not a source-to-source compiler and not a proof of language equivalence",
        },
    }
    digest = hashlib.sha256(canonical_json_bytes(packet_base)).hexdigest()
    proof = prove_dict(packet_base)
    return {
        **packet_base,
        "move_id": digest[:16],
        "canonical_sha256": digest,
        "bijective_proof": proof,
        "round_trip_ok": bool(proof["ok"]),
    }


def main() -> int:
    try:
        packet = build_packet(_read_stdin_json())
    except Exception as exc:  # pragma: no cover - exercised via CLI failure path.
        print(json.dumps({"schema_version": SCHEMA_VERSION, "ok": False, "error": str(exc)}))
        return 2
    print(
        json.dumps(
            {"schema_version": SCHEMA_VERSION, "ok": True, "packet": packet},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
