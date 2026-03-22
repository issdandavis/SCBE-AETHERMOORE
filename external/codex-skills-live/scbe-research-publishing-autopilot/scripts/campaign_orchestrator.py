#!/usr/bin/env python3
"""
Build a multi-hour dispatch plan for research-to-publishing campaigns.

Input: campaign JSON
Output: dispatch plan JSON with heartbeat, draft-refresh, and publish events
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a multi-hour campaign dispatch plan.")
    parser.add_argument("--campaign", required=True, help="Path to campaign JSON")
    parser.add_argument("--out", required=True, help="Path to output plan JSON")
    parser.add_argument(
        "--now",
        default="",
        help="Optional ISO8601 timestamp (UTC). Example: 2026-02-23T18:00:00Z",
    )
    return parser.parse_args()


@dataclass
class Channel:
    name: str
    cadence_minutes: int
    enabled: bool = True


def parse_now(raw: str) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_channels(raw_channels: List[Dict[str, Any]]) -> List[Channel]:
    out: List[Channel] = []
    for row in raw_channels:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        cadence = int(row.get("cadence_minutes", 120))
        enabled = bool(row.get("enabled", True))
        out.append(Channel(name=name, cadence_minutes=max(5, cadence), enabled=enabled))
    return out


def ts_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def plan_events(campaign: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    run_hours = float(campaign.get("run_hours", 6.0))
    heartbeat_minutes = int(campaign.get("heartbeat_minutes", 15))
    campaign_id = str(campaign.get("campaign_id", "campaign-auto"))
    posts: List[Dict[str, Any]] = list(campaign.get("posts", []))
    channels = load_channels(list(campaign.get("channels", [])))

    window_end = now + timedelta(hours=max(1.0, run_hours))
    events: List[Dict[str, Any]] = []

    # Heartbeat events keep long runs observable.
    t = now
    while t <= window_end:
        events.append(
            {
                "ts": ts_iso(t),
                "type": "heartbeat",
                "campaign_id": campaign_id,
                "payload": {"status": "alive"},
            }
        )
        t += timedelta(minutes=max(5, heartbeat_minutes))

    # Dispatch events by channel cadence; rotate eligible posts.
    for channel in channels:
        if not channel.enabled:
            continue
        channel_posts = [p for p in posts if str(p.get("channel", "")).lower() == channel.name.lower()]
        if not channel_posts:
            continue

        idx = 0
        t = now + timedelta(minutes=3)
        while t <= window_end:
            post = channel_posts[idx % len(channel_posts)]
            post_id = str(post.get("id", f"{channel.name}-{idx+1}"))
            events.append(
                {
                    "ts": ts_iso(t),
                    "type": "publish",
                    "campaign_id": campaign_id,
                    "channel": channel.name,
                    "post_id": post_id,
                    "payload": {
                        "title": post.get("title", ""),
                        "cta": post.get("cta", ""),
                        "offer_path": post.get("offer_path", ""),
                    },
                }
            )

            # Add a follow-up check event shortly after publish.
            events.append(
                {
                    "ts": ts_iso(t + timedelta(minutes=20)),
                    "type": "metric_check",
                    "campaign_id": campaign_id,
                    "channel": channel.name,
                    "post_id": post_id,
                    "payload": {"window_minutes": 20},
                }
            )

            idx += 1
            t += timedelta(minutes=channel.cadence_minutes)

    events.sort(key=lambda e: (e["ts"], e.get("type", "")))
    return {
        "campaign_id": campaign_id,
        "generated_at": ts_iso(now),
        "window_start": ts_iso(now),
        "window_end": ts_iso(window_end),
        "retrigger_rules": campaign.get("retrigger_rules", []),
        "events": events,
        "summary": {
            "event_count": len(events),
            "publish_count": len([e for e in events if e["type"] == "publish"]),
            "heartbeat_count": len([e for e in events if e["type"] == "heartbeat"]),
        },
    }


def main() -> int:
    args = parse_args()
    campaign_path = Path(args.campaign)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    campaign = load_json(campaign_path)
    now = parse_now(args.now)
    plan = plan_events(campaign, now)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"Saved plan: {out_path}")
    print(f"Events: {plan['summary']['event_count']} | Publishes: {plan['summary']['publish_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
