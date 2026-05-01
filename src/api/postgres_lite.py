"""Optional PostgreSQL connectivity for local / lite deployments.

Uses ``SCBE_POSTGRES_URL`` or standard ``DATABASE_URL`` when set (non-SQLite).
Docker: ``docker compose -f docker-compose.postgres-lite.yml up -d``
(default DSN port **5433**).

Billing and HYDRA defaults remain SQLite unless separately migrated.
"""

from __future__ import annotations

import os
import time
from typing import Any

from src.storage.context_beehive_schema import SCHEMA_VERSION as CONTEXT_BEEHIVE_SCHEMA_VERSION


def resolved_postgres_dsn() -> str | None:
    """Return DSN if Postgres is configured; skip sqlite: URLs."""

    for key in ("SCBE_POSTGRES_URL", "DATABASE_URL"):
        raw = os.getenv(key, "").strip()
        if not raw:
            continue
        if raw.lower().startswith("sqlite:"):
            continue
        return raw
    return None


def probe_postgres(*, dsn: str | None = None, timeout_s: float = 3.0) -> dict[str, Any]:
    """Ping database with ``SELECT 1``; never raises — for health endpoints."""

    use_dsn = (dsn or "").strip() or resolved_postgres_dsn()
    if not use_dsn:
        return {
            "configured": False,
            "reachable": False,
            "driver": None,
        }

    try:
        import psycopg
    except ImportError:
        return {
            "configured": True,
            "reachable": False,
            "driver": None,
            "error": "psycopg package not installed (pip install psycopg[binary])",
        }

    timeout_int = max(1, int(timeout_s))
    t0 = time.perf_counter()
    try:
        with psycopg.connect(use_dsn, connect_timeout=timeout_int) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
        if row is None or row[0] != 1:
            return {
                "configured": True,
                "reachable": False,
                "driver": "psycopg3",
                "error": "unexpected SELECT 1 result",
            }
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "configured": True,
            "reachable": True,
            "driver": "psycopg3",
            "latency_ms": elapsed_ms,
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "driver": "psycopg3",
            "error": str(exc)[:500],
        }


def health_postgres_payload(timeout_s: float = 3.0) -> dict[str, Any]:
    """Stable fragment merged into ``/health`` responses."""

    payload = probe_postgres(timeout_s=timeout_s)
    payload["optional_lanes"] = {
        "context_beehive": {
            "schema_version": CONTEXT_BEEHIVE_SCHEMA_VERSION,
            "tables": ["scbe_context_cells", "scbe_context_edges"],
            "stores": "hashes, artifact pointers, semantic overlays, and positive/negative retrieval partitions",
        }
    }
    return payload
