#!/usr/bin/env python3
"""Build a tracked multi-lane goal race from one user objective.

This is a thin orchestration artifact generator. It does not execute agents
itself. Instead, it emits lane packets and a scoreboard so existing Codex /
Claude / HYDRA runs can be tracked like a relay race with checkpoints.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


DEFAULT_LANES = {
    "research": ["scout", "builder", "reviewer"],
    "money": ["prospector", "builder", "closer"],
    "browser": ["navigator", "operator", "verifier"],
    "publish": ["writer", "operator", "reviewer"],
    "story": ["weaver", "forger", "editor"],
    "custom": ["runner-1", "runner-2", "overwatch"],
}

DEFAULT_PHASES = {
    "research": [
        ("sense", "Find the highest-signal sources and constraints."),
        ("extract", "Reduce the source pile into usable packets."),
        ("verify", "Check evidence quality and contradictions."),
        ("synthesize", "Turn findings into one practical output."),
    ],
    "money": [
        ("inventory", "Find assets and rails that can convert to cash."),
        ("package", "Define one deliverable buyers can understand."),
        ("activate", "Push the offer into one live channel."),
        ("followup", "Track responses, blockers, and next asks."),
    ],
    "browser": [
        ("route", "Choose browser lane and session surface."),
        ("act", "Execute the smallest useful browser actions."),
        ("verify", "Check the resulting page state and capture proof."),
        ("repair", "Patch the lane if the browser path failed."),
    ],
    "publish": [
        ("draft", "Write the platform-native source piece."),
        ("review", "Tighten tone, claims, and links before posting."),
        ("publish", "Push the piece into the selected live channel."),
        ("amplify", "Record the link, proof, and next distribution step."),
    ],
    "story": [
        ("map", "Break the chapter or scene into beats."),
        ("expand", "Turn beats into sequences and packets."),
        ("render", "Compile prompts or outputs for the lane."),
        ("review", "Check rhythm, continuity, and emotional clarity."),
    ],
    "custom": [
        ("frame", "Frame the mission and acceptance bar."),
        ("run", "Execute the main work packet."),
        ("gate", "Verify and return pass/fail."),
        ("ship", "Publish the approved result or next action."),
    ],
}

SKILL_SUGGESTIONS = {
    "research": {
        "sense": ["hydra-deep-research-self-healing", "aetherbrowser-arxiv-nav"],
        "extract": ["notion-research-documentation", "agent-handoff-packager"],
        "verify": ["video-source-verification", "plan-check-gate"],
        "synthesize": ["scbe-universal-synthesis", "article-posting-ops"],
    },
    "money": {
        "inventory": ["scbe-monetization-thought-to-cash", "profit-autopilot"],
        "package": ["scbe-monetization-thought-to-cash", "scbe-marketing-outreach-runbook"],
        "activate": ["scbe-shopify-money-flow", "article-posting-ops"],
        "followup": ["profit-autopilot", "agent-handoff-packager"],
    },
    "browser": {
        "route": ["living-codex-browser-builder", "aetherbrowser-github-nav"],
        "act": ["playwright", "aether-phone-lane-ops"],
        "verify": ["screenshot", "video-source-verification"],
        "repair": ["scbe-browser-sidepanel-ops", "development-flow-loop"],
    },
    "publish": {
        "draft": ["article-posting-ops", "issac-story-engine"],
        "review": ["video-source-verification", "agent-handoff-packager"],
        "publish": ["article-posting-ops", "living-codex-browser-builder"],
        "amplify": ["scbe-research-publishing-autopilot", "scbe-marketing-outreach-runbook"],
    },
    "story": {
        "map": ["scbe-webtoon-book-conversion", "issac-story-engine"],
        "expand": ["scbe-webtoon-book-conversion", "aethermoor-lore"],
        "render": ["scbe-manhwa-video-picture-research", "scbe-webtoon-book-conversion"],
        "review": ["novel-editor-flow", "multi-agent-review-gate"],
    },
    "custom": {
        "frame": ["multi-agent-orchestrator", "scbe-overwatch-relay-swarm"],
        "run": ["development-flow-loop", "scbe-universal-synthesis"],
        "gate": ["multi-agent-review-gate", "plan-check-gate"],
        "ship": ["agent-handoff-packager", "article-posting-ops"],
    },
}


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:64] or "goal"


@dataclass(frozen=True)
class Packet:
    task_id: str
    owner_role: str
    phase_id: str
    goal: str
    recommended_skills: List[str]
    inputs: List[str]
    allowed_paths: List[str]
    blocked_paths: List[str]
    dependencies: List[str]
    done_criteria: List[str]
    return_format: str
    checkpoint: bool


def build_packets(goal: str, mode: str, lanes: Sequence[str]) -> List[Packet]:
    packets: List[Packet] = []
    phases = DEFAULT_PHASES.get(mode, DEFAULT_PHASES["custom"])
    lane_list = list(lanes) if lanes else DEFAULT_LANES.get(mode, DEFAULT_LANES["custom"])
    base_slug = _slug(goal)

    previous_task_id = ""
    for idx, (phase_id, phase_goal) in enumerate(phases, start=1):
        owner = lane_list[(idx - 1) % len(lane_list)]
        task_id = f"{base_slug}-{idx:02d}-{phase_id}"
        dependencies = [previous_task_id] if previous_task_id else []
        checkpoint = phase_id in {"verify", "gate", "review", "followup", "repair", "ship"}
        recommended_skills = SKILL_SUGGESTIONS.get(mode, SKILL_SUGGESTIONS["custom"]).get(
            phase_id,
            ["multi-agent-orchestrator", "agent-handoff-packager"],
        )
        packets.append(
            Packet(
                task_id=task_id,
                owner_role=owner,
                phase_id=phase_id,
                goal=f"{goal} | {phase_goal}",
                recommended_skills=recommended_skills,
                inputs=[goal, f"mode={mode}", f"phase={phase_id}"],
                allowed_paths=["artifacts/", "notes/", "docs/", "scripts/"],
                blocked_paths=["secrets", "destructive git history rewrites", "unapproved production deploys"],
                dependencies=dependencies,
                done_criteria=[
                    "produce one concrete artifact or decision",
                    "write one next action for the following lane",
                    "include proof path or verification note",
                ],
                return_format="summary, proof, next_action, blockers",
                checkpoint=checkpoint,
            )
        )
        previous_task_id = task_id
    return packets


def build_scoreboard(
    goal: str, mode: str, packets: Sequence[Packet], lanes: Sequence[str], run_id: str
) -> Dict[str, Any]:
    lane_states = []
    for lane in lanes:
        owned = [packet.task_id for packet in packets if packet.owner_role == lane]
        lane_states.append(
            {
                "lane": lane,
                "status": "pending",
                "tasks": owned,
                "completed": 0,
                "checkpoints": sum(1 for packet in packets if packet.owner_role == lane and packet.checkpoint),
                "skills": sorted(
                    {skill for packet in packets if packet.owner_role == lane for skill in packet.recommended_skills}
                ),
            }
        )

    return {
        "run_id": run_id,
        "goal": goal,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "lanes": lane_states,
        "total_tasks": len(packets),
        "completed_tasks": 0,
        "checkpoint_tasks": sum(1 for packet in packets if packet.checkpoint),
        "status": "ready",
    }


def write_markdown(goal: str, mode: str, packets: Sequence[Packet], scoreboard: Dict[str, Any]) -> str:
    lines = [
        f"# Goal Race Loop — {goal}",
        "",
        f"- Run ID: `{scoreboard['run_id']}`",
        f"- Mode: `{mode}`",
        f"- Total tasks: `{scoreboard['total_tasks']}`",
        f"- Checkpoint tasks: `{scoreboard['checkpoint_tasks']}`",
        "",
        "## Lanes",
    ]
    for lane in scoreboard["lanes"]:
        lines.append(
            f"- `{lane['lane']}`: status=`{lane['status']}` tasks=`{len(lane['tasks'])}` checkpoints=`{lane['checkpoints']}`"
        )
        if lane["skills"]:
            lines.append(f"  skills: {', '.join(f'`{skill}`' for skill in lane['skills'])}")
    lines.extend(["", "## Packet Queue"])
    for packet in packets:
        dep = ", ".join(packet.dependencies) if packet.dependencies else "none"
        lines.append(
            f"- `{packet.task_id}` [{packet.owner_role}] phase=`{packet.phase_id}` checkpoint=`{str(packet.checkpoint).lower()}` deps=`{dep}`"
        )
        lines.append(f"  goal: {packet.goal}")
        lines.append(f"  skills: {', '.join(packet.recommended_skills)}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a tracked multi-lane goal race loop.")
    parser.add_argument("--goal", required=True, help="Mission or project goal.")
    parser.add_argument(
        "--mode",
        default="custom",
        choices=sorted(DEFAULT_PHASES.keys()),
        help="Packet pattern to use.",
    )
    parser.add_argument(
        "--lanes",
        default="",
        help="Comma-separated owner roles. Defaults depend on mode.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/goal_races"),
        help="Where to write the packet and scoreboard artifacts.",
    )
    args = parser.parse_args(argv)

    lanes = [item.strip() for item in args.lanes.split(",") if item.strip()] or DEFAULT_LANES.get(
        args.mode, DEFAULT_LANES["custom"]
    )
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{_slug(args.goal)}"
    out_dir = args.output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    packets = build_packets(args.goal, args.mode, lanes)
    scoreboard = build_scoreboard(args.goal, args.mode, packets, lanes, run_id)
    packet_doc = {
        "run_id": run_id,
        "goal": args.goal,
        "mode": args.mode,
        "lanes": lanes,
        "packets": [asdict(packet) for packet in packets],
    }

    packets_path = out_dir / "packets.json"
    scoreboard_path = out_dir / "scoreboard.json"
    readme_path = out_dir / "README.md"
    packets_path.write_text(json.dumps(packet_doc, indent=2), encoding="utf-8")
    scoreboard_path.write_text(json.dumps(scoreboard, indent=2), encoding="utf-8")
    readme_path.write_text(write_markdown(args.goal, args.mode, packets, scoreboard), encoding="utf-8")

    print(f"[goal-race] wrote {packets_path}")
    print(f"[goal-race] wrote {scoreboard_path}")
    print(f"[goal-race] wrote {readme_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
