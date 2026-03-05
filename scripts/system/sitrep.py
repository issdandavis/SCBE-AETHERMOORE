#!/usr/bin/env python3
"""
sitrep.py — Situation Report generator for SCBE multi-agent operations.

Scans cross-talk packets, git log, and artifacts to produce a deduplicated,
prioritized briefing of what happened, what's stuck, and what needs attention.

Usage:
  python scripts/system/sitrep.py                    # Last 24 hours
  python scripts/system/sitrep.py --hours 8          # Last 8 hours
  python scripts/system/sitrep.py --json             # Machine-readable output
  python scripts/system/sitrep.py --since 2026-03-04 # Since specific date
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_COMM = REPO_ROOT / "artifacts" / "agent_comm"
GITHUB_LANES = AGENT_COMM / "github_lanes"
NOTES_INBOX = REPO_ROOT / "notes" / "_inbox.md"
NOTES_CONTEXT = REPO_ROOT / "notes" / "_context.md"
SESSION_SIGNONS = AGENT_COMM / "session_signons.jsonl"


def parse_timestamp(ts: str) -> datetime | None:
    """Parse ISO-ish timestamps from packets."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H%M%S%fZ",
    ):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def scan_json_packets(since: datetime) -> list[dict]:
    """Scan artifacts/agent_comm/ date folders for JSON packets."""
    packets = []
    if not AGENT_COMM.exists():
        return packets

    for date_dir in sorted(AGENT_COMM.iterdir()):
        if not date_dir.is_dir() or date_dir.name == "github_lanes":
            continue
        # Quick date filter on directory name
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y%m%d").replace(
                tzinfo=timezone.utc
            )
            if dir_date.date() < since.date() - timedelta(days=1):
                continue
        except ValueError:
            continue

        for f in date_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ts = parse_timestamp(data.get("created_at", ""))
                if ts and ts >= since:
                    data["_source_file"] = str(f.name)
                    data["_parsed_ts"] = ts
                    packets.append(data)
            except (json.JSONDecodeError, OSError):
                continue

    return packets


def scan_inbox_packets(since: datetime) -> list[dict]:
    """Parse notes/_inbox.md cross-talk lines into pseudo-packets."""
    packets = []
    if not NOTES_INBOX.exists():
        return packets

    line_re = re.compile(
        r"^- (\S+)\s+"  # timestamp
        r"(?:\[.*?\]\s+)?"  # optional session/codename tags
        r"(\S+)\s*->\s*(\S+)\s*\|\s*"  # from -> to
        r"(\S+)\s*\|\s*"  # intent
        r"(\S+)\s*\|\s*"  # status
        r"(\S+)\s*\|\s*"  # task_slug
        r"(.+?)(?:\s*\(.*\))?$"  # summary (optional artifact path)
    )

    for line in NOTES_INBOX.read_text(encoding="utf-8").splitlines():
        m = line_re.match(line.strip())
        if not m:
            continue
        ts_str, frm, to, intent, status, slug, summary = m.groups()
        # Strip brackets from timestamps that have session prefixes
        ts_str = ts_str.strip("[]")
        ts = parse_timestamp(ts_str)
        if ts and ts >= since:
            packets.append(
                {
                    "created_at": ts_str,
                    "_parsed_ts": ts,
                    "from": frm,
                    "to": to,
                    "intent": intent,
                    "status": status,
                    "task_slug": slug,
                    "summary": summary.strip(),
                    "_source": "inbox",
                }
            )

    return packets


def extract_task_key(p: dict) -> str:
    """Extract a stable dedup key from a packet.

    Priority: task_id > task_slug > derived from filename/packet_id.
    The goal is that MONETIZE-SHOPIFY-CONVERSION packets all collapse to one entry.
    """
    # Best: explicit task_id field
    if p.get("task_id"):
        return p["task_id"]
    # Second: task_slug from inbox parsing
    if p.get("task_slug") and p["task_slug"] != "UNSPECIFIED":
        return p["task_slug"]
    # Third: derive from packet_id by stripping timestamp suffix
    pid = p.get("packet_id", "")
    if pid:
        # Pattern: cross-talk-agent-{agent}-{task-slug}-{timestamp}
        # Strip the timestamp portion (YYYYMMDDTHHMMSS... at end)
        import re

        m = re.match(
            r"^cross-talk-(?:agent-|artifacts-)?[\w-]*?-(.+?)-\d{8}T\d{6}",
            pid,
        )
        if m:
            return m.group(1).upper().replace("-", "_")
    # Fallback
    return p.get("packet_id", p.get("_source_file", "unknown"))


def deduplicate_by_task(packets: list[dict]) -> dict[str, dict]:
    """Keep only the latest packet per task key. Returns {key: packet}."""
    by_key = {}
    for p in packets:
        key = extract_task_key(p)
        existing = by_key.get(key)
        if not existing or p["_parsed_ts"] > existing["_parsed_ts"]:
            by_key[key] = p
    return by_key


def get_git_log(since: datetime, max_count: int = 20) -> list[dict]:
    """Get recent git commits."""
    since_str = since.strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={since_str}",
                f"--max-count={max_count}",
                "--pretty=format:%H|%h|%s|%an|%aI",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=10,
        )
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append(
                    {
                        "hash": parts[0],
                        "short": parts[1],
                        "message": parts[2],
                        "author": parts[3],
                        "date": parts[4],
                    }
                )
        return commits
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def get_active_sessions() -> list[dict]:
    """Read session signons from last 8 hours."""
    sessions = []
    if not SESSION_SIGNONS.exists():
        return sessions
    cutoff = datetime.now(timezone.utc) - timedelta(hours=8)
    for line in SESSION_SIGNONS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            ts = parse_timestamp(entry.get("signed_on", ""))
            if ts and ts >= cutoff:
                sessions.append(entry)
        except json.JSONDecodeError:
            continue
    return sessions


