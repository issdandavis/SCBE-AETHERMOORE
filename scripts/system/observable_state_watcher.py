#!/usr/bin/env python3
"""Observable state watcher for SCBE bus runs.

This script does not expose hidden model chain-of-thought. It builds a readable
watch surface from durable artifacts the system already owns: mirror-room round
decisions, free-LLM dispatch events, and file-tracking snapshots.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIRROR_ROOT = REPO_ROOT / "artifacts" / "agent_bus" / "mirror_room"
DEFAULT_DISPATCH_LOG = REPO_ROOT / ".scbe" / "packets" / "free_llm_dispatch.jsonl"
DEFAULT_FILE_SNAPSHOT = (
    REPO_ROOT / "artifacts" / "file_tracking" / "latest" / "file_tracking_snapshot.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "artifacts" / "agent_bus" / "observable_state" / "latest_watcher.json"
)


@dataclass(frozen=True)
class WatcherWeights:
    action: float = 1.0
    live_text: float = (1.0 + math.sqrt(5.0)) / 2.0
    packet_state: float = ((1.0 + math.sqrt(5.0)) / 2.0) ** 2

    def normalized(self) -> dict[str, float]:
        raw = {
            "action": self.action,
            "live_text": self.live_text,
            "packet_state": self.packet_state,
        }
        total = sum(raw.values())
        return {key: round(value / total, 8) for key, value in raw.items()}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _load_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _latest_mirror_round(
    series_id: str, mirror_root: Path = DEFAULT_MIRROR_ROOT
) -> dict[str, Any]:
    return _load_json(mirror_root / series_id / "latest_round.json", {})


def _hex_prefix(value: str | None, chars: int = 16) -> str | None:
    if not value:
        return None
    return value[:chars]


def _binary_prefix_from_hex(value: str | None, bits: int = 64) -> str | None:
    if not value:
        return None
    clean = "".join(char for char in value.lower() if char in "0123456789abcdef")
    if not clean:
        return None
    as_bits = "".join(f"{int(char, 16):04b}" for char in clean)
    return as_bits[:bits]


def _action_lane(round_packet: dict[str, Any]) -> dict[str, Any]:
    primary = (
        round_packet.get("primary_bus", []) if isinstance(round_packet, dict) else []
    )
    secondary = (
        round_packet.get("secondary_bus", []) if isinstance(round_packet, dict) else []
    )
    tertiary = (
        round_packet.get("tertiary_bus", []) if isinstance(round_packet, dict) else []
    )
    return {
        "selected_provider": round_packet.get("selected_provider"),
        "task": round_packet.get("task", {}),
        "primary": [
            {
                "provider": item.get("provider"),
                "role": item.get("role"),
                "score": item.get("score"),
                "reason": item.get("reason"),
            }
            for item in primary
            if isinstance(item, dict)
        ],
        "watchers": [
            {
                "provider": item.get("provider"),
                "score": item.get("score"),
                "policy": item.get("watch_policy"),
            }
            for item in secondary
            if isinstance(item, dict)
        ],
        "resting": [
            {
                "provider": item.get("provider"),
                "reason": item.get("reason"),
            }
            for item in tertiary
            if isinstance(item, dict)
        ],
    }


def _live_text_lane(dispatch_events: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = []
    for event in dispatch_events:
        result = (
            event.get("result", {}) if isinstance(event.get("result"), dict) else {}
        )
        route = event.get("route", {}) if isinstance(event.get("route"), dict) else {}
        summaries.append(
            {
                "event_id": event.get("event_id"),
                "provider": route.get("provider"),
                "model": result.get("model"),
                "finish_reason": result.get("finish_reason"),
                "text_chars": result.get("text_chars", 0),
                "text_sha256_prefix": _hex_prefix(result.get("text_sha256")),
            }
        )
    return {
        "policy": "live text is summarized by event metadata and output hash; raw provider text is not replayed",
        "events": summaries,
    }


def _packet_state_lane(
    file_snapshot: dict[str, Any], dispatch_events: list[dict[str, Any]]
) -> dict[str, Any]:
    files = (
        file_snapshot.get("files", [])
        if isinstance(file_snapshot.get("files"), list)
        else []
    )
    file_packets = []
    for item in files:
        if not isinstance(item, dict):
            continue
        file_packets.append(
            {
                "path": item.get("path"),
                "git_status": item.get("git_status"),
                "sha256_hex": _hex_prefix(item.get("sha256"), 24),
                "sha256_binary": _binary_prefix_from_hex(item.get("sha256"), 48),
                "size_bytes": item.get("size_bytes"),
            }
        )

    dispatch_packets = []
    for event in dispatch_events:
        prompt = (
            event.get("prompt", {}) if isinstance(event.get("prompt"), dict) else {}
        )
        dispatch_packets.append(
            {
                "event_id": event.get("event_id"),
                "prompt_hex": _hex_prefix(prompt.get("sha256"), 24),
                "prompt_binary": _binary_prefix_from_hex(prompt.get("sha256"), 48),
                "prompt_chars": prompt.get("chars"),
            }
        )

    return {
        "policy": "binary and hex views are hashes and packet identifiers, not hidden model thoughts",
        "file_summary": file_snapshot.get("summary", {}),
        "file_packets": file_packets,
        "dispatch_packets": dispatch_packets,
    }


def build_watcher_state(
    *,
    series_id: str,
    mirror_root: Path = DEFAULT_MIRROR_ROOT,
    dispatch_log: Path = DEFAULT_DISPATCH_LOG,
    file_snapshot_path: Path = DEFAULT_FILE_SNAPSHOT,
    dispatch_tail: int = 5,
    weights: WatcherWeights | None = None,
) -> dict[str, Any]:
    round_packet = _latest_mirror_round(series_id, mirror_root)
    dispatch_events = _load_jsonl_tail(dispatch_log, dispatch_tail)
    file_snapshot = _load_json(file_snapshot_path, {})
    lane_weights = (weights or WatcherWeights()).normalized()
    return {
        "schema_version": "scbe-observable-state-watcher-v1",
        "created_at_utc": _utc_now(),
        "series_id": series_id,
        "visibility_contract": {
            "shows": [
                "action decisions",
                "provider scores and watcher/rest roles",
                "live-text metadata",
                "binary/hex hash packet views",
                "file tracking hashes and statuses",
            ],
            "does_not_show": [
                "hidden chain-of-thought",
                "raw prompts unless already shown by caller",
                "raw file contents",
                "secrets",
            ],
        },
        "lane_weights": lane_weights,
        "lanes": {
            "action": _action_lane(round_packet),
            "live_text": _live_text_lane(dispatch_events),
            "packet_state": _packet_state_lane(file_snapshot, dispatch_events),
        },
    }


def write_watcher_state(
    state: dict[str, Any], output_path: Path = DEFAULT_OUTPUT
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an observable SCBE bus watcher state"
    )
    parser.add_argument("--series-id", default="file-tracking-bus-weave")
    parser.add_argument("--mirror-root", default=str(DEFAULT_MIRROR_ROOT))
    parser.add_argument("--dispatch-log", default=str(DEFAULT_DISPATCH_LOG))
    parser.add_argument("--file-snapshot", default=str(DEFAULT_FILE_SNAPSHOT))
    parser.add_argument("--dispatch-tail", type=int, default=5)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state = build_watcher_state(
        series_id=args.series_id,
        mirror_root=Path(args.mirror_root),
        dispatch_log=Path(args.dispatch_log),
        file_snapshot_path=Path(args.file_snapshot),
        dispatch_tail=args.dispatch_tail,
    )
    output_path = write_watcher_state(state, Path(args.output))
    if args.json:
        print(
            json.dumps(
                {"state": state, "written": str(output_path)},
                indent=2,
                ensure_ascii=True,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "series_id": state["series_id"],
                    "lane_weights": state["lane_weights"],
                    "selected_provider": state["lanes"]["action"].get(
                        "selected_provider"
                    ),
                    "dispatch_events": len(state["lanes"]["live_text"]["events"]),
                    "file_packets": len(state["lanes"]["packet_state"]["file_packets"]),
                    "written": str(output_path),
                },
                indent=2,
                ensure_ascii=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
