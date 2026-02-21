"""
Polly Pad Runtime Store
=======================

Auditable headless runtime for pad lifecycle:
- active pad records
- compact state snapshots
- exit logs on decommission
- cousin takeover lineage
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def _ts() -> int:
    return int(time.time())


class PollyPadStore:
    """SQLite-backed Polly Pad lifecycle store."""

    def __init__(self, db_path: str = "artifacts/hydra/polly_pad/pads.db"):
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
                CREATE TABLE IF NOT EXISTS pads (
                  pad_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  parent_pad_id TEXT,
                  metadata_json TEXT,
                  last_compact_json TEXT,
                  last_exit_log_json TEXT,
                  created_at INTEGER NOT NULL,
                  updated_at INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_pads_status ON pads(status);

                CREATE TABLE IF NOT EXISTS pad_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pad_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  created_at INTEGER NOT NULL,
                  FOREIGN KEY(pad_id) REFERENCES pads(pad_id)
                );

                CREATE INDEX IF NOT EXISTS idx_pad_events_pad_id
                  ON pad_events(pad_id, id);

                CREATE TABLE IF NOT EXISTS recoveries (
                  failed_task_id TEXT PRIMARY KEY,
                  source_pad_id TEXT NOT NULL,
                  cousin_pad_id TEXT NOT NULL,
                  takeover_task_id TEXT NOT NULL,
                  created_at INTEGER NOT NULL
                );
                """
            )

    def ensure_pad(self, pad_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        now = _ts()
        meta_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            row = conn.execute(
                "SELECT pad_id FROM pads WHERE pad_id=? LIMIT 1",
                (pad_id,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE pads
                    SET metadata_json=?, updated_at=?
                    WHERE pad_id=?
                    """,
                    (meta_json, now, pad_id),
                )
                return pad_id

            conn.execute(
                """
                INSERT INTO pads(
                  pad_id, status, parent_pad_id, metadata_json,
                  last_compact_json, last_exit_log_json, created_at, updated_at
                ) VALUES (?, 'active', NULL, ?, NULL, NULL, ?, ?)
                """,
                (pad_id, meta_json, now, now),
            )
        return pad_id

    def create_pad(self, parent_pad_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        pad_id = f"pad-{uuid.uuid4().hex[:12]}"
        now = _ts()
        meta_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pads(
                  pad_id, status, parent_pad_id, metadata_json,
                  last_compact_json, last_exit_log_json, created_at, updated_at
                ) VALUES (?, 'active', ?, ?, NULL, NULL, ?, ?)
                """,
                (pad_id, parent_pad_id, meta_json, now, now),
            )
        return pad_id

    def log_event(self, pad_id: str, event_type: str, payload: Dict[str, Any]) -> int:
        now = _ts()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pad_events(pad_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (pad_id, str(event_type), payload_json, now),
            )
            conn.execute(
                """
                UPDATE pads SET updated_at=? WHERE pad_id=?
                """,
                (now, pad_id),
            )
            return int(cur.lastrowid)

    def write_compact(self, pad_id: str, compact: Dict[str, Any]) -> None:
        now = _ts()
        compact_json = json.dumps(compact, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pads
                SET last_compact_json=?, updated_at=?
                WHERE pad_id=?
                """,
                (compact_json, now, pad_id),
            )

    def decommission(self, pad_id: str, reason: str, exit_log: Dict[str, Any]) -> None:
        now = _ts()
        exit_log_json = json.dumps(exit_log, sort_keys=True, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pads
                SET status='decommissioned',
                    last_exit_log_json=?,
                    updated_at=?
                WHERE pad_id=?
                """,
                (exit_log_json, now, pad_id),
            )
        self.log_event(
            pad_id,
            "decommissioned",
            {"reason": reason, "exit_log": exit_log},
        )

    def spawn_cousin(self, source_pad_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        source = self.get_pad(source_pad_id)
        if not source:
            raise ValueError(f"source pad not found: {source_pad_id}")

        source_compact = source.get("last_compact") or {}
        cousin_meta = dict(metadata or {})
        cousin_meta["spawn_reason"] = reason
        cousin_meta["inherited_from"] = source_pad_id
        cousin_meta["inherited_compact"] = source_compact

        cousin_id = self.create_pad(parent_pad_id=source_pad_id, metadata=cousin_meta)
        self.log_event(
            cousin_id,
            "cousin_spawned",
            {
                "source_pad_id": source_pad_id,
                "reason": reason,
                "inherited_compact": source_compact,
            },
        )
        return cousin_id

    def has_recovery(self, failed_task_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM recoveries WHERE failed_task_id=? LIMIT 1",
                (failed_task_id,),
            ).fetchone()
            return row is not None

    def record_recovery(
        self,
        failed_task_id: str,
        source_pad_id: str,
        cousin_pad_id: str,
        takeover_task_id: str,
    ) -> None:
        now = _ts()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO recoveries(
                  failed_task_id, source_pad_id, cousin_pad_id, takeover_task_id, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (failed_task_id, source_pad_id, cousin_pad_id, takeover_task_id, now),
            )

    def get_pad(self, pad_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM pads WHERE pad_id=? LIMIT 1
                """,
                (pad_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "pad_id": str(row["pad_id"]),
            "status": str(row["status"]),
            "parent_pad_id": str(row["parent_pad_id"]) if row["parent_pad_id"] else None,
            "metadata": json.loads(str(row["metadata_json"])) if row["metadata_json"] else {},
            "last_compact": json.loads(str(row["last_compact_json"])) if row["last_compact_json"] else None,
            "last_exit_log": json.loads(str(row["last_exit_log_json"])) if row["last_exit_log_json"] else None,
            "created_at": int(row["created_at"]),
            "updated_at": int(row["updated_at"]),
        }

    def list_events(self, pad_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, event_type, payload_json, created_at
                FROM pad_events
                WHERE pad_id=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (pad_id, int(limit)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": int(r["id"]),
                    "event_type": str(r["event_type"]),
                    "payload": json.loads(str(r["payload_json"])) if r["payload_json"] else {},
                    "created_at": int(r["created_at"]),
                }
            )
        return out
