from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "action_map_v1"
EVENT_SCHEMA_VERSION = "action_event_v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "training" / "runs" / "action_maps"
REPO_ORDERING_LATEST = REPO_ROOT / "artifacts" / "repo-ordering" / "latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str, *, fallback: str = "task", max_length: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if not slug:
        return fallback
    return slug[:max_length].rstrip("-") or fallback


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def parse_json_object(raw: str | None, field_name: str) -> dict[str, Any]:
    cleaned = safe_text(raw)
    if not cleaned:
        return {}
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must decode to an object")
    return value


def parse_decisions(raw_entries: list[str] | None) -> list[dict[str, str]]:
    decisions: list[dict[str, str]] = []
    for entry in raw_entries or []:
        cleaned = safe_text(entry)
        if not cleaned:
            continue
        rationale = ""
        if "::" in cleaned:
            cleaned, rationale = cleaned.split("::", 1)
        key, sep, value = cleaned.partition("=")
        if not sep:
            raise ValueError("decision entries must use key=value or key=value::rationale")
        decisions.append(
            {
                "key": safe_text(key),
                "value": safe_text(value),
                "rationale": safe_text(rationale),
            }
        )
    return decisions


def unique_strings(items: list[str] | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items or []:
        cleaned = safe_text(item)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


@dataclass(frozen=True)
class ActionEvent:
    event_id: str
    run_id: str
    event_type: str
    task: str
    summary: str
    timestamp_utc: str
    step_index: int
    status: str = "in_progress"
    operator: str = "agent.codex"
    lane: str = "terminal"
    tool: str = ""
    command: str = ""
    next_action: str = ""
    tags: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    touched_layers: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    proof: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    decisions: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionEvent":
        return cls(
            event_id=safe_text(payload.get("event_id")),
            run_id=safe_text(payload.get("run_id")),
            event_type=safe_text(payload.get("event_type")),
            task=safe_text(payload.get("task")),
            summary=safe_text(payload.get("summary")),
            timestamp_utc=safe_text(payload.get("timestamp_utc")),
            step_index=int(payload.get("step_index") or 0),
            status=safe_text(payload.get("status")) or "in_progress",
            operator=safe_text(payload.get("operator")) or "agent.codex",
            lane=safe_text(payload.get("lane")) or "terminal",
            tool=safe_text(payload.get("tool")),
            command=safe_text(payload.get("command")),
            next_action=safe_text(payload.get("next_action")),
            tags=unique_strings(payload.get("tags") or []),
            skills=unique_strings(payload.get("skills") or []),
            touched_layers=unique_strings(payload.get("touched_layers") or []),
            changed_files=unique_strings(payload.get("changed_files") or []),
            proof=unique_strings(payload.get("proof") or []),
            artifacts=unique_strings(payload.get("artifacts") or []),
            inputs=dict(payload.get("inputs") or {}),
            outputs=dict(payload.get("outputs") or {}),
            metadata=dict(payload.get("metadata") or {}),
            metrics=dict(payload.get("metrics") or {}),
            decisions=list(payload.get("decisions") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVENT_SCHEMA_VERSION,
            "event_id": self.event_id,
            "run_id": self.run_id,
            "event_type": self.event_type,
            "task": self.task,
            "summary": self.summary,
            "timestamp_utc": self.timestamp_utc,
            "step_index": self.step_index,
            "status": self.status,
            "operator": self.operator,
            "lane": self.lane,
            "tool": self.tool,
            "command": self.command,
            "next_action": self.next_action,
            "tags": self.tags,
            "skills": self.skills,
            "touched_layers": self.touched_layers,
            "changed_files": self.changed_files,
            "proof": self.proof,
            "artifacts": self.artifacts,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "metrics": self.metrics,
            "decisions": self.decisions,
        }


def run_dir(run_root: Path, run_id: str) -> Path:
    return Path(run_root) / run_id


def events_path(run_root: Path, run_id: str) -> Path:
    return run_dir(run_root, run_id) / "events.jsonl"


def action_map_path(run_root: Path, run_id: str) -> Path:
    return run_dir(run_root, run_id) / "action_map.json"


def run_summary_path(run_root: Path, run_id: str) -> Path:
    return run_dir(run_root, run_id) / "run_summary.json"


def training_rows_path(run_root: Path, run_id: str) -> Path:
    return run_dir(run_root, run_id) / "training_rows.jsonl"


def create_run_id(task: str) -> str:
    return f"{utc_stamp()}-{safe_slug(task)}"


def load_events(run_root: Path, run_id: str) -> list[ActionEvent]:
    path = events_path(run_root, run_id)
    if not path.exists():
        raise FileNotFoundError(f"Action-map run not found: {run_id}")
    events: list[ActionEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip()
            if not cleaned:
                continue
            payload = json.loads(cleaned)
            events.append(ActionEvent.from_dict(payload))
    events.sort(key=lambda item: (item.step_index, item.timestamp_utc, item.event_id))
    return events


def find_latest_run(run_root: Path) -> str | None:
    root = Path(run_root)
    if not root.exists():
        return None
    candidates = [entry.name for entry in root.iterdir() if entry.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def next_step_index(existing_events: list[ActionEvent]) -> int:
    if not existing_events:
        return 0
    return max(event.step_index for event in existing_events) + 1


def append_event(
    run_root: Path,
    *,
    run_id: str,
    event_type: str,
    task: str,
    summary: str,
    status: str,
    operator: str,
    lane: str,
    tool: str,
    command: str,
    next_action: str,
    tags: list[str] | None = None,
    skills: list[str] | None = None,
    touched_layers: list[str] | None = None,
    changed_files: list[str] | None = None,
    proof: list[str] | None = None,
    artifacts: list[str] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    decisions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    root = Path(run_root)
    current_events = load_events(root, run_id) if events_path(root, run_id).exists() else []
    step_index = next_step_index(current_events)
    event = ActionEvent(
        event_id=f"{event_type}-{utc_stamp()}-{step_index:04d}",
        run_id=run_id,
        event_type=event_type,
        task=task,
        summary=summary,
        timestamp_utc=utc_now(),
        step_index=step_index,
        status=status,
        operator=operator,
        lane=lane,
        tool=tool,
        command=command,
        next_action=next_action,
        tags=unique_strings(tags),
        skills=unique_strings(skills),
        touched_layers=unique_strings(touched_layers),
        changed_files=unique_strings(changed_files),
        proof=unique_strings(proof),
        artifacts=unique_strings(artifacts),
        inputs=dict(inputs or {}),
        outputs=dict(outputs or {}),
        metadata=dict(metadata or {}),
        metrics=dict(metrics or {}),
        decisions=list(decisions or []),
    )
    event_file = events_path(root, run_id)
    event_file.parent.mkdir(parents=True, exist_ok=True)
    with event_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict(), ensure_ascii=True) + "\n")
    return {
        "run_id": run_id,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "step_index": event.step_index,
        "event_path": str(event_file),
        "summary": event.summary,
        "status": event.status,
    }


def start_run(
    run_root: Path,
    *,
    task: str,
    run_id: str | None = None,
    summary: str = "",
    operator: str = "agent.codex",
    lane: str = "terminal",
    tool: str = "",
    command: str = "",
    next_action: str = "",
    tags: list[str] | None = None,
    skills: list[str] | None = None,
    touched_layers: list[str] | None = None,
    changed_files: list[str] | None = None,
    proof: list[str] | None = None,
    artifacts: list[str] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    decisions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    resolved_run_id = safe_text(run_id) or create_run_id(task)
    event_file = events_path(run_root, resolved_run_id)
    if event_file.exists():
        raise FileExistsError(f"Action-map run already exists: {resolved_run_id}")
    result = append_event(
        run_root,
        run_id=resolved_run_id,
        event_type="start",
        task=task,
        summary=summary or f"Started workflow for {task}",
        status="in_progress",
        operator=operator,
        lane=lane,
        tool=tool,
        command=command,
        next_action=next_action,
        tags=tags,
        skills=skills,
        touched_layers=touched_layers,
        changed_files=changed_files,
        proof=proof,
        artifacts=artifacts,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
        metrics=metrics,
        decisions=decisions,
    )
    result["run_dir"] = str(run_dir(run_root, resolved_run_id))
    result["task"] = task
    return result


def append_step(
    run_root: Path,
    *,
    run_id: str,
    summary: str,
    status: str = "in_progress",
    operator: str = "agent.codex",
    lane: str = "terminal",
    tool: str = "",
    command: str = "",
    next_action: str = "",
    tags: list[str] | None = None,
    skills: list[str] | None = None,
    touched_layers: list[str] | None = None,
    changed_files: list[str] | None = None,
    proof: list[str] | None = None,
    artifacts: list[str] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    decisions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    events = load_events(run_root, run_id)
    return append_event(
        run_root,
        run_id=run_id,
        event_type="step",
        task=events[0].task,
        summary=summary,
        status=status,
        operator=operator,
        lane=lane,
        tool=tool,
        command=command,
        next_action=next_action,
        tags=tags,
        skills=skills,
        touched_layers=touched_layers,
        changed_files=changed_files,
        proof=proof,
        artifacts=artifacts,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
        metrics=metrics,
        decisions=decisions,
    )


def close_run(
    run_root: Path,
    *,
    run_id: str,
    summary: str,
    status: str = "completed",
    operator: str = "agent.codex",
    lane: str = "terminal",
    tool: str = "",
    command: str = "",
    next_action: str = "",
    tags: list[str] | None = None,
    skills: list[str] | None = None,
    touched_layers: list[str] | None = None,
    changed_files: list[str] | None = None,
    proof: list[str] | None = None,
    artifacts: list[str] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    decisions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    events = load_events(run_root, run_id)
    return append_event(
        run_root,
        run_id=run_id,
        event_type="close",
        task=events[0].task,
        summary=summary,
        status=status,
        operator=operator,
        lane=lane,
        tool=tool,
        command=command,
        next_action=next_action,
        tags=tags,
        skills=skills,
        touched_layers=touched_layers,
        changed_files=changed_files,
        proof=proof,
        artifacts=artifacts,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
        metrics=metrics,
        decisions=decisions,
    )


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status_output = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    dirty_files: list[str] = []
    dirty_roots: dict[str, int] = {}
    for line in status_output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"').replace("\\", "/")
        dirty_files.append(path)
        root = path.split("/", 1)[0]
        dirty_roots[root] = dirty_roots.get(root, 0) + 1

    top_dirty = [
        {"name": name, "dirty_count": count}
        for name, count in sorted(dirty_roots.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "available": True,
        "branch": branch,
        "dirty_file_count": len(dirty_files),
        "top_dirty_roots": top_dirty,
        "sample_dirty_files": dirty_files[:50],
    }


def load_repo_ordering_snapshot() -> dict[str, Any] | None:
    if not REPO_ORDERING_LATEST.exists():
        return None
    try:
        return json.loads(REPO_ORDERING_LATEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_cleanup_focus(task: str, repo_snapshot: dict[str, Any]) -> dict[str, Any]:
    ordering = load_repo_ordering_snapshot()
    annotated_hotspots: list[dict[str, Any]] = []
    reason_by_root: dict[str, dict[str, Any]] = {}
    if ordering:
        for entry in ordering.get("root_entries", []):
            reason_by_root[str(entry.get("name"))] = {
                "category": entry.get("category", "unknown"),
                "reason": entry.get("reason", ""),
            }
    for row in repo_snapshot.get("top_dirty_roots", []):
        detail = reason_by_root.get(row["name"], {})
        annotated_hotspots.append(
            {
                "name": row["name"],
                "dirty_count": row["dirty_count"],
                "category": detail.get("category", "unknown"),
                "reason": detail.get("reason", ""),
            }
        )
    return {
        "task_matches_cleanup": any(token in task.lower() for token in ("clean", "cleanup", "organize", "sort")),
        "dirty_hotspots": annotated_hotspots,
    }


def workflow_signature(task: str, timeline: list[dict[str, Any]]) -> str:
    payload = {
        "task": task,
        "timeline": [
            {
                "event_type": row["event_type"],
                "status": row["status"],
                "tool": row["tool"],
                "summary": row["summary"],
            }
            for row in timeline
        ],
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_training_rows(action_map: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prior_steps: list[dict[str, str]] = []
    for event in action_map["timeline"]:
        condensed = {
            "event_type": event["event_type"],
            "summary": event["summary"],
            "status": event["status"],
            "tool": event["tool"],
        }
        if event["event_type"] == "start":
            prior_steps.append(condensed)
            continue
        rows.append(
            {
                "instruction": f"Continue the SCBE workflow for task: {action_map['task']}",
                "input": {
                    "run_id": action_map["run_id"],
                    "workflow_signature": action_map["workflow_signature"],
                    "prior_steps": prior_steps[-5:],
                    "event_type": event["event_type"],
                    "lane": event["lane"],
                    "operator": event["operator"],
                },
                "output": json.dumps(
                    {
                        "summary": event["summary"],
                        "status": event["status"],
                        "tool": event["tool"],
                        "command": event["command"],
                        "changed_files": event["changed_files"],
                        "artifacts": event["artifacts"],
                        "next_action": event["next_action"],
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                "source": "action_map_protocol",
                "metadata": {
                    "origin": "action_map_protocol",
                    "run_id": action_map["run_id"],
                    "task": action_map["task"],
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "step_index": event["step_index"],
                    "timestamp_utc": event["timestamp_utc"],
                    "terminal_status": event["status"],
                },
            }
        )
        prior_steps.append(condensed)
    return rows


def build_action_map(run_root: Path, run_id: str) -> dict[str, Any]:
    events = load_events(run_root, run_id)
    if not events:
        raise ValueError(f"No action-map events found for run: {run_id}")

    task = events[0].task
    timeline = [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "step_index": event.step_index,
            "timestamp_utc": event.timestamp_utc,
            "summary": event.summary,
            "status": event.status,
            "operator": event.operator,
            "lane": event.lane,
            "tool": event.tool,
            "command": event.command,
            "next_action": event.next_action,
            "tags": event.tags,
            "skills": event.skills,
            "touched_layers": event.touched_layers,
            "changed_files": event.changed_files,
            "proof": event.proof,
            "artifacts": event.artifacts,
            "decisions": event.decisions,
        }
        for event in events
    ]

    terminal_status = events[-1].status
    tools = unique_strings([event.tool for event in events if event.tool])
    lanes = unique_strings([event.lane for event in events if event.lane])
    skills = unique_strings([skill for event in events for skill in event.skills])
    touched_layers = unique_strings([layer for event in events for layer in event.touched_layers])
    changed_files = unique_strings([path for event in events for path in event.changed_files])
    artifacts = unique_strings([path for event in events for path in event.artifacts])
    proof = unique_strings([path for event in events for path in event.proof])
    tags = unique_strings([tag for event in events for tag in event.tags])
    decisions = [decision for event in events for decision in event.decisions]

    status_counts: dict[str, int] = {}
    for event in events:
        status_counts[event.status] = status_counts.get(event.status, 0) + 1

    repo_snapshot = git_snapshot(REPO_ROOT)
    cleanup_focus = build_cleanup_focus(task, repo_snapshot)
    signature = workflow_signature(task, timeline)

    action_map = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "task": task,
        "started_at": events[0].timestamp_utc,
        "closed_at": events[-1].timestamp_utc if events[-1].event_type == "close" else "",
        "workflow_signature": signature,
        "summary": {
            "terminal_status": terminal_status,
            "event_count": len(events),
            "step_count": sum(1 for event in events if event.event_type == "step"),
            "status_counts": status_counts,
        },
        "lanes": lanes,
        "tools": tools,
        "skills": skills,
        "tags": tags,
        "touched_layers": touched_layers,
        "changed_files": changed_files,
        "artifacts": artifacts,
        "proof": proof,
        "decisions": decisions,
        "timeline": timeline,
        "repo_snapshot": repo_snapshot,
        "cleanup_focus": cleanup_focus,
    }
    rows = build_training_rows(action_map)
    summary = {
        "run_id": run_id,
        "task": task,
        "terminal_status": terminal_status,
        "event_count": len(events),
        "training_rows": len(rows),
        "action_map_path": str(action_map_path(run_root, run_id)),
        "training_rows_path": str(training_rows_path(run_root, run_id)),
    }

    write_json(action_map_path(run_root, run_id), action_map)
    write_json(run_summary_path(run_root, run_id), summary)
    write_jsonl(training_rows_path(run_root, run_id), rows)
    return {**summary, "workflow_signature": signature, "cleanup_focus": cleanup_focus}


def status(run_root: Path, run_id: str | None = None) -> dict[str, Any]:
    resolved_run_id = run_id or find_latest_run(run_root)
    if not resolved_run_id:
        return {"available": False, "message": "No action-map runs found."}
    events = load_events(run_root, resolved_run_id)
    latest = events[-1]
    payload = {
        "available": True,
        "run_id": resolved_run_id,
        "task": events[0].task,
        "event_count": len(events),
        "latest_event": {
            "event_id": latest.event_id,
            "event_type": latest.event_type,
            "status": latest.status,
            "summary": latest.summary,
            "timestamp_utc": latest.timestamp_utc,
        },
        "artifacts": {
            "events": str(events_path(run_root, resolved_run_id)),
            "action_map": str(action_map_path(run_root, resolved_run_id)),
            "run_summary": str(run_summary_path(run_root, resolved_run_id)),
            "training_rows": str(training_rows_path(run_root, resolved_run_id)),
        },
    }
    if run_summary_path(run_root, resolved_run_id).exists():
        payload["compiled"] = True
        payload["compiled_summary"] = json.loads(run_summary_path(run_root, resolved_run_id).read_text(encoding="utf-8"))
    else:
        payload["compiled"] = False
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record and compile SCBE action-map workflow telemetry.")
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT), help=f"Run root (default: {DEFAULT_RUN_ROOT})")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    def add_common_arguments(p: argparse.ArgumentParser, *, require_summary: bool = True) -> None:
        p.add_argument("--summary", required=require_summary, default="", help="Human summary for this event.")
        p.add_argument("--operator", default="agent.codex")
        p.add_argument("--lane", default="terminal")
        p.add_argument("--tool", default="")
        p.add_argument("--command", dest="command_text", default="")
        p.add_argument("--next-action", default="")
        p.add_argument("--tag", action="append", default=[])
        p.add_argument("--skill", action="append", default=[])
        p.add_argument("--touched-layer", action="append", default=[])
        p.add_argument("--changed-file", action="append", default=[])
        p.add_argument("--proof", action="append", default=[])
        p.add_argument("--artifact", action="append", default=[])
        p.add_argument("--decision", action="append", default=[])
        p.add_argument("--inputs-json", default="")
        p.add_argument("--outputs-json", default="")
        p.add_argument("--metadata-json", default="")
        p.add_argument("--metrics-json", default="")

    start_p = sub.add_parser("start", help="Start a new action-map run")
    start_p.add_argument("--task", required=True)
    start_p.add_argument("--run-id", default="")
    add_common_arguments(start_p, require_summary=False)

    step_p = sub.add_parser("step", help="Append a step to an action-map run")
    step_p.add_argument("--run-id", required=True)
    step_p.add_argument("--status", default="in_progress")
    add_common_arguments(step_p)

    close_p = sub.add_parser("close", help="Close an action-map run")
    close_p.add_argument("--run-id", required=True)
    close_p.add_argument("--status", default="completed")
    add_common_arguments(close_p)

    build_p = sub.add_parser("build", help="Compile action-map artifacts and training rows")
    build_p.add_argument("--run-id", required=True)

    status_p = sub.add_parser("status", help="Show the latest action-map run or one specific run")
    status_p.add_argument("--run-id", default="")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_root = Path(args.run_root).expanduser()

    if args.subcommand == "start":
        result = start_run(
            run_root,
            task=args.task,
            run_id=args.run_id or None,
            summary=args.summary,
            operator=args.operator,
            lane=args.lane,
            tool=args.tool,
            command=args.command_text,
            next_action=args.next_action,
            tags=args.tag,
            skills=args.skill,
            touched_layers=args.touched_layer,
            changed_files=args.changed_file,
            proof=args.proof,
            artifacts=args.artifact,
            inputs=parse_json_object(args.inputs_json, "inputs_json"),
            outputs=parse_json_object(args.outputs_json, "outputs_json"),
            metadata=parse_json_object(args.metadata_json, "metadata_json"),
            metrics=parse_json_object(args.metrics_json, "metrics_json"),
            decisions=parse_decisions(args.decision),
        )
    elif args.subcommand == "step":
        result = append_step(
            run_root,
            run_id=args.run_id,
            summary=args.summary,
            status=args.status,
            operator=args.operator,
            lane=args.lane,
            tool=args.tool,
            command=args.command_text,
            next_action=args.next_action,
            tags=args.tag,
            skills=args.skill,
            touched_layers=args.touched_layer,
            changed_files=args.changed_file,
            proof=args.proof,
            artifacts=args.artifact,
            inputs=parse_json_object(args.inputs_json, "inputs_json"),
            outputs=parse_json_object(args.outputs_json, "outputs_json"),
            metadata=parse_json_object(args.metadata_json, "metadata_json"),
            metrics=parse_json_object(args.metrics_json, "metrics_json"),
            decisions=parse_decisions(args.decision),
        )
    elif args.subcommand == "close":
        result = close_run(
            run_root,
            run_id=args.run_id,
            summary=args.summary,
            status=args.status,
            operator=args.operator,
            lane=args.lane,
            tool=args.tool,
            command=args.command_text,
            next_action=args.next_action,
            tags=args.tag,
            skills=args.skill,
            touched_layers=args.touched_layer,
            changed_files=args.changed_file,
            proof=args.proof,
            artifacts=args.artifact,
            inputs=parse_json_object(args.inputs_json, "inputs_json"),
            outputs=parse_json_object(args.outputs_json, "outputs_json"),
            metadata=parse_json_object(args.metadata_json, "metadata_json"),
            metrics=parse_json_object(args.metrics_json, "metrics_json"),
            decisions=parse_decisions(args.decision),
        )
    elif args.subcommand == "build":
        result = build_action_map(run_root, args.run_id)
    else:
        result = status(run_root, args.run_id or None)

    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
