#!/usr/bin/env python3
"""Merge two agent context states into a shared compact handoff packet.

This is the deterministic core for a future small "Polly helper" model. The
helper model may summarize the packet later, but the packet itself preserves
provenance, conflicts, open tasks, proof links, and next actions without
rewriting history.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crypto.sacred_tongue_payload_bijection import prove_dict  # noqa: E402

SCHEMA_VERSION = "scbe_context_librarian_compact_v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "context_librarian"


@dataclass(frozen=True)
class AgentState:
    agent_id: str
    role: str
    status: str
    summary: str
    open_tasks: list[str]
    completed_tasks: list[str]
    changed_paths: list[str]
    proof: list[str]
    blockers: list[str]
    next_actions: list[str]
    claims: dict[str, Any]
    raw: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return [str(value)]


def _load_state(path: Path) -> AgentState:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return AgentState(
        agent_id=str(payload.get("agent_id") or payload.get("sender") or path.stem),
        role=str(payload.get("role") or payload.get("owner_role") or "agent"),
        status=str(payload.get("status") or "unknown"),
        summary=str(payload.get("summary") or ""),
        open_tasks=_as_list(payload.get("open_tasks") or payload.get("pending") or payload.get("todo")),
        completed_tasks=_as_list(payload.get("completed_tasks") or payload.get("done")),
        changed_paths=_as_list(payload.get("changed_paths") or payload.get("paths")),
        proof=_as_list(payload.get("proof") or payload.get("evidence")),
        blockers=_as_list(payload.get("blockers") or payload.get("risks")),
        next_actions=_as_list(payload.get("next_actions") or payload.get("next_action")),
        claims=payload.get("claims") if isinstance(payload.get("claims"), dict) else {},
        raw=payload,
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _path_owner_map(states: list[AgentState]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for state in states:
        for path in state.changed_paths:
            owners.setdefault(path, []).append(state.agent_id)
    return {path: sorted(set(ids)) for path, ids in owners.items()}


def _detect_conflicts(states: list[AgentState]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for path, owners in _path_owner_map(states).items():
        if len(owners) > 1:
            conflicts.append(
                {
                    "type": "path_contention",
                    "path": path,
                    "agents": owners,
                    "resolution": "manual_or_integration_owner_required",
                }
            )

    claim_values: dict[str, dict[str, list[str]]] = {}
    for state in states:
        for key, value in state.claims.items():
            normalized = json.dumps(value, sort_keys=True, ensure_ascii=True)
            claim_values.setdefault(key, {}).setdefault(normalized, []).append(state.agent_id)
    for key, values in claim_values.items():
        if len(values) > 1:
            conflicts.append(
                {
                    "type": "claim_conflict",
                    "claim": key,
                    "variants": [
                        {"value": json.loads(value), "agents": sorted(agents)}
                        for value, agents in sorted(values.items())
                    ],
                    "resolution": "preserve_both_until_verified",
                }
            )
    return conflicts


def merge_states(left: AgentState, right: AgentState, *, mission_id: str = "") -> dict[str, Any]:
    states = [left, right]
    open_tasks = _dedupe([task for state in states for task in state.open_tasks])
    completed = set(_dedupe([task for state in states for task in state.completed_tasks]))
    unresolved = [task for task in open_tasks if task not in completed]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "mission_id": mission_id,
        "agents": [
            {
                "agent_id": state.agent_id,
                "role": state.role,
                "status": state.status,
                "summary": state.summary,
            }
            for state in states
        ],
        "merged": {
            "open_tasks": unresolved,
            "completed_tasks": sorted(completed),
            "changed_paths": _dedupe([path for state in states for path in state.changed_paths]),
            "proof": _dedupe([proof for state in states for proof in state.proof]),
            "blockers": _dedupe([blocker for state in states for blocker in state.blockers]),
            "next_actions": _dedupe([action for state in states for action in state.next_actions]),
        },
        "conflicts": _detect_conflicts(states),
        "provenance": {
            state.agent_id: {
                "open_tasks": state.open_tasks,
                "completed_tasks": state.completed_tasks,
                "changed_paths": state.changed_paths,
                "proof": state.proof,
                "claims": state.claims,
            }
            for state in states
        },
        "helper_policy": {
            "model_may_summarize": True,
            "model_may_resolve_conflicts": False,
            "model_must_preserve_provenance": True,
            "truth_source": "packet_fields_and_proof_links",
        },
    }
    core = {k: v for k, v in payload.items() if k != "sacred_tongue_bijection"}
    payload["sacred_tongue_bijection"] = prove_dict(core)
    return payload


def write_compact(payload: dict[str, Any], output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, str]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "shared_context_compact.json"
    md_path = out_dir / "shared_context_compact.md"
    latest_dir = output_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_json = latest_dir / "shared_context_compact.json"

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    latest_json.write_text(text, encoding="utf-8")

    merged = payload["merged"]
    lines = [
        "# Shared Context Compact",
        "",
        f"- schema: `{payload['schema_version']}`",
        f"- mission: `{payload.get('mission_id') or ''}`",
        f"- agents: `{', '.join(agent['agent_id'] for agent in payload['agents'])}`",
        f"- conflicts: `{len(payload['conflicts'])}`",
        "",
        "## Open Tasks",
        *[f"- {task}" for task in merged["open_tasks"]],
        "",
        "## Next Actions",
        *[f"- {action}" for action in merged["next_actions"]],
        "",
        "## Proof",
        *[f"- {proof}" for proof in merged["proof"]],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "latest_json": str(latest_json)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--mission-id", default="")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true", help="print compact JSON instead of writing files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = merge_states(_load_state(args.left), _load_state(args.right), mission_id=args.mission_id)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    paths = write_compact(payload, args.output_root)
    print(json.dumps({"ok": True, **paths, "conflicts": len(payload["conflicts"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
