#!/usr/bin/env python3
"""Lease-based AI dispatch spine for SCBE multi-agent work."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "dispatch_spine"
DB_PATH = ARTIFACT_DIR / "dispatch.db"
REGISTRY_PATH = REPO_ROOT / "config" / "system" / "advanced_ai_dispatch_capabilities.json"
BROWSER_DISPATCHER_PATH = REPO_ROOT / "scripts" / "system" / "browser_chain_dispatcher.py"

TASK_STATES = {"queued", "running", "completed", "failed"}


@dataclass
class TaskRecord:
    task_id: str
    title: str
    goal: str
    capability: str
    priority: int
    status: str
    owner_role: str
    requested_by: str
    write_scope: list[str]
    dependencies: list[str]
    payload: dict[str, Any]
    route: dict[str, Any]
    notes: str
    evidence_required: bool
    created_at: str
    updated_at: str
    lease_owner: str | None
    lease_expires_at: str | None
    result_summary: str | None
    failure_reason: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_task_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"task-{stamp}-{uuid.uuid4().hex[:6]}"


def ensure_artifact_dir() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def load_json_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("JSON payload must decode to an object.")
    return value


def parse_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_registry() -> dict[str, dict[str, Any]]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Capability registry must be a JSON object.")
    return data


def load_module(module_path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def enrich_browser_route(capability: str, payload: dict[str, Any], default_task_type: str) -> dict[str, Any]:
    if not capability.startswith("browser."):
        return {}
    domain = str(payload.get("domain", "")).strip()
    if not domain:
        return {}
    dispatcher_module = load_module(BROWSER_DISPATCHER_PATH, "advanced_ai_browser_dispatcher")
    dispatcher = dispatcher_module.BrowserChainDispatcher()
    for tentacle in dispatcher_module.build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    task_type = str(payload.get("task_type", "")).strip() or default_task_type
    return dispatcher.assign_task(domain, task_type, payload)


def connect_db() -> sqlite3.Connection:
    ensure_artifact_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            goal TEXT NOT NULL,
            capability TEXT NOT NULL,
            priority INTEGER NOT NULL,
            status TEXT NOT NULL,
            owner_role TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            write_scope_json TEXT NOT NULL,
            dependencies_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            route_json TEXT NOT NULL,
            notes TEXT NOT NULL,
            evidence_required INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            lease_owner TEXT,
            lease_expires_at TEXT,
            result_summary TEXT,
            failure_reason TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(task_id)
        )
        """
    )
    return conn


