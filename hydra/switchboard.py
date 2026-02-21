"""
HYDRA Switchboard
=================

Lease-based task queue + role channels for coordinated multi-agent execution.
Backed by SQLite for simple remote deployment and auditable state transitions.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _ts() -> int:
    return int(time.time())


class Switchboard:
    """Task switchboard with lease locks and role-scoped channels."""

    def __init__(self, db_path: str = "artifacts/hydra/switchboard.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                  task_id TEXT PRIMARY KEY,
                  role TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  status TEXT NOT NULL,
                  priority INTEGER NOT NULL DEFAULT 100,
                  dedupe_key TEXT,
                  lease_owner TEXT,
                  lease_expires_at INTEGER,
                  attempts INTEGER NOT NULL DEFAULT 0,
                  result_json TEXT,
                  error_text TEXT,
                  created_at INTEGER NOT NULL,
                  updated_at INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_role_status_priority
                  ON tasks(role, status, priority, created_at);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_dedupe_live
                  ON tasks(dedupe_key)
                  WHERE dedupe_key IS NOT NULL AND status IN ('queued', 'leased');

                CREATE TABLE IF NOT EXISTS role_messages (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  channel TEXT NOT NULL,
                  sender TEXT NOT NULL,
                  message_json TEXT NOT NULL,
                  created_at INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_role_messages_channel_id
                  ON role_messages(channel, id);
                """
            )

    def enqueue_task(
        self,
        role: str,
        payload: Dict[str, Any],
        dedupe_key: Optional[str] = None,
        priority: int = 100,
    ) -> Dict[str, Any]:
        role = str(role).strip().lower()
        if not role:
            raise ValueError("role is required")
        now = _ts()
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if dedupe_key:
                row = conn.execute(
                    """
                    SELECT task_id, status FROM tasks
                    WHERE dedupe_key = ? AND status IN ('queued','leased')
                    ORDER BY created_at ASC LIMIT 1
                    """,
                    (dedupe_key,),
                ).fetchone()
                if row:
                    conn.execute("COMMIT")
                    return {
                        "task_id": str(row["task_id"]),
                        "role": role,
                        "status": str(row["status"]),
                        "deduped": True,
                    }
            conn.execute(
                """
                INSERT INTO tasks(
                  task_id, role, payload_json, status, priority, dedupe_key,
                  lease_owner, lease_expires_at, attempts, result_json, error_text,
                  created_at, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, ?, NULL, NULL, 0, NULL, NULL, ?, ?)
                """,
                (task_id, role, payload_json, int(priority), dedupe_key, now, now),
            )
            conn.execute("COMMIT")
        return {"task_id": task_id, "role": role, "status": "queued", "deduped": False}

    def claim_task(
        self,
        worker_id: str,
        roles: Iterable[str],
        lease_seconds: int = 60,
    ) -> Optional[Dict[str, Any]]:
        role_list = [str(r).strip().lower() for r in roles if str(r).strip()]
        if not role_list:
            return None
        now = _ts()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE tasks
                SET status='queued', lease_owner=NULL, lease_expires_at=NULL, updated_at=?
                WHERE status='leased' AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?
                """,
                (now, now),
            )
            placeholders = ",".join(["?"] * len(role_list))
            row = conn.execute(
                f"""
                SELECT task_id FROM tasks
                WHERE status='queued' AND role IN ({placeholders})
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                """,
                tuple(role_list),
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            task_id = str(row["task_id"])
            expires = now + max(1, int(lease_seconds))
            conn.execute(
                """
                UPDATE tasks
                SET status='leased',
                    lease_owner=?,
                    lease_expires_at=?,
                    attempts=attempts+1,
                    updated_at=?
                WHERE task_id=?
                """,
                (worker_id, expires, now, task_id),
            )
            full = conn.execute(
                """
                SELECT * FROM tasks WHERE task_id=?
                """,
                (task_id,),
            ).fetchone()
            conn.execute("COMMIT")
        if not full:
            return None
        payload = {}
        try:
            payload = json.loads(str(full["payload_json"]))
        except Exception:
            payload = {}
        return {
            "task_id": str(full["task_id"]),
            "role": str(full["role"]),
            "payload": payload,
            "status": str(full["status"]),
            "lease_owner": str(full["lease_owner"] or ""),
            "lease_expires_at": int(full["lease_expires_at"] or 0),
            "attempts": int(full["attempts"] or 0),
            "priority": int(full["priority"] or 100),
        }

    def renew_lease(self, task_id: str, worker_id: str, lease_seconds: int = 60) -> bool:
        now = _ts()
        expires = now + max(1, int(lease_seconds))
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE tasks
                SET lease_expires_at=?, updated_at=?
                WHERE task_id=? AND status='leased' AND lease_owner=?
                """,
                (expires, now, task_id, worker_id),
            )
            return cur.rowcount > 0

    def complete_task(self, task_id: str, worker_id: str, result: Dict[str, Any]) -> bool:
        now = _ts()
        result_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE tasks
                SET status='done',
                    result_json=?,
                    error_text=NULL,
                    lease_owner=NULL,
                    lease_expires_at=NULL,
                    updated_at=?
                WHERE task_id=? AND status='leased' AND lease_owner=?
                """,
                (result_json, now, task_id, worker_id),
            )
            return cur.rowcount > 0

    def fail_task(
        self,
        task_id: str,
        worker_id: str,
        error_text: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        now = _ts()
        result_json = json.dumps(result, sort_keys=True, separators=(",", ":")) if result else None
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE tasks
                SET status='failed',
                    result_json=?,
                    error_text=?,
                    lease_owner=NULL,
                    lease_expires_at=NULL,
                    updated_at=?
                WHERE task_id=? AND status='leased' AND lease_owner=?
                """,
                (result_json, str(error_text), now, task_id, worker_id),
            )
            return cur.rowcount > 0

    def post_role_message(self, channel: str, sender: str, message: Dict[str, Any]) -> int:
        now = _ts()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO role_messages(channel, sender, message_json, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (str(channel), str(sender), json.dumps(message, sort_keys=True), now),
            )
            return int(cur.lastrowid)

    def get_role_messages(self, channel: str, since_id: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, channel, sender, message_json, created_at
                FROM role_messages
                WHERE channel=? AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (str(channel), int(since_id), int(limit)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            msg: Dict[str, Any]
            try:
                msg = json.loads(str(r["message_json"]))
            except Exception:
                msg = {"raw": str(r["message_json"])}
            out.append(
                {
                    "id": int(r["id"]),
                    "channel": str(r["channel"]),
                    "sender": str(r["sender"]),
                    "message": msg,
                    "created_at": int(r["created_at"]),
                }
            )
        return out

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            by_status_rows = conn.execute(
                "SELECT status, COUNT(*) AS c FROM tasks GROUP BY status"
            ).fetchall()
            by_role_rows = conn.execute(
                "SELECT role, COUNT(*) AS c FROM tasks GROUP BY role"
            ).fetchall()
            leased_rows = conn.execute(
                "SELECT task_id, role, lease_owner, lease_expires_at FROM tasks WHERE status='leased' ORDER BY updated_at DESC LIMIT 50"
            ).fetchall()
            msg_count = conn.execute(
                "SELECT COUNT(*) AS c FROM role_messages"
            ).fetchone()

        return {
            "db_path": self.db_path,
            "by_status": {str(r["status"]): int(r["c"]) for r in by_status_rows},
            "by_role": {str(r["role"]): int(r["c"]) for r in by_role_rows},
            "leased": [
                {
                    "task_id": str(r["task_id"]),
                    "role": str(r["role"]),
                    "lease_owner": str(r["lease_owner"] or ""),
                    "lease_expires_at": int(r["lease_expires_at"] or 0),
                }
                for r in leased_rows
            ],
            "role_message_count": int(msg_count["c"] if msg_count else 0),
        }

