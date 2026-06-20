"""CLI wrapper for SCBE fleet governance over an agent move packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.agent_move_packet import build_packet
from src.agentic.fleet_governance import authority_from_dict, evaluate_fleet_move, posture_from_dict


def _read_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("expected JSON on stdin")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def main() -> int:
    try:
        payload = _read_json()
        move_packet = payload.get("move_packet")
        if not isinstance(move_packet, dict):
            move_packet = build_packet(payload) if "move" in payload else None
        if not isinstance(move_packet, dict):
            raise ValueError("expected move_packet or move payload")
        out = evaluate_fleet_move(
            move_packet,
            posture=posture_from_dict(payload.get("posture")),
            authority=authority_from_dict(payload.get("authority")),
        )
    except Exception as exc:
        print(json.dumps({"schema_version": "scbe_fleet_governance_gate_v1", "ok": False, "error": str(exc)}))
        return 2
    print(json.dumps({"ok": True, **out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
