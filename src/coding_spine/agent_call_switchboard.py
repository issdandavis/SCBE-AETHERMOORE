"""Governed call switchboard for multiple AI agents.

The switchboard is a small coordination primitive: before an agent starts a
"call" with a tool, file lane, model lane, or human-facing surface, it asks for
a reservation. The switchboard prevents obvious collisions like two agents
writing the same resource or one applying while another is still verifying.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "scbe_agent_call_switchboard_v1"

EXCLUSIVE_MODES = {"write", "apply", "cloud_dispatch", "human_send"}
ACTIVE_STATES = {"reserved", "active"}


@dataclass(frozen=True)
class AgentCall:
    call_id: str
    agent_id: str
    lane: str
    resource: str
    mode: str = "read"
    state: str = "reserved"
    priority: int = 5
    created_at: str = ""
    expires_at: str = ""
    summary: str = ""

    def normalized(self) -> "AgentCall":
        return AgentCall(
            call_id=str(self.call_id).strip(),
            agent_id=str(self.agent_id).strip() or "agent.unknown",
            lane=_norm(self.lane, "general"),
            resource=_norm(self.resource, "workspace"),
            mode=_norm(self.mode, "read"),
            state=_norm(self.state, "reserved"),
            priority=int(self.priority),
            created_at=str(self.created_at).strip(),
            expires_at=str(self.expires_at).strip(),
            summary=str(self.summary).strip(),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(value: str, fallback: str) -> str:
    cleaned = str(value or "").strip().lower().replace("_", "-")
    return cleaned or fallback


def _call_from_dict(raw: dict[str, Any]) -> AgentCall:
    return AgentCall(
        call_id=str(raw.get("call_id", raw.get("id", ""))),
        agent_id=str(raw.get("agent_id", raw.get("owner", ""))),
        lane=str(raw.get("lane", "")),
        resource=str(raw.get("resource", raw.get("target", ""))),
        mode=str(raw.get("mode", "read")),
        state=str(raw.get("state", "reserved")),
        priority=int(raw.get("priority", 5)),
        created_at=str(raw.get("created_at", "")),
        expires_at=str(raw.get("expires_at", "")),
        summary=str(raw.get("summary", "")),
    ).normalized()


def _same_surface(left: AgentCall, right: AgentCall) -> bool:
    return left.lane == right.lane and left.resource == right.resource


def _compatible(left: AgentCall, right: AgentCall) -> bool:
    if left.agent_id == right.agent_id and left.call_id == right.call_id:
        return True
    if not _same_surface(left, right):
        return True
    if left.mode in EXCLUSIVE_MODES or right.mode in EXCLUSIVE_MODES:
        return False
    return True


def evaluate_call_request(existing: list[dict[str, Any]], request: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a new call against existing reservations."""

    req = _call_from_dict(request)
    active_calls = [
        _call_from_dict(row)
        for row in existing
        if _norm(str(row.get("state", "reserved")), "reserved") in ACTIVE_STATES
    ]
    collisions = [call for call in active_calls if not _compatible(call, req)]
    if collisions:
        highest_priority = min(call.priority for call in collisions)
        decision = "QUEUE" if req.priority <= highest_priority else "BLOCK"
        reason = "exclusive_surface_collision"
    else:
        decision = "GRANT"
        reason = "no_collision"

    return {
        "schema_version": SCHEMA_VERSION,
        "evaluated_at": _utc_now(),
        "decision": decision,
        "ok": decision == "GRANT",
        "reason": reason,
        "request": asdict(req),
        "collisions": [asdict(call) for call in collisions],
        "switchboard_event": {
            "_agent_id": req.agent_id,
            "_sig": f"switchboard-{req.call_id}",
            "id": req.call_id,
            "task_type": "switchboard",
            "query": req.summary or f"{req.mode} {req.lane}:{req.resource}",
            "success": decision == "GRANT",
            "timestamp": _utc_now(),
            "breaker_state": {"call_lane": "closed" if decision == "GRANT" else "review"},
        },
    }


def build_switchboard_snapshot(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a GeoShell-friendly snapshot of current switchboard state."""

    normalized = [_call_from_dict(row) for row in calls]
    active = [call for call in normalized if call.state in ACTIVE_STATES]
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for call in active:
        by_lane.setdefault(call.lane, []).append(asdict(call))
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "active_count": len(active),
        "by_lane": by_lane,
        "calls": [asdict(call) for call in normalized],
    }
