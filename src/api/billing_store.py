"""Durable persistence for Stripe billing state (SQLite).

Survives API restarts: subscription customers, API keys, purchase log, webhook dedupe.

Environment:
- SCBE_BILLING_DB_PATH: optional absolute path to SQLite file.
  Default: ``<repo_root>/.scbe/billing.sqlite3``
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

LOGGER = logging.getLogger("scbe.billing_store")

_lock = threading.Lock()
_loaded = False

Row = Dict[str, Any]


def default_db_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".scbe" / "billing.sqlite3"


def resolved_db_path() -> Path:
    raw = os.getenv("SCBE_BILLING_DB_PATH", "").strip()
    if raw:
        return Path(raw)
    return default_db_path()


def _connect() -> sqlite3.Connection:
    path = resolved_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS billing_customers (
            customer_id TEXT PRIMARY KEY NOT NULL,
            record_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS billing_api_keys (
            api_key TEXT PRIMARY KEY NOT NULL,
            customer_id TEXT NOT NULL,
            record_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_billing_api_keys_customer
            ON billing_api_keys(customer_id);
        CREATE TABLE IF NOT EXISTS purchase_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            record_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_purchase_log_created ON purchase_log(created_at);
        CREATE TABLE IF NOT EXISTS processed_webhook_events (
            event_id TEXT PRIMARY KEY NOT NULL,
            received_at INTEGER NOT NULL
        );
        """)
    conn.commit()


def _with_conn(fn: Callable[[sqlite3.Connection], Any]) -> Any:
    with _lock:
        conn = _connect()
        try:
            init_schema(conn)
            return fn(conn)
        finally:
            conn.close()


def save_customer(customer_id: str, record: Row) -> None:
    if not customer_id:
        LOGGER.warning("save_customer skipped: empty customer_id")
        return
    payload = json.dumps(record, sort_keys=True)
    now = int(time.time())

    def _do(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO billing_customers (customer_id, record_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                record_json = excluded.record_json,
                updated_at = excluded.updated_at
            """,
            (customer_id, payload, now),
        )
        conn.commit()

    _with_conn(_do)


def save_api_key(api_key: str, customer_id: str, record: Row) -> None:
    if not api_key:
        return
    payload = json.dumps(record, sort_keys=True)
    now = int(time.time())

    def _do(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO billing_api_keys (api_key, customer_id, record_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(api_key) DO UPDATE SET
                customer_id = excluded.customer_id,
                record_json = excluded.record_json,
                updated_at = excluded.updated_at
            """,
            (api_key, customer_id, payload, now),
        )
        conn.commit()

    _with_conn(_do)


def remove_api_key_from_valid_auth(api_key: str) -> None:
    """Remove API key row (e.g. after subscription deletion)."""

    def _do(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM billing_api_keys WHERE api_key = ?", (api_key,))
        conn.commit()

    _with_conn(_do)


def append_purchase(record: Row) -> None:
    payload = json.dumps(record, sort_keys=True)
    session_id = str(record.get("session_id") or "")
    now = int(time.time())

    def _do(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO purchase_log (session_id, record_json, created_at)
            VALUES (?, ?, ?)
            """,
            (session_id or None, payload, now),
        )
        conn.commit()

    _with_conn(_do)


def try_claim_webhook_event(event_id: str) -> bool:
    """Return True if this event_id was newly recorded (should process)."""

    if not event_id:
        return True
    now = int(time.time())

    def _do(conn: sqlite3.Connection) -> bool:
        try:
            conn.execute(
                "INSERT INTO processed_webhook_events (event_id, received_at) VALUES (?, ?)",
                (event_id, now),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    return bool(_with_conn(_do))


def load_into_memory(
    billing_customers: Dict[str, Row],
    billing_api_keys: Dict[str, Row],
    purchase_log: List[Row],
    valid_api_keys: Dict[str, str],
    *,
    purchase_limit: int = 500,
) -> None:
    """Populate in-memory dicts and merge active billing keys into ``valid_api_keys``.

    Does not remove unrelated keys from ``valid_api_keys`` (for example env-configured keys).
    """

    def _do(conn: sqlite3.Connection) -> None:
        billing_customers.clear()
        billing_api_keys.clear()
        purchase_log.clear()

        for row in conn.execute("SELECT customer_id, record_json FROM billing_customers"):
            cid, js = row
            billing_customers[cid] = json.loads(js)

        for row in conn.execute("SELECT api_key, record_json FROM billing_api_keys"):
            key, js = row
            rec = json.loads(js)
            billing_api_keys[key] = rec
            label = str(rec.get("email") or rec.get("customer_id") or "stripe_billing")
            if rec.get("active") is True:
                valid_api_keys[key] = label
            else:
                valid_api_keys.pop(key, None)

        for row in conn.execute(
            """
            SELECT record_json FROM purchase_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (purchase_limit,),
        ):
            purchase_log.append(json.loads(row[0]))
        purchase_log.reverse()

    global _loaded
    with _lock:
        conn = _connect()
        try:
            init_schema(conn)
            _do(conn)
        finally:
            conn.close()
        _loaded = True


def ensure_loaded(
    billing_customers: Dict[str, Row],
    billing_api_keys: Dict[str, Row],
    purchase_log: List[Row],
    valid_api_keys: Dict[str, str],
) -> None:
    if _loaded:
        return
    load_into_memory(billing_customers, billing_api_keys, purchase_log, valid_api_keys)


def reset_loaded_flag_for_tests() -> None:
    global _loaded
    _loaded = False
