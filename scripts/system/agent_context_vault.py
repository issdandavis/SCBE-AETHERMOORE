#!/usr/bin/env python3
"""Rolling context vault and channel runner for SCBE AI-to-AI work.

The vault gives each agent a small retained state plus an append-only local
trail. Channels are JSONL streams that teams can tail while a task is active.
This is deliberately local-first; a later sync worker can mirror the same files
to cloud storage without changing the packet contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ROOT = REPO_ROOT / "artifacts" / "agent_context_vault"
SCHEMA_VERSION = "scbe_agent_context_vault_v1"
STATE_SCHEMA_VERSION = "scbe_agent_context_state_v1"
CHANNEL_SCHEMA_VERSION = "scbe_agent_channel_event_v1"
SENSITIVE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"nvapi-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"ak-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
)


@dataclass(frozen=True)
class VaultPaths:
    root: Path

    @property
    def agents(self) -> Path:
        return self.root / "agents"

    @property
    def channels(self) -> Path:
        return self.root / "channels"

    @property
    def scoreboards(self) -> Path:
        return self.root / "scoreboards"

    def agent_dir(self, agent_id: str) -> Path:
        return self.agents / _safe_name(agent_id)

    def rolling_path(self, agent_id: str) -> Path:
        return self.agent_dir(agent_id) / "rolling.jsonl"

    def state_path(self, agent_id: str) -> Path:
        return self.agent_dir(agent_id) / "state.json"

    def channel_path(self, channel_id: str) -> Path:
        return self.channels / f"{_safe_name(channel_id)}.jsonl"

    def scoreboard_path(self, task_id: str) -> Path:
        return self.scoreboards / f"{_safe_name(task_id)}.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(value: str, fallback: str = "default") -> str:
    token = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value).strip()).strip("-")
    return token or fallback


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _as_list(values: list[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    return [line.strip() for line in str(values).splitlines() if line.strip()]


def _assert_no_secret_text(*values: str) -> None:
    joined = "\n".join(str(value) for value in values)
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(joined):
            raise ValueError("refusing to write likely secret material into agent context vault")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def init_vault(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    paths = VaultPaths(root)
    for path in (paths.agents, paths.channels, paths.scoreboards):
        path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "root": str(root),
        "storage_policy": {
            "default": "local_first",
            "full_history": "append_only_jsonl",
            "compact_state": "per_agent_state_json",
            "cloud_ready": True,
            "secret_policy": "reject_likely_tokens_and_keys",
        },
        "views": {
            "small": "state.json compact context for immediate handoff",
            "rolling": "last N events from rolling.jsonl",
            "channel": "shared channel JSONL for real-time team coordination",
        },
    }
    _write_json(root / "manifest.json", manifest)
    return manifest


def append_event(
    *,
    root: Path = DEFAULT_ROOT,
    agent_id: str,
    channel_id: str,
    task_id: str,
    summary: str,
    intent: str = "status",
    status: str = "in_progress",
    recipient: str = "",
    proof: list[str] | None = None,
    next_action: str = "",
    risk: str = "low",
    role: str = "worker",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _assert_no_secret_text(agent_id, channel_id, task_id, summary, recipient, next_action, "\n".join(proof or []))
    paths = VaultPaths(root)
    init_vault(root)
    event_core = {
        "schema_version": CHANNEL_SCHEMA_VERSION,
        "created_at": _utc_now(),
        "agent_id": agent_id,
        "role": role,
        "channel_id": channel_id,
        "task_id": task_id,
        "intent": intent,
        "status": status,
        "recipient": recipient,
        "summary": summary.strip(),
        "proof": _as_list(proof),
        "next_action": next_action.strip(),
        "risk": risk,
        "metadata": metadata or {},
        "token_estimate": _estimate_tokens(" ".join([summary, next_action, " ".join(proof or [])])),
    }
    event = {**event_core, "event_id": f"ctx-{_sha256_json(event_core)[:16]}"}
    _append_jsonl(paths.rolling_path(agent_id), event)
    _append_jsonl(paths.channel_path(channel_id), event)
    return event


def digest_agent(
    *,
    root: Path = DEFAULT_ROOT,
    agent_id: str,
    max_items: int = 12,
    max_chars: int = 1600,
) -> dict[str, Any]:
    paths = VaultPaths(root)
    rows = _read_jsonl(paths.rolling_path(agent_id))
    recent = rows[-max(1, max_items) :]
    summaries: list[str] = []
    proof: list[str] = []
    open_actions: list[str] = []
    risks: list[str] = []
    for row in recent:
        summary = str(row.get("summary", "")).strip()
        if summary:
            summaries.append(f"- {row.get('created_at', '')} {summary}")
        proof.extend(_as_list(row.get("proof")))
        next_action = str(row.get("next_action", "")).strip()
        if next_action:
            open_actions.append(next_action)
        risk = str(row.get("risk", "")).strip()
        if risk and risk != "low":
            risks.append(risk)

    compact = "\n".join(summaries)
    if len(compact) > max_chars:
        compact = compact[-max_chars:].lstrip()
    state_core = {
        "schema_version": STATE_SCHEMA_VERSION,
        "agent_id": agent_id,
        "updated_at": _utc_now(),
        "source_event_count": len(rows),
        "recent_event_ids": [str(row.get("event_id", "")) for row in recent if row.get("event_id")],
        "compact_context": compact,
        "proof": sorted(set(item for item in proof if item)),
        "open_actions": list(dict.fromkeys(open_actions)),
        "risks": sorted(set(risks)),
        "limits": {"max_items": max_items, "max_chars": max_chars},
    }
    state = {**state_core, "state_hash": _sha256_json(state_core)}
    _write_json(paths.state_path(agent_id), state)
    return state


def read_agent(root: Path = DEFAULT_ROOT, agent_id: str = "", tail: int = 10) -> dict[str, Any]:
    paths = VaultPaths(root)
    state_path = paths.state_path(agent_id)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
    events = _read_jsonl(paths.rolling_path(agent_id))[-max(0, tail) :]
    return {"agent_id": agent_id, "state": state, "events": events}


def read_channel(root: Path = DEFAULT_ROOT, channel_id: str = "", tail: int = 25) -> dict[str, Any]:
    paths = VaultPaths(root)
    rows = _read_jsonl(paths.channel_path(channel_id))
    return {"channel_id": channel_id, "count": len(rows), "events": rows[-max(0, tail) :]}


def simulate_team(
    *,
    root: Path = DEFAULT_ROOT,
    task_id: str,
    agents: list[str],
    channel_id: str = "",
) -> dict[str, Any]:
    if len(agents) < 2:
        raise ValueError("simulate requires at least two agents")
    channel = channel_id or task_id
    events = []
    for index, agent in enumerate(agents):
        recipient = agents[(index + 1) % len(agents)]
        events.append(
            append_event(
                root=root,
                agent_id=agent,
                channel_id=channel,
                task_id=task_id,
                intent="team_sync",
                recipient=recipient,
                role="lane",
                summary=f"{agent} joined channel {channel} and handed compact task state to {recipient}.",
                proof=[f"channel:{channel}", f"task:{task_id}"],
                next_action=f"{recipient} should read channel tail, ACK, and continue its lane.",
            )
        )
    states = [digest_agent(root=root, agent_id=agent) for agent in agents]
    scoreboard_core = {
        "schema_version": "scbe_agent_team_scoreboard_v1",
        "task_id": task_id,
        "channel_id": channel,
        "updated_at": _utc_now(),
        "agents": agents,
        "event_ids": [event["event_id"] for event in events],
        "state_hashes": {state["agent_id"]: state["state_hash"] for state in states},
        "ready_for_scale_test": True,
        "next_scale_step": "Run producers/tailers concurrently or mirror this vault root to a cloud sync target.",
    }
    scoreboard = {**scoreboard_core, "scoreboard_hash": _sha256_json(scoreboard_core)}
    _write_json(VaultPaths(root).scoreboard_path(task_id), scoreboard)
    return {"events": events, "states": states, "scoreboard": scoreboard}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create vault folders and manifest")

    append_p = sub.add_parser("append", help="append one agent event to rolling vault and channel")
    append_p.add_argument("--agent", required=True)
    append_p.add_argument("--channel", required=True)
    append_p.add_argument("--task-id", required=True)
    append_p.add_argument("--summary", required=True)
    append_p.add_argument("--intent", default="status")
    append_p.add_argument("--status", default="in_progress")
    append_p.add_argument("--recipient", default="")
    append_p.add_argument("--proof", nargs="*", default=[])
    append_p.add_argument("--next-action", default="")
    append_p.add_argument("--risk", default="low")
    append_p.add_argument("--role", default="worker")

    digest_p = sub.add_parser("digest", help="compact one agent's rolling trail into state.json")
    digest_p.add_argument("--agent", required=True)
    digest_p.add_argument("--max-items", type=int, default=12)
    digest_p.add_argument("--max-chars", type=int, default=1600)

    read_p = sub.add_parser("read", help="read one agent state plus recent events")
    read_p.add_argument("--agent", required=True)
    read_p.add_argument("--tail", type=int, default=10)

    channel_p = sub.add_parser("channel", help="tail a shared channel")
    channel_p.add_argument("--channel", required=True)
    channel_p.add_argument("--tail", type=int, default=25)

    sim_p = sub.add_parser("simulate", help="run a deterministic multi-agent channel smoke test")
    sim_p.add_argument("--task-id", required=True)
    sim_p.add_argument("--agents", required=True, help="comma-separated agent ids")
    sim_p.add_argument("--channel", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "init":
        result = init_vault(args.root)
    elif args.command == "append":
        result = append_event(
            root=args.root,
            agent_id=args.agent,
            channel_id=args.channel,
            task_id=args.task_id,
            summary=args.summary,
            intent=args.intent,
            status=args.status,
            recipient=args.recipient,
            proof=args.proof,
            next_action=args.next_action,
            risk=args.risk,
            role=args.role,
        )
    elif args.command == "digest":
        result = digest_agent(root=args.root, agent_id=args.agent, max_items=args.max_items, max_chars=args.max_chars)
    elif args.command == "read":
        result = read_agent(root=args.root, agent_id=args.agent, tail=args.tail)
    elif args.command == "channel":
        result = read_channel(root=args.root, channel_id=args.channel, tail=args.tail)
    elif args.command == "simulate":
        agents = [agent.strip() for agent in args.agents.split(",") if agent.strip()]
        result = simulate_team(root=args.root, task_id=args.task_id, agents=agents, channel_id=args.channel)
    else:  # pragma: no cover
        raise AssertionError(args.command)

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
