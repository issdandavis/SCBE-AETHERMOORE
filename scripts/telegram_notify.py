#!/usr/bin/env python3
"""
Send SCBE autopilot notifications to Telegram.

Usage:
  # One-shot message
  python scripts/telegram_notify.py --message "Hello from SCBE"

  # From autopilot JSON report
  python scripts/telegram_notify.py --report artifacts/ops-autopilot/latest.json

  # From scan postprocess
  python scripts/telegram_notify.py --postprocess artifacts/repo_scans/.../postprocess/

Environment:
  SCBE_TELEGRAM_BOT_TOKEN  — Bot API token (from @BotFather)
  SCBE_TELEGRAM_CHAT_ID    — Chat/channel ID to send to

Setup:
  1. Message @BotFather on Telegram, /newbot, get the token
  2. Add the bot to your channel/group, send a message, then:
     curl https://api.telegram.org/bot<TOKEN>/getUpdates
     Find your chat_id in the response
  3. Set env vars:
     SCBE_TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
     SCBE_TELEGRAM_CHAT_ID=-100123456789
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _get_config() -> tuple[str, str]:
    token = os.getenv("SCBE_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("SCBE_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print(
            "Missing SCBE_TELEGRAM_BOT_TOKEN or SCBE_TELEGRAM_CHAT_ID.\n"
            "Set these env vars to enable Telegram notifications.\n"
            "See: scripts/telegram_notify.py header for setup instructions.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token, chat_id


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def format_autopilot_report(report: Dict[str, Any]) -> str:
    """Format an autopilot JSON report into a Telegram message."""
    status = report.get("status", "unknown")
    status_emoji = {"done": "✅", "ok": "✅", "blocked": "🚨", "in_progress": "⏳"}.get(status, "❓")
    run_id = report.get("run_id", "?")

    lines = [
        f"{status_emoji} *SCBE Ops Pulse* — `{run_id}`",
        f"Status: *{status}*",
    ]

    # Scan summary
    scan = report.get("scan", {})
    if scan.get("ok"):
        summary = scan.get("scan_summary", {})
        file_count = summary.get("file_count", "?")
        lines.append(f"Scan: {file_count} files")
        top_tasks = scan.get("top_tasks", [])
        if top_tasks:
            lines.append("Top tasks:")
            for t in top_tasks[:3]:
                lines.append(f"  • P{t.get('priority', '?')}: {t.get('title', '?')}")
    elif scan:
        lines.append(f"Scan: FAILED — {scan.get('error', '?')[:100]}")

    # Smoke summary
    smoke = report.get("smoke", {})
    if smoke.get("ok") is True:
        lines.append("HF Smoke: passed")
    elif smoke.get("ok") is False:
        lines.append("HF Smoke: FAILED")
    elif smoke.get("status") == "skipped":
        lines.append("HF Smoke: skipped")

    # Steps (from 24x7 wrapper)
    steps = report.get("steps", {}) or report.get("latest_cycle", {}).get("steps", {})
    if steps:
        for name, step in steps.items():
            st = step.get("status", "?")
            elapsed = step.get("elapsed_sec", "?")
            icon = "✅" if st == "ok" else "❌"
            lines.append(f"{icon} {name}: {st} ({elapsed}s)")

    return "\n".join(lines)


def format_postprocess_summary(postprocess_dir: Path) -> str:
    """Format scan postprocess results into a Telegram message."""
    folder_map = postprocess_dir / "folder_map.json"
    tasks_file = postprocess_dir / "tasks.json"

    lines = ["📊 *SCBE Scan Postprocess*"]

    if folder_map.exists():
        data = json.loads(folder_map.read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        totals = summary.get("totals", {})
        lines.append(
            f"Files: clean={totals.get('clean', '?')} | "
            f"risky={totals.get('risky', '?')} | "
            f"archive={totals.get('archive', '?')}"
        )
        lines.append(f"Folders: {summary.get('folders', '?')}")

        folders = data.get("folders", [])
        risky_folders = [f for f in folders if f.get("risky", 0) > 0][:5]
        if risky_folders:
            lines.append("Top risky:")
            for f in risky_folders:
                lines.append(f"  • `{f['folder']}` ({f['risky']} risky)")

    if tasks_file.exists():
        tasks = json.loads(tasks_file.read_text(encoding="utf-8")).get("tasks", [])
        if tasks:
            lines.append("Tasks:")
            for t in tasks[:4]:
                lines.append(f"  • P{t.get('priority', '?')}: {t.get('title', '?')}")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"_Generated {ts}_")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Send SCBE notifications to Telegram")
    ap.add_argument("--message", default="", help="Send a plain text message")
    ap.add_argument("--report", default="", help="Path to autopilot JSON report")
    ap.add_argument("--postprocess", default="", help="Path to postprocess output directory")
    ap.add_argument("--dry-run", action="store_true", help="Print message without sending")
    args = ap.parse_args()

    if not args.message and not args.report and not args.postprocess:
        ap.error("Provide --message, --report, or --postprocess")

    # Build message
    if args.report:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        text = format_autopilot_report(report)
    elif args.postprocess:
        text = format_postprocess_summary(Path(args.postprocess))
    else:
        text = args.message

    if args.dry_run:
        # Windows console may not support emoji; encode safely for display
        safe = text.encode("utf-8", errors="replace").decode("utf-8")
        sys.stdout.buffer.write(b"--- DRY RUN ---\n")
        sys.stdout.buffer.write(safe.encode("utf-8"))
        sys.stdout.buffer.write(b"\n--- END ---\n")
        sys.stdout.buffer.flush()
        return 0

    token, chat_id = _get_config()
    result = send_message(token, chat_id, text)

    if result.get("ok"):
        print(f"Sent to chat {chat_id}")
        return 0
    else:
        print(f"Failed: {result.get('error', result)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
