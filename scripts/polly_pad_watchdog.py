#!/usr/bin/env python3
"""
Polly Pad Watchdog
==================

Observes failed switchboard tasks, decommissions impacted pads, and enqueues
"cousin takeover" tasks with inherited compact + exit log.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hydra.polly_pad import PollyPadStore
from hydra.switchboard import Switchboard


def _json_load(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"value": value}
    except Exception:  # noqa: BLE001
        return {"raw": str(raw)}


def _read_failed_tasks(db_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT task_id, role, payload_json, status, priority, attempts, result_json, error_text, created_at, updated_at
            FROM tasks
            WHERE status='failed'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append({k: row[k] for k in row.keys()})
    return out


def _extract_pad_id(role: str, payload: Dict[str, Any]) -> str:
    params = payload.get("params", {}) if isinstance(payload.get("params"), dict) else {}
    explicit = str(params.get("pad_id", "")).strip()
    if explicit:
        return explicit
    return f"pad-{role}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Polly Pad watchdog")
    parser.add_argument("--switchboard-db", default="artifacts/hydra/headless_ide/switchboard.db")
    parser.add_argument("--pad-db", default="artifacts/hydra/polly_pad/pads.db")
    parser.add_argument("--scan-limit", type=int, default=50)
    args = parser.parse_args()

    switchboard_db = str((ROOT / args.switchboard_db).resolve()) if not Path(args.switchboard_db).is_absolute() else args.switchboard_db
    pad_db = str((ROOT / args.pad_db).resolve()) if not Path(args.pad_db).is_absolute() else args.pad_db

    board = Switchboard(switchboard_db)
    pads = PollyPadStore(pad_db)

    failed = _read_failed_tasks(switchboard_db, limit=args.scan_limit)
    recoveries: List[Dict[str, Any]] = []

    for row in failed:
        failed_task_id = str(row.get("task_id", ""))
        if not failed_task_id or pads.has_recovery(failed_task_id):
            continue

        role = str(row.get("role", "default")).strip().lower() or "default"
        payload = _json_load(row.get("payload_json"))
        result = _json_load(row.get("result_json"))
        error_text = str(row.get("error_text", "") or "")

        source_pad_id = _extract_pad_id(role, payload)
        pads.ensure_pad(source_pad_id, metadata={"role": role, "origin": "watchdog"})

        compact = {
            "failed_task_id": failed_task_id,
            "role": role,
            "payload": payload,
            "result": result,
            "error_text": error_text,
            "attempts": int(row.get("attempts", 0) or 0),
            "updated_at": int(row.get("updated_at", 0) or 0),
        }
        pads.write_compact(source_pad_id, compact)

        exit_log = {
            "reason": "task_failed",
            "failed_task_id": failed_task_id,
            "error_text": error_text,
            "result_excerpt": str(result)[:1000],
        }
        pads.decommission(source_pad_id, reason="task_failed", exit_log=exit_log)

        cousin_id = pads.spawn_cousin(
            source_pad_id,
            reason="takeover_after_failure",
            metadata={"role": role},
        )

        takeover_payload = dict(payload)
        params = takeover_payload.get("params", {}) if isinstance(takeover_payload.get("params"), dict) else {}
        params["pad_id"] = cousin_id
        params["handoff_compact"] = compact
        params["handoff_exit_log"] = exit_log
        takeover_payload["params"] = params

        takeover = board.enqueue_task(
            role=role,
            payload=takeover_payload,
            dedupe_key=f"cousin:{failed_task_id}",
            priority=max(1, int(row.get("priority", 100) or 100) - 10),
        )

        pads.record_recovery(
            failed_task_id=failed_task_id,
            source_pad_id=source_pad_id,
            cousin_pad_id=cousin_id,
            takeover_task_id=str(takeover.get("task_id", "")),
        )
        pads.log_event(
            cousin_id,
            "takeover_enqueued",
            {
                "from_failed_task": failed_task_id,
                "takeover_task_id": takeover.get("task_id"),
                "role": role,
            },
        )

        recoveries.append(
            {
                "failed_task_id": failed_task_id,
                "source_pad_id": source_pad_id,
                "cousin_pad_id": cousin_id,
                "takeover_task_id": takeover.get("task_id"),
            }
        )

    output = {
        "switchboard_db": switchboard_db,
        "pad_db": pad_db,
        "failed_scanned": len(failed),
        "recoveries_created": len(recoveries),
        "recoveries": recoveries,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
