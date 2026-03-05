#!/usr/bin/env python3
"""Monitor Kindle lane packets on the cross-talk bus."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_PATH = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _read_packets(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    packets: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            packets.append(obj)
    return packets


def _is_kindle_packet(packet: Dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            str(packet.get("packet_id", "")),
            str(packet.get("task_id", "")),
            str(packet.get("summary", "")),
            str(packet.get("next_action", "")),
            str(packet.get("proof", "")),
        ]
    ).lower()
    return "kindle" in haystack or "fire os" in haystack or "capacitor" in haystack


def summarize(limit: int = 400) -> Dict[str, Any]:
    rows = _read_packets(LANE_PATH)
    if limit > 0:
        rows = rows[-limit:]
    kindle_rows = [row for row in rows if _is_kindle_packet(row)]
    latest = kindle_rows[-1] if kindle_rows else {}
    status_counts: Dict[str, int] = {}
    for row in kindle_rows:
        state = str(row.get("status", "unknown"))
        status_counts[state] = status_counts.get(state, 0) + 1
    return {
        "generated_at": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane_file": str(LANE_PATH),
        "kindle_packet_count": len(kindle_rows),
        "latest_packet": latest,
        "status_counts": status_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Kindle packet progress from cross-talk bus.")
    parser.add_argument("--limit", type=int, default=400, help="Number of latest rows to inspect")
    args = parser.parse_args()

    payload = summarize(limit=max(0, args.limit))
    day = _utc_now().strftime("%Y%m%d")
    out_dir = REPO_ROOT / "artifacts" / "agent_comm" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"kindle-lane-status-{_utc_now().strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "status_path": str(out_path), "count": payload["kindle_packet_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
