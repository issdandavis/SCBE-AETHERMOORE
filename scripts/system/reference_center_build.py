#!/usr/bin/env python3
"""Build a lightweight Reference Center for smaller task agents.

Outputs:
- index.json
- small_agents_overview.md
- cards/<agent>.md
- task_queue.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def codename_for(agent: str) -> str:
    digest = hashlib.sha1(agent.encode("utf-8")).hexdigest()[:6].upper()
    stem = agent.replace(".", "-").replace("_", "-").strip("-")
    return f"{stem}-RC-{digest}"


def gather_recent_packets(repo_root: Path, max_packets: int) -> list[dict[str, Any]]:
    base = repo_root / "artifacts" / "agent_comm"
    if not base.exists():
        return []
    candidates = sorted(base.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    rows: list[dict[str, Any]] = []
    for path in candidates[: max(0, max_packets)]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            payload = {}
        rows.append(
            {
                "path": str(path.resolve()),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "task_id": payload.get("task_id") or payload.get("packet_id") or "",
                "summary": payload.get("summary") or payload.get("note") or "",
                "status": payload.get("status") or "",
            }
        )
    return rows


def build_agent_card(
    *,
    agent: str,
    out_dir: Path,
    mission: str,
    references: list[str],
    packets: list[dict[str, Any]],
) -> Path:
    card_dir = out_dir / "cards"
    card_dir.mkdir(parents=True, exist_ok=True)
    path = card_dir / f"{agent.replace('.', '_')}.md"
    lines = [
        f"# Agent Card: {agent}",
        "",
        f"- codename: `{codename_for(agent)}`",
        f"- generated_at_utc: `{utc_now()}`",
        f"- mission: {mission}",
        "",
        "## Reference Spine",
    ]
    for ref in references:
        lines.append(f"- {ref}")
    lines.extend(["", "## Recent Packets"])
    if not packets:
        lines.append("- none")
    else:
        for row in packets[:8]:
            lines.append(
                f"- `{row.get('mtime','')}` | `{row.get('status','')}` | {row.get('task_id','')} | {row.get('path','')}"
            )
    lines.extend(
        [
            "",
            "## Standard Loop",
            "1. Read this card + index.json + task_queue.jsonl.",
            "2. Claim one task, execute, and write artifact path.",
            "3. Emit cross-talk packet with task_id + status + next_action.",
            "4. Update task_queue.jsonl entry state to done/blocked.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_task_queue(out_dir: Path, tasks: list[str], default_agents: list[str]) -> Path:
    queue_path = out_dir / "task_queue.jsonl"
    rows: list[dict[str, Any]] = []
    now = utc_now()
    if tasks:
        for i, task in enumerate(tasks, start=1):
            rows.append(
                {
                    "task_id": f"RC-TASK-{i:03d}",
                    "summary": task,
                    "owner": default_agents[(i - 1) % len(default_agents)] if default_agents else "",
                    "status": "todo",
                    "created_at": now,
                    "updated_at": now,
                    "artifact_path": "",
                }
            )
    if rows:
        queue_path.write_text("".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows), encoding="utf-8")
    else:
        queue_path.write_text("", encoding="utf-8")
    return queue_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCBE small-agent Reference Center.")
    parser.add_argument("--repo-root", default="", help="Repo root (defaults from script path).")
    parser.add_argument("--out-dir", default="", help="Output directory (default: artifacts/agent_reference_center).")
    parser.add_argument("--agent", action="append", default=[], help="Agent id for card generation. Repeatable.")
    parser.add_argument("--task", action="append", default=[], help="Task summary for initial queue. Repeatable.")
    parser.add_argument("--mission", default="Execute scoped tasks with deterministic handoff packets.")
    parser.add_argument("--max-packets", type=int, default=20)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve() if args.repo_root else repo_root_from_script()
    out_dir = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else (repo_root / "artifacts" / "agent_reference_center")
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    agents = args.agent or ["agent.mini.research", "agent.mini.writer", "agent.mini.qa"]
    packets = gather_recent_packets(repo_root, args.max_packets)
    references = [
        str((repo_root / "scripts" / "system" / "terminal_crosstalk_emit.ps1").resolve()),
        str((repo_root / "scripts" / "system" / "run_deep_research_self_healing.ps1").resolve()),
        str((repo_root / "docs" / "map-room" / "session_handoff_latest.md").resolve()),
        str((repo_root / "agents" / "codex.md").resolve()),
    ]

    card_paths = [
        str(
            build_agent_card(
                agent=agent, out_dir=out_dir, mission=args.mission, references=references, packets=packets
            ).resolve()
        )
        for agent in agents
    ]
    queue_path = build_task_queue(out_dir, args.task, agents)

    overview = out_dir / "small_agents_overview.md"
    overview_lines = [
        "# Small Agent Reference Center",
        "",
        f"- generated_at_utc: `{utc_now()}`",
        f"- agents: {', '.join(agents)}",
        f"- cards_dir: `{(out_dir / 'cards').resolve()}`",
        f"- task_queue: `{queue_path.resolve()}`",
        "",
        "## Start Sequence",
        "1. Open the agent card for your lane.",
        "2. Pick one `todo` item from `task_queue.jsonl`.",
        "3. Run task, capture artifact path, emit cross-talk update.",
        "4. Mark status and move to next task.",
    ]
    overview.write_text("\n".join(overview_lines) + "\n", encoding="utf-8")

    index = {
        "ok": True,
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "out_dir": str(out_dir),
        "agents": agents,
        "cards": card_paths,
        "task_queue_path": str(queue_path.resolve()),
        "overview_path": str(overview.resolve()),
        "packet_samples": packets[:10],
    }
    index_path = out_dir / "index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(json.dumps(index, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
