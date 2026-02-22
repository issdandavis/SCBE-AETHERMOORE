"""Sacred Egg Registry — Persistent Egg Lifecycle Management

SQLite-backed registry for Sacred Egg storage, status tracking,
and ritual audit logging. Every egg has a lifecycle:

    SEALED → HATCHED (success) or EXPIRED (TTL exceeded)

Every hatch attempt (success or failure) is logged to the ritual
audit trail. No information about failure reasons is stored
(oracle safety).

Integrates:
  - sacred_egg_integrator: SacredEgg, SacredEggIntegrator
  - cli_toolkit: CrossTokenizer infrastructure

@layer Layer 12, Layer 13
@component Sacred Egg Registry
@version 1.0.0
@patent USPTO #63/961,403
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.symphonic_cipher.scbe_aethermoore.sacred_egg_integrator import (
    SacredEgg,
    SacredEggIntegrator,
    HatchResult,
)

# Default database path
_DEFAULT_DB = os.path.join(
    os.path.expanduser("~"), ".scbe", "sacred_eggs.db"
)

# Egg statuses
SEALED = "SEALED"
HATCHED = "HATCHED"
EXPIRED = "EXPIRED"


class SacredEggRegistry:
    """SQLite-backed Sacred Egg lifecycle manager.

    Usage:
        registry = SacredEggRegistry()
        registry.register(egg, ttl_seconds=3600)
        egg = registry.get("abc123deadbeef")
        registry.log_attempt("abc123deadbeef", success=False, tongue="DR")
        registry.mark_hatched("abc123deadbeef")
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _DEFAULT_DB
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS eggs (
                egg_id          TEXT PRIMARY KEY,
                primary_tongue  TEXT NOT NULL,
                glyph           TEXT NOT NULL,
                hatch_condition TEXT NOT NULL,
                yolk_ct         TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'SEALED',
                created_at      REAL NOT NULL,
                ttl_seconds     INTEGER DEFAULT 0,
                hatched_at      REAL,
                hatched_by      TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ritual_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                egg_id          TEXT NOT NULL,
                timestamp       REAL NOT NULL,
                success         INTEGER NOT NULL,
                agent_tongue    TEXT,
                ritual_mode     TEXT,
                FOREIGN KEY (egg_id) REFERENCES eggs(egg_id)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_ritual_egg
            ON ritual_log(egg_id)
        """)
        self._conn.commit()

    def register(self, egg: SacredEgg, ttl_seconds: int = 0) -> str:
        """Store a sealed egg in the registry.

        Args:
            egg: The Sacred Egg to register
            ttl_seconds: Time-to-live in seconds (0 = no expiry)

        Returns:
            The egg_id
        """
        c = self._conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO eggs
               (egg_id, primary_tongue, glyph, hatch_condition,
                yolk_ct, status, created_at, ttl_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                egg.egg_id,
                egg.primary_tongue,
                egg.glyph,
                json.dumps(egg.hatch_condition),
                json.dumps(egg.yolk_ct),
                SEALED,
                time.time(),
                ttl_seconds,
            ),
        )
        self._conn.commit()
        return egg.egg_id

    def get(self, egg_id: str) -> Optional[SacredEgg]:
        """Retrieve an egg by ID. Returns None if not found or expired."""
        c = self._conn.cursor()
        c.execute("SELECT * FROM eggs WHERE egg_id = ?", (egg_id,))
        row = c.fetchone()
        if row is None:
            return None

        # Check expiry
        if row["ttl_seconds"] > 0:
            if time.time() - row["created_at"] > row["ttl_seconds"]:
                self._expire(egg_id)
                return None

        return SacredEgg(
            egg_id=row["egg_id"],
            primary_tongue=row["primary_tongue"],
            glyph=row["glyph"],
            hatch_condition=json.loads(row["hatch_condition"]),
            yolk_ct=json.loads(row["yolk_ct"]),
        )

    def get_status(self, egg_id: str) -> Optional[str]:
        """Get current status of an egg (SEALED/HATCHED/EXPIRED)."""
        c = self._conn.cursor()
        c.execute("SELECT status, created_at, ttl_seconds FROM eggs WHERE egg_id = ?", (egg_id,))
        row = c.fetchone()
        if row is None:
            return None
        if row["status"] == SEALED and row["ttl_seconds"] > 0:
            if time.time() - row["created_at"] > row["ttl_seconds"]:
                self._expire(egg_id)
                return EXPIRED
        return row["status"]

    def mark_hatched(self, egg_id: str, hatched_by: str = ""):
        """Mark an egg as successfully hatched."""
        c = self._conn.cursor()
        c.execute(
            "UPDATE eggs SET status = ?, hatched_at = ?, hatched_by = ? WHERE egg_id = ?",
            (HATCHED, time.time(), hatched_by, egg_id),
        )
        self._conn.commit()

    def _expire(self, egg_id: str):
        c = self._conn.cursor()
        c.execute(
            "UPDATE eggs SET status = ? WHERE egg_id = ?",
            (EXPIRED, egg_id),
        )
        self._conn.commit()

    def log_attempt(
        self,
        egg_id: str,
        success: bool,
        agent_tongue: str = "",
        ritual_mode: str = "",
    ):
        """Log a hatch attempt to the ritual audit trail."""
        c = self._conn.cursor()
        c.execute(
            """INSERT INTO ritual_log
               (egg_id, timestamp, success, agent_tongue, ritual_mode)
               VALUES (?, ?, ?, ?, ?)""",
            (egg_id, time.time(), int(success), agent_tongue, ritual_mode),
        )
        self._conn.commit()

    def get_attempts(self, egg_id: str) -> List[dict]:
        """Get all hatch attempts for an egg."""
        c = self._conn.cursor()
        c.execute(
            "SELECT * FROM ritual_log WHERE egg_id = ? ORDER BY timestamp",
            (egg_id,),
        )
        return [dict(row) for row in c.fetchall()]

    def list_eggs(self, status: Optional[str] = None) -> List[dict]:
        """List all eggs, optionally filtered by status."""
        c = self._conn.cursor()
        if status:
            c.execute(
                "SELECT egg_id, primary_tongue, glyph, status, created_at FROM eggs WHERE status = ?",
                (status,),
            )
        else:
            c.execute(
                "SELECT egg_id, primary_tongue, glyph, status, created_at FROM eggs"
            )
        return [dict(row) for row in c.fetchall()]

    def expire_stale(self) -> int:
        """Expire all eggs past their TTL. Returns count expired."""
        now = time.time()
        c = self._conn.cursor()
        c.execute(
            """UPDATE eggs SET status = ?
               WHERE status = ? AND ttl_seconds > 0
               AND (created_at + ttl_seconds) < ?""",
            (EXPIRED, SEALED, now),
        )
        self._conn.commit()
        return c.rowcount

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
