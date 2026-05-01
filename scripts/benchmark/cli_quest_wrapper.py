#!/usr/bin/env python3
"""Wrap command-line teaching games as SCBE agent quest packets.

The wrapper does not need to vendor or execute the upstream projects. It turns
local Bashcrawl / Terminus / clmystery-style folders into bounded, auditable
tasks that an agent can navigate with ordinary shell commands, then emits a
training-ready quest record.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "config" / "eval" / "cli_quest_tasks.sample.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "cli_quest_runs"

SCHEMA_VERSION = "scbe_cli_quest_manifest_v1"
RUN_SCHEMA_VERSION = "scbe_cli_quest_run_v1"
TRAINING_SCHEMA_VERSION = "scbe_cli_quest_training_record_v1"

SOURCE_CATALOG: dict[str, dict[str, str]] = {
    "bashcrawl": {
        "title": "Bashcrawl",
        "repo_url": "https://gitlab.com/slackermedia/bashcrawl",
        "mirror_url": "https://github.com/notklaatu/bashcrawl",
        "license": "GPL-3.0",
        "pattern": "directory dungeon for POSIX shell navigation",
    },
    "terminus": {
        "title": "Terminus",
        "repo_url": "https://github.com/mprat/Terminus",
        "license": "GPL-2.0",
        "pattern": "text-adventure command objectives and world-state changes",
    },
    "clmystery": {
        "title": "Command Line Murder Mystery",
        "repo_url": "https://github.com/veltman/clmystery",
        "mirror_url": "https://github.com/makersacademy/clmystery",
        "license": "check-upstream-license-before-redistribution",
        "pattern": "evidence search, grep constraints, and final answer justification",
    },
}

DEFAULT_ALLOWED_COMMANDS = [
    "pwd",
    "ls",
    "dir",
    "cat",
    "type",
    "grep",
    "rg",
    "find",
    "Select-String",
    "cd",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class CliQuest:
    quest_id: str
    source: str
    title: str
    local_path: str
    start_path: str
    objective: str
    instructions_file: str
    success_markers: list[str]
    allowed_commands: list[str]
    sandbox: str
    max_steps: int
    repo_url: str
    license: str


def _as_list(value: Any, default: list[str] | None = None) -> list[str]:
    if value is None:
        return list(default or [])
    if not isinstance(value, list):
        raise ValueError("expected list")
    return [str(x) for x in value]


def _resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def load_manifest(path: Path) -> list[CliQuest]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"manifest schema_version must be {SCHEMA_VERSION}")
    rows = payload.get("quests")
    if not isinstance(rows, list):
        raise ValueError("manifest.quests must be a list")

    quests: list[CliQuest] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("quest rows must be JSON objects")
        source = str(row.get("source", "")).strip()
        catalog = SOURCE_CATALOG.get(source, {})
        allowed = _as_list(row.get("allowed_commands"), DEFAULT_ALLOWED_COMMANDS)
        quests.append(
            CliQuest(
                quest_id=str(row["quest_id"]),
                source=source,
                title=str(row.get("title") or catalog.get("title") or row["quest_id"]),
                local_path=str(row.get("local_path", "")),
                start_path=str(row.get("start_path", ".")),
                objective=str(row.get("objective", "")),
                instructions_file=str(row.get("instructions_file", "")),
                success_markers=_as_list(row.get("success_markers")),
                allowed_commands=allowed,
                sandbox=str(row.get("sandbox", "copy")),
                max_steps=max(1, int(row.get("max_steps", 30))),
                repo_url=str(row.get("repo_url") or catalog.get("repo_url", "")),
                license=str(row.get("license") or catalog.get("license", "unknown")),
            )
        )
    return quests


def validate_quests(quests: list[CliQuest]) -> dict[str, Any]:
    problems: list[str] = []
    seen: set[str] = set()
    for quest in quests:
        if quest.quest_id in seen:
            problems.append(f"duplicate quest_id: {quest.quest_id}")
        seen.add(quest.quest_id)
        if quest.source not in SOURCE_CATALOG:
            problems.append(f"{quest.quest_id}: unknown source {quest.source!r}")
        if quest.sandbox not in {"copy", "read_only", "external_planned"}:
            problems.append(f"{quest.quest_id}: unsupported sandbox {quest.sandbox!r}")
        if not quest.objective:
            problems.append(f"{quest.quest_id}: missing objective")
        if not quest.local_path:
            problems.append(f"{quest.quest_id}: missing local_path")
        if not quest.instructions_file:
            problems.append(f"{quest.quest_id}: missing instructions_file")
        if not quest.success_markers:
            problems.append(f"{quest.quest_id}: missing success_markers")
        if not quest.allowed_commands:
            problems.append(f"{quest.quest_id}: missing allowed_commands")
    return {"ok": not problems, "quest_count": len(quests), "problems": problems}


def _copy_quest(src: Path, dest: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        blocked = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache"}
        return {name for name in names if name in blocked}

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=ignore)


def _read_instruction(workspace: Path, quest: CliQuest) -> str:
    path = workspace / quest.start_path / quest.instructions_file
    if not path.exists():
        return ""
    if path.is_dir():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:8000]


def prepare_quest(quest: CliQuest, output_root: Path, *, copy_source: bool = True) -> dict[str, Any]:
    source_root = _resolve_repo_path(quest.local_path)
    run_dir = output_root / quest.quest_id / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    if not source_root.exists():
        payload = {
            "schema_version": RUN_SCHEMA_VERSION,
            "quest_id": quest.quest_id,
            "source": quest.source,
            "title": quest.title,
            "status": "missing_source",
            "ok": False,
            "source_root": str(source_root),
            "run_dir": str(run_dir),
            "repo_url": quest.repo_url,
            "recommended_fetch": f"clone or export {quest.repo_url} into {quest.local_path}",
            "license": quest.license,
        }
        (run_dir / "quest_packet.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return payload

    workspace = run_dir / "workspace"
    if quest.sandbox == "copy" and copy_source:
        _copy_quest(source_root, workspace)
    else:
        workspace = source_root

    instruction_text = _read_instruction(workspace, quest)
    task_packet = {
        "schema_version": RUN_SCHEMA_VERSION,
        "quest_id": quest.quest_id,
        "source": quest.source,
        "title": quest.title,
        "status": "prepared",
        "ok": True,
        "workspace": str(workspace),
        "start_path": str((workspace / quest.start_path).resolve()),
        "objective": quest.objective,
        "instructions_file": quest.instructions_file,
        "instruction_excerpt": instruction_text,
        "success_markers": quest.success_markers,
        "allowed_commands": quest.allowed_commands,
        "sandbox": quest.sandbox,
        "max_steps": quest.max_steps,
        "upstream": {
            "repo_url": quest.repo_url,
            "license": quest.license,
            "pattern": SOURCE_CATALOG.get(quest.source, {}).get("pattern", ""),
        },
        "agent_contract": {
            "observe_first": True,
            "do_not_modify_source": quest.sandbox == "read_only",
            "emit_trajectory_jsonl": True,
            "final_answer_requires_evidence": True,
        },
    }
    training_record = {
        "schema_version": TRAINING_SCHEMA_VERSION,
        "category": "agentic-cli-quest",
        "source": quest.source,
        "quest_id": quest.quest_id,
        "instruction": (
            "Complete this CLI quest using only the allowed shell commands. "
            "Observe files first, collect evidence, and return the final answer with command trace."
        ),
        "input": {
            "objective": quest.objective,
            "start_path": task_packet["start_path"],
            "allowed_commands": quest.allowed_commands,
            "success_markers": quest.success_markers,
        },
        "expected_behavior": [
            "navigate before acting",
            "use command output as evidence",
            "avoid destructive commands",
            "produce final answer only after satisfying success markers",
        ],
        "routing": {
            "geoseal_lane": "agentic_training_loop",
            "recommended_role_pair": ["Navigator", "Verifier"],
        },
    }
    (run_dir / "quest_packet.json").write_text(json.dumps(task_packet, indent=2) + "\n", encoding="utf-8")
    (run_dir / "training_record.json").write_text(json.dumps(training_record, indent=2) + "\n", encoding="utf-8")
    (run_dir / "trajectory.jsonl").write_text(
        json.dumps(
            {
                "event": "quest_prepared",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "quest_id": quest.quest_id,
                "start_path": task_packet["start_path"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {**task_packet, "run_dir": str(run_dir)}


def write_catalog(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "scbe_cli_quest_source_catalog_v1",
        "sources": SOURCE_CATALOG,
        "default_allowed_commands": DEFAULT_ALLOWED_COMMANDS,
    }
    path = output_root / "source_catalog.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(path), "source_count": len(SOURCE_CATALOG)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    sub.add_parser("validate")
    prep = sub.add_parser("prepare")
    prep.add_argument("--quest-id", default="", help="Prepare one quest; default prepares all")
    prep.add_argument("--no-copy", action="store_true", help="Reference local source instead of copying it")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "catalog":
        print(json.dumps(write_catalog(args.output_root), indent=2))
        return 0
    quests = load_manifest(args.manifest)
    validation = validate_quests(quests)
    if args.command == "validate":
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 0 if validation["ok"] else 1
    if not validation["ok"]:
        print(json.dumps(validation, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    selected = [q for q in quests if not args.quest_id or q.quest_id == args.quest_id]
    if not selected:
        print(json.dumps({"ok": False, "error": f"quest not found: {args.quest_id}"}, indent=2), file=sys.stderr)
        return 1
    results = [prepare_quest(q, args.output_root, copy_source=not args.no_copy) for q in selected]
    payload = {"ok": all(r.get("ok") for r in results), "results": results}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
