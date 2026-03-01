#!/usr/bin/env python3
"""Agent roundtable orchestrator for notes-driven multi-AI collaboration.

Creates a small chat loop where local/offline context is threaded through
multiple specialized agent personas. Every run writes human-readable notes and
machine-readable JSON so future AI sessions can continue without context loss.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from src.fleet.octo_armor import OctoArmor, Tentacle


@dataclass(frozen=True)
class Persona:
    name: str
    task_type: str
    tentacle: Optional[Tentacle]
    objective: str
    style: str


PERSONAS: Dict[str, Persona] = {
    "builder": Persona(
        name="Builder",
        task_type="architecture",
        tentacle=Tentacle.GOOGLE_AI,
        objective="Design a practical roadmap and execution sequence for monetization.",
        style="technical, shippable, and constrained to real implementation steps",
    ),
    "skeptic": Persona(
        name="Skeptic",
        task_type="analysis",
        tentacle=Tentacle.GROQ,
        objective="Find failure modes, attack surfaces, and reasons the plan may fail.",
        style="hard-nosed risk review with concrete failure cases",
    ),
    "risk": Persona(
        name="Risk",
        task_type="governance",
        tentacle=Tentacle.CLAUDE,
        objective="Apply governance and safety constraints before shipping.",
        style="strict control checks and measurable controls only",
    ),
    "marketer": Persona(
        name="Marketer",
        task_type="creative",
        tentacle=Tentacle.TOGETHER,
        objective="Create monetizable offer angles and buyer-focused value messages.",
        style="clear product language and conversion-oriented",
    ),
    "executor": Persona(
        name="Executor",
        task_type="analysis",
        tentacle=Tentacle.GITHUB_MODELS,
        objective="Convert strategy into a short list of immediate tasks and ownership.",
        style="operations-first, short lead times, explicit deliverables",
    ),
}


ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "agent_roundtable"
NOTES_ROOT = REPO_ROOT / "docs" / "notes"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return (cleaned[:64] or "agent-roundtable")


def _read_obsidian_context(
    *,
    vault: str = "",
    session_query: str = "",
    folders: str = "Sessions,Context",
    max_chars: int = 5000,
) -> Optional[Dict[str, str]]:
    try:
        from scripts.obsidian_ai_hub import resolve_vault_path, read_context

        if not vault:
            vault = str(resolve_vault_path())
        context_record = read_context(
            vault_path=vault,
            session_query=session_query,
            include_folders=tuple([item.strip() for item in folders.split(",") if item.strip()]),
            latest=True,
            max_chars=max_chars,
        )
        return {
            "path": context_record.get("path", ""),
            "content": str(context_record.get("content", "")),
        }
    except Exception:
        return None


def _local_notes_context() -> Optional[Dict[str, str]]:
    if not NOTES_ROOT.exists():
        return None

    recent = sorted(NOTES_ROOT.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not recent:
        return None
    path = recent[0]
    return {"path": str(path), "content": path.read_text(encoding="utf-8", errors="replace")}


def _parse_result_text(result: Dict[str, Any]) -> str:
    for key in ("response", "answer", "text"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    messages = result.get("messages")
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict):
            for key in ("content", "text"):
                value = last.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    error = result.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()

    return ""


def _build_prompt(
    *,
    persona: Persona,
    topic: str,
    objective: str,
    context: str,
    previous: List[Dict[str, Any]],
    round_no: int,
    turn_no: int,
) -> str:
    history = "\n".join(
        f"{line['role']} (R{line['round']}T{line['turn']}): {line['response'][:140]}"
        for line in previous[-12:]
    ) or "(no history yet)"

    return (
        f"You are the {persona.name} persona ({persona.style}).\n"
        f"Topic: {topic}\n"
        f"Core objective: {objective}\n"
        f"Round {round_no}, Turn {turn_no}.\n\n"
        f"Context:\\n{context or '(no local context available)'}\\n\\n"
        f"Recent transcript:\n{history}\n\n"
        f"Task for this turn: {persona.objective}\n"
        "Respond with 3-5 concise bullets, then one concrete next action."
    )


def _shorten(value: str, limit: int = 5000) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


async def run_roundtable(args: argparse.Namespace) -> Dict[str, Any]:
    selected_keys = [key.strip().lower() for key in args.roles.split(",") if key.strip()]
    if not selected_keys:
        selected = list(PERSONAS.values())
    else:
        selected = [
            PERSONAS[key]
            for key in selected_keys
            if key in PERSONAS
        ]
        if not selected:
            raise ValueError("No valid roles selected.")

    context = ""
    context_path = ""
    if args.context_from_obsidian:
        obs_context = _read_obsidian_context(
            vault=args.vault,
            session_query=args.session_query,
            folders=args.obsidian_folders,
            max_chars=args.max_context_chars,
        )
        if obs_context:
            context = obs_context.get("content", "")
            context_path = obs_context.get("path", "")

    if not context:
        local_context = _local_notes_context()
        if local_context:
            context = local_context.get("content", "")
            context_path = local_context.get("path", "")

    if not context:
        context = "No notes context found; rely only on the topic."

    armor = OctoArmor()
    turn_log: List[Dict[str, Any]] = []
    run_id = _timestamp()
    run_root = ARTIFACT_ROOT / f"{_slug(args.topic)}-{run_id}"
    run_root.mkdir(parents=True, exist_ok=True)

    for round_no in range(1, args.rounds + 1):
        for turn_no, persona in enumerate(selected, start=1):
            prompt = _build_prompt(
                persona=persona,
                topic=args.topic,
                objective=args.objective or "generate a monetization path",
                context=_shorten(context, 2200),
                previous=turn_log,
                round_no=round_no,
                turn_no=turn_no,
            )

            if args.simulate:
                status = "ok"
                result = {
                    "response": (
                        f"[{persona.name}] Simulation turn."
                        f" Keep this run simple, create a monetization action around {args.topic}."
                    ),
                    "tentacle": "simulate",
                    "model": "simulate",
                    "quality": 0.0,
                    "latency_ms": 0.0,
                    "training_pair_generated": False,
                }
            else:
                result = await armor.reach(
                    prompt,
                    task_type=persona.task_type,
                    preferred_tentacle=persona.tentacle,
                )

            text = _parse_result_text(result)
            turn = {
                "round": round_no,
                "turn": turn_no,
                "role": persona.name,
                "status": result.get("status", "ok"),
                "tentacle": result.get("tentacle", getattr(persona.tentacle, "value", "auto")),
                "model": result.get("model", ""),
                "quality": result.get("quality", 0.0),
                "latency_ms": result.get("latency_ms", 0.0),
                "training_pair_generated": bool(result.get("training_pair_generated", False)),
                "response": text or "(empty)",
            }
            turn_log.append(turn)

    consensus = {
        "status": "ok",
        "summary": "\n".join(
            f"- {entry['role']}: {entry['response'][:220]}" for entry in turn_log[-len(selected):]
        ),
        "recommended_next_steps": [
            "Turn the strongest proposal into 3 tickets",
            "Spin one content batch from the proposal for social + marketplace",
            "Push training telemetry and monitor HF quality ratios",
        ],
        "context_reference": context_path,
    }

    payload = {
        "run_id": run_id,
        "topic": args.topic,
        "objective": args.objective,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "rounds": args.rounds,
        "roles": [
            {
                "name": persona.name,
                "task_type": persona.task_type,
                "tentacle": getattr(persona.tentacle, "value", "auto"),
                "objective": persona.objective,
            }
            for persona in selected
        ],
        "context_source": context_path or "local_notes",
        "context": _shorten(context, 3000),
        "turns": turn_log,
        "consensus": consensus,
        "artifact_dir": str(run_root),
    }

    run_json = run_root / "run.json"
    run_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    run_md = run_root / "run.md"
    md_lines = [
        f"# Agent Roundtable: {args.topic}",
        f"Run ID: {run_id}",
        f"Started: {payload['started_utc']}",
        f"Rounds: {args.rounds}",
        "",
        "## Context",
        _shorten(context, 2000),
        "",
        "## Consensus",
        consensus["summary"],
        "",
        "## Recommended Next Steps",
        *[f"- {item}" for item in consensus["recommended_next_steps"]],
        "",
        "## Transcript",
    ]
    for row in turn_log:
        md_lines.append(
            f"### {row['role']} (R{row['round']} T{row['turn']}) - {row['status']}"
        )
        md_lines.append(f"Provider: {row['tentacle']} / {row['model']}")
        md_lines.append(f"Quality: {row['quality']}")
        md_lines.append(row['response'])
        md_lines.append("")

    run_md.write_text("\n".join(md_lines), encoding="utf-8")

    NOTES_ROOT.mkdir(parents=True, exist_ok=True)
    latest_note = NOTES_ROOT / "agent_roundtable_latest.md"
    latest_note.write_text(
        "\n".join(
            [
                f"# Agent Roundtable Latest",
                f"Run: {run_id}",
                f"Topic: {args.topic}",
                f"Artifacts: {run_root}",
                f"Latest summary: {consensus['summary']}",
            ]
        ),
        encoding="utf-8",
    )

    if args.post_obsidian:
        try:
            from scripts.obsidian_ai_hub import resolve_vault_path, post_context

            vault = resolve_vault_path(args.vault)
            note_text = "\n".join(
                [
                    f"# Roundtable Session",
                    f"Run: {run_id}",
                    f"Topic: {args.topic}",
                    f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
                    "",
                    "## Summary",
                    consensus["summary"],
                    "",
                    "## Next Actions",
                    *[f"- {item}" for item in consensus["recommended_next_steps"]],
                    "",
                    "## Notes",
                    f"Artifact JSON: {run_json}",
                    f"Artifact Markdown: {run_md}",
                ]
            )
            obsidian_path = post_context(vault, title=f"agent-roundtable-{_slug(args.topic)}-{run_id}", body=note_text, folder="Sessions")
            payload["obsidian_note"] = str(obsidian_path)
        except Exception:
            payload["obsidian_note"] = "not available"

    run_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "run_id": run_id,
        "json": str(run_json),
        "markdown": str(run_md),
        "note": str(latest_note),
        "payload": payload,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SCBE multi-agent roundtable.")
    parser.add_argument("--topic", required=True, help="Roundtable topic / problem statement.")
    parser.add_argument("--objective", default="", help="Optional high-level objective override.")
    parser.add_argument("--rounds", type=int, default=2, help="Number of rounds to run.")
    parser.add_argument("--roles", default="builder,skeptic,risk,marketer,executor", help="Comma-separated persona list.")
    parser.add_argument("--simulate", action="store_true", help="Run with synthetic responses only.")
    parser.add_argument("--context-from-obsidian", action="store_true", help="Load latest notes from Obsidian as context.")
    parser.add_argument("--vault", default="", help="Obsidian vault path (auto-detect if omitted).")
    parser.add_argument("--session-query", default="", help="Filter context file by session query.")
    parser.add_argument("--obsidian-folders", default="Sessions,Context", help="Folders under AI Workspace to search.")
    parser.add_argument("--max-context-chars", type=int, default=5000, help="Context chars injected per run.")
    parser.add_argument("--post-obsidian", action="store_true", help="Post final summary into Obsidian Sessions.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.rounds <= 0:
        raise SystemExit("--rounds must be >= 1")

    summary = asyncio.run(run_roundtable(args))
    print(f"Run complete: {summary['run_id']}")
    print(f"JSON: {summary['json']}")
    print(f"Markdown: {summary['markdown']}")
    print(f"Latest note: {summary['note']}")
    if "obsidian_note" in summary["payload"]:
        print(f"Obsidian: {summary['payload']['obsidian_note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

