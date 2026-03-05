#!/usr/bin/env python3
"""Summarize monetization lane progress from cross-talk JSONL bus."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
CROSSTALK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _read_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _is_monetization_packet(packet: Dict[str, Any]) -> bool:
    task_id = str(packet.get("task_id", "")).upper()
    intent = str(packet.get("intent", "")).lower()
    summary = str(packet.get("summary", "")).lower()
    return task_id.startswith("MONETIZE-") or "monetiz" in summary or intent in {"lane_assignment", "asset_drop"}


def summarize(limit: int = 500) -> Dict[str, Any]:
    rows = _read_rows(CROSSTALK_LANE)
    if limit > 0:
        rows = rows[-limit:]

    filtered = [row for row in rows if _is_monetization_packet(row)]
    latest_by_task: Dict[str, Dict[str, Any]] = {}
    for row in filtered:
        task = str(row.get("task_id", "unknown"))
        latest_by_task[task] = row

    lanes = []
    for task_id, row in sorted(latest_by_task.items()):
        lanes.append(
            {
                "task_id": task_id,
                "status": row.get("status", "unknown"),
                "recipient": row.get("recipient", ""),
                "intent": row.get("intent", ""),
                "created_at": row.get("created_at", ""),
                "packet_id": row.get("packet_id", ""),
                "next_action": row.get("next_action", ""),
            }
        )

    counts: Dict[str, int] = {}
    for lane in lanes:
        state = str(lane.get("status", "unknown"))
        counts[state] = counts.get(state, 0) + 1

    return {
        "generated_at": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane_file": str(CROSSTALK_LANE),
        "monetization_packets_seen": len(filtered),
        "lanes": lanes,
        "status_counts": counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize monetization cross-talk lane status.")
    parser.add_argument("--limit", type=int, default=500, help="Number of latest packets to inspect")
    args = parser.parse_args()

    summary = summarize(limit=max(0, args.limit))
    day = _utc_now().strftime("%Y%m%d")
    out_dir = REPO_ROOT / "artifacts" / "agent_comm" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"monetization-swarm-status-{_utc_now().strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "summary_path": str(out_path), "status_counts": summary["status_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