def classify_packets(
    deduped: dict[str, dict],
) -> dict[str, list[tuple[str, dict]]]:
    """Classify packets into priority buckets."""
    buckets = {
        "blocked": [],
        "needs_ack": [],
        "in_progress": [],
        "done": [],
        "other": [],
    }
    for slug, p in deduped.items():
        status = (p.get("status") or "").lower()
        if status == "blocked":
            buckets["blocked"].append((slug, p))
        elif p.get("ack_required") and status != "done":
            buckets["needs_ack"].append((slug, p))
        elif status == "in_progress":
            buckets["in_progress"].append((slug, p))
        elif status in ("done", "completed"):
            buckets["done"].append((slug, p))
        else:
            buckets["other"].append((slug, p))

    # Sort each bucket by timestamp (newest first)
    for key in buckets:
        buckets[key].sort(key=lambda x: x[1]["_parsed_ts"], reverse=True)

    return buckets


def format_packet_line(slug: str, p: dict) -> str:
    """Format a single packet into a readable line."""
    ts = p.get("created_at", "?")
    frm = p.get("from", "?")
    to = p.get("to", "?")
    summary = p.get("summary", "")
    # Truncate long summaries
    if len(summary) > 120:
        summary = summary[:117] + "..."
    return f"  [{ts}] {frm} -> {to} | {slug} | {summary}"


def render_text_report(
    buckets: dict,
    commits: list[dict],
    sessions: list[dict],
    total_raw: int,
    total_deduped: int,
    hours: float,
) -> str:
    """Render human-readable situation report."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"  SITREP — Last {hours:.0f} hours")
    lines.append(
        f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    lines.append(
        f"  Packets: {total_raw} raw -> {total_deduped} unique tasks"
    )
    lines.append("=" * 72)

    # Active sessions
    if sessions:
        lines.append(f"\n## Active Sessions ({len(sessions)})")
        for s in sessions:
            lines.append(
                f"  {s.get('callsign', '?')} | {s.get('agent', '?')} | signed on {s.get('signed_on', '?')}"
            )

    # BLOCKED — highest priority
    if buckets["blocked"]:
        lines.append(f"\n## BLOCKED ({len(buckets['blocked'])})")
        for slug, p in buckets["blocked"]:
            lines.append(format_packet_line(slug, p))

    # Needs ACK
    if buckets["needs_ack"]:
        lines.append(f"\n## NEEDS ACK ({len(buckets['needs_ack'])})")
        for slug, p in buckets["needs_ack"]:
            lines.append(format_packet_line(slug, p))

    # In Progress
    if buckets["in_progress"]:
        lines.append(f"\n## IN PROGRESS ({len(buckets['in_progress'])})")
        for slug, p in buckets["in_progress"]:
            lines.append(format_packet_line(slug, p))

    # Done
    if buckets["done"]:
        lines.append(f"\n## DONE ({len(buckets['done'])})")
        for slug, p in buckets["done"]:
            lines.append(format_packet_line(slug, p))

    # Other
    if buckets["other"]:
        lines.append(f"\n## OTHER ({len(buckets['other'])})")
        for slug, p in buckets["other"]:
            lines.append(format_packet_line(slug, p))

    # Git commits
    if commits:
        lines.append(f"\n## GIT LOG ({len(commits)} commits)")
        for c in commits[:15]:
            lines.append(f"  {c['short']} {c['message']}")

    lines.append("\n" + "=" * 72)
    return "\n".join(lines)


def render_json_report(
    buckets: dict,
    commits: list[dict],
    sessions: list[dict],
    total_raw: int,
    total_deduped: int,
    hours: float,
) -> str:
    """Render machine-readable JSON report."""

    def clean_packet(slug, p):
        cp = {k: v for k, v in p.items() if not k.startswith("_")}
        cp["task_slug"] = slug
        return cp

    report = {
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "window_hours": hours,
        "packets_raw": total_raw,
        "packets_deduped": total_deduped,
        "sessions": sessions,
        "blocked": [clean_packet(s, p) for s, p in buckets["blocked"]],
        "needs_ack": [clean_packet(s, p) for s, p in buckets["needs_ack"]],
        "in_progress": [
            clean_packet(s, p) for s, p in buckets["in_progress"]
        ],
        "done": [clean_packet(s, p) for s, p in buckets["done"]],
        "commits": commits[:15],
    }
    return json.dumps(report, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="SCBE Situation Report Generator"
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24,
        help="Look back N hours (default: 24)",
    )
    parser.add_argument(
        "--since", type=str, help="Look back to specific date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of text"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        hours = (datetime.now(timezone.utc) - since).total_seconds() / 3600
    else:
        hours = args.hours
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Gather data
    json_packets = scan_json_packets(since)
    inbox_packets = scan_inbox_packets(since)
    all_packets = json_packets + inbox_packets
    total_raw = len(all_packets)

    deduped = deduplicate_by_task(all_packets)
    total_deduped = len(deduped)

    buckets = classify_packets(deduped)
    commits = get_git_log(since)
    sessions = get_active_sessions()

    # Render
    if args.json:
        output = render_json_report(
            buckets, commits, sessions, total_raw, total_deduped, hours
        )
    else:
        output = render_text_report(
            buckets, commits, sessions, total_raw, total_deduped, hours
        )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