def row_to_task(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(
        task_id=row["task_id"],
        title=row["title"],
        goal=row["goal"],
        capability=row["capability"],
        priority=row["priority"],
        status=row["status"],
        owner_role=row["owner_role"],
        requested_by=row["requested_by"],
        write_scope=json.loads(row["write_scope_json"]),
        dependencies=json.loads(row["dependencies_json"]),
        payload=json.loads(row["payload_json"]),
        route=json.loads(row["route_json"]),
        notes=row["notes"],
        evidence_required=bool(row["evidence_required"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        lease_owner=row["lease_owner"],
        lease_expires_at=row["lease_expires_at"],
        result_summary=row["result_summary"],
        failure_reason=row["failure_reason"],
    )


def task_to_dict(task: TaskRecord) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "goal": task.goal,
        "capability": task.capability,
        "priority": task.priority,
        "status": task.status,
        "owner_role": task.owner_role,
        "requested_by": task.requested_by,
        "write_scope": task.write_scope,
        "dependencies": task.dependencies,
        "payload": task.payload,
        "route": task.route,
        "notes": task.notes,
        "evidence_required": task.evidence_required,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "lease_owner": task.lease_owner,
        "lease_expires_at": task.lease_expires_at,
        "result_summary": task.result_summary,
        "failure_reason": task.failure_reason,
    }


def emit_event(
    conn: sqlite3.Connection,
    task_id: str,
    event_type: str,
    actor: str,
    payload: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO task_events (task_id, event_type, actor, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (task_id, event_type, actor, json.dumps(payload or {}, sort_keys=True), utc_now()),
    )


def dependencies_complete(conn: sqlite3.Connection, dependencies: list[str]) -> bool:
    if not dependencies:
        return True
    rows = conn.execute(
        f"SELECT task_id, status FROM tasks WHERE task_id IN ({','.join('?' for _ in dependencies)})",
        dependencies,
    ).fetchall()
    state = {row["task_id"]: row["status"] for row in rows}
    return all(state.get(task_id) == "completed" for task_id in dependencies)


def command_init(_: argparse.Namespace) -> dict[str, Any]:
    conn = connect_db()
    conn.close()
    return {
        "ok": True,
        "db_path": str(DB_PATH),
        "registry_path": str(REGISTRY_PATH),
    }


def command_enqueue(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_registry()
    capability_meta = registry.get(args.capability)
    if capability_meta is None:
        raise ValueError(f"Unknown capability: {args.capability}")

    conn = connect_db()
    now = utc_now()
    task_id = build_task_id()
    payload = load_json_dict(args.payload)
    route = enrich_browser_route(
        args.capability,
        payload,
        str(capability_meta.get("default_task_type", "navigate")),
    )
    priority = args.priority if args.priority is not None else int(capability_meta.get("default_priority", 50))
    owner_role = args.owner_role or str(capability_meta.get("owner_role", "agent.worker"))

    conn.execute(
        """
        INSERT INTO tasks (
            task_id, title, goal, capability, priority, status, owner_role, requested_by,
            write_scope_json, dependencies_json, payload_json, route_json, notes,
            evidence_required, created_at, updated_at, lease_owner, lease_expires_at,
            result_summary, failure_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            args.title,
            args.goal,
            args.capability,
            priority,
            "queued",
            owner_role,
            args.requested_by,
            json.dumps(parse_csv(args.write_scope)),
            json.dumps(args.dependency or []),
            json.dumps(payload, sort_keys=True),
            json.dumps(route, sort_keys=True),
            args.notes or "",
            1 if args.evidence_required else 0,
            now,
            now,
            None,
            None,
            None,
            None,
        ),
    )
    emit_event(
        conn,
        task_id,
        "enqueue",
        args.requested_by,
        {
            "capability": args.capability,
            "priority": priority,
            "write_scope": parse_csv(args.write_scope),
        },
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    return {"ok": True, "task": task_to_dict(row_to_task(row))}


def command_claim(args: argparse.Namespace) -> dict[str, Any]:
    worker_capabilities = set(args.capability or [])
    conn = connect_db()
    conn.execute("BEGIN IMMEDIATE")
    rows = conn.execute(
        """
        SELECT * FROM tasks
        WHERE status = 'queued'
        ORDER BY priority DESC, created_at ASC
        """
    ).fetchall()

    selected: sqlite3.Row | None = None
    for row in rows:
        capability = row["capability"]
        dependencies = json.loads(row["dependencies_json"])
        if worker_capabilities and capability not in worker_capabilities:
            continue
        if not dependencies_complete(conn, dependencies):
            continue
        selected = row
        break

    if selected is None:
        conn.commit()
        conn.close()
        return {"ok": True, "task": None, "reason": "no_matching_queued_task"}

    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=args.lease_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_at = utc_now()
    conn.execute(
        """
        UPDATE tasks
        SET status = 'running', lease_owner = ?, lease_expires_at = ?, updated_at = ?
        WHERE task_id = ?
        """,
        (args.worker_id, expires_at, updated_at, selected["task_id"]),
    )
    emit_event(
        conn,
        selected["task_id"],
        "claim",
        args.worker_id,
        {"lease_minutes": args.lease_minutes, "lease_expires_at": expires_at},
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (selected["task_id"],)).fetchone()
    conn.close()
    return {"ok": True, "task": task_to_dict(row_to_task(row))}


def command_complete(args: argparse.Namespace) -> dict[str, Any]:
    conn = connect_db()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone()
    if row is None:
        raise ValueError(f"Unknown task_id: {args.task_id}")
    if row["lease_owner"] not in (None, args.worker_id):
        raise ValueError(f"Task {args.task_id} is leased to {row['lease_owner']}, not {args.worker_id}")

    conn.execute(
        """
        UPDATE tasks
        SET status = 'completed',
            updated_at = ?,
            lease_owner = NULL,
            lease_expires_at = NULL,
            result_summary = ?,
            failure_reason = NULL
        WHERE task_id = ?
        """,
        (utc_now(), args.summary, args.task_id),
    )
    emit_event(conn, args.task_id, "complete", args.worker_id, {"summary": args.summary})
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone()
    conn.close()
    return {"ok": True, "task": task_to_dict(row_to_task(updated))}


def command_fail(args: argparse.Namespace) -> dict[str, Any]:
    conn = connect_db()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone()
    if row is None:
        raise ValueError(f"Unknown task_id: {args.task_id}")
    if row["lease_owner"] not in (None, args.worker_id):
        raise ValueError(f"Task {args.task_id} is leased to {row['lease_owner']}, not {args.worker_id}")

    conn.execute(
        """
        UPDATE tasks
        SET status = 'failed',
            updated_at = ?,
            lease_owner = NULL,
            lease_expires_at = NULL,
            failure_reason = ?
        WHERE task_id = ?
        """,
        (utc_now(), args.reason, args.task_id),
    )
    emit_event(conn, args.task_id, "fail", args.worker_id, {"reason": args.reason})
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone()
    conn.close()
    return {"ok": True, "task": task_to_dict(row_to_task(updated))}


def command_release_stale(args: argparse.Namespace) -> dict[str, Any]:
    threshold = (
        datetime.now(timezone.utc) - timedelta(minutes=args.max_age_minutes)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = connect_db()
    rows = conn.execute(
        """
        SELECT * FROM tasks
        WHERE status = 'running'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at < ?
        """,
        (threshold,),
    ).fetchall()
    released: list[str] = []
    for row in rows:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'queued',
                updated_at = ?,
                lease_owner = NULL,
                lease_expires_at = NULL
            WHERE task_id = ?
            """,
            (utc_now(), row["task_id"]),
        )
        emit_event(conn, row["task_id"], "release_stale", args.actor, {"previous_owner": row["lease_owner"]})
        released.append(row["task_id"])
    conn.commit()
    conn.close()
    return {"ok": True, "released": released, "count": len(released)}


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    conn = connect_db()
    counts = {
        row["status"]: row["count"]
        for row in conn.execute(
            "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"
        ).fetchall()
    }
    for state in TASK_STATES:
        counts.setdefault(state, 0)
    tasks = [
        task_to_dict(row_to_task(row))
        for row in conn.execute(
            """
            SELECT * FROM tasks
            ORDER BY
                CASE status
                    WHEN 'running' THEN 0
                    WHEN 'queued' THEN 1
                    WHEN 'failed' THEN 2
                    ELSE 3
                END,
                priority DESC,
                created_at ASC
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()
    ]
    conn.close()
    return {"ok": True, "db_path": str(DB_PATH), "counts": counts, "tasks": tasks}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Initialize the dispatch database.")
    init_parser.set_defaults(handler=command_init)

    enqueue_parser = sub.add_parser("enqueue", help="Queue a new dispatch task.")
    enqueue_parser.add_argument("--title", required=True)
    enqueue_parser.add_argument("--goal", required=True)
    enqueue_parser.add_argument("--capability", required=True)
    enqueue_parser.add_argument("--priority", type=int)
    enqueue_parser.add_argument("--owner-role")
    enqueue_parser.add_argument("--requested-by", default="agent.unknown")
    enqueue_parser.add_argument("--write-scope", default="")
    enqueue_parser.add_argument("--dependency", action="append")
    enqueue_parser.add_argument("--payload", help="JSON object payload.")
    enqueue_parser.add_argument("--notes", default="")
    enqueue_parser.add_argument("--evidence-required", action="store_true")
    enqueue_parser.set_defaults(handler=command_enqueue)

    claim_parser = sub.add_parser("claim", help="Claim the next matching queued task.")
    claim_parser.add_argument("--worker-id", required=True)
    claim_parser.add_argument("--capability", action="append")
    claim_parser.add_argument("--lease-minutes", type=int, default=45)
    claim_parser.set_defaults(handler=command_claim)

    complete_parser = sub.add_parser("complete", help="Mark a task as completed.")
    complete_parser.add_argument("--task-id", required=True)
    complete_parser.add_argument("--worker-id", required=True)
    complete_parser.add_argument("--summary", required=True)
    complete_parser.set_defaults(handler=command_complete)

    fail_parser = sub.add_parser("fail", help="Mark a task as failed.")
    fail_parser.add_argument("--task-id", required=True)
    fail_parser.add_argument("--worker-id", required=True)
    fail_parser.add_argument("--reason", required=True)
    fail_parser.set_defaults(handler=command_fail)

    release_parser = sub.add_parser("release-stale", help="Requeue expired running tasks.")
    release_parser.add_argument("--max-age-minutes", type=int, default=45)
    release_parser.add_argument("--actor", default="agent.dispatch")
    release_parser.set_defaults(handler=command_release_stale)

    status_parser = sub.add_parser("status", help="Show dispatch queue state.")
    status_parser.add_argument("--limit", type=int, default=20)
    status_parser.set_defaults(handler=command_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.handler(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
