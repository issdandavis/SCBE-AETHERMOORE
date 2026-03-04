#!/usr/bin/env python3
"""Execute browser tentacle tasks through Playwriter CLI.

This runner bridges dispatcher assignments to the user's active Chrome tab
without launching a new browser instance.

Usage:
  python scripts/system/playwriter_lane_runner.py --session 1 --domain github.com --task navigate
  python scripts/system/playwriter_lane_runner.py --session 1 --url https://example.com --task snapshot
  python scripts/system/playwriter_lane_runner.py --session 1 --expr "await page.goto('https://example.com')"
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes"
EXEC_LOG = LANE_ROOT / "playwriter_exec.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def build_expression(task: str, url: str, selector: str) -> str:
    t = task.strip().lower()
    if t == "navigate":
        return f"await page.goto('{url}')"
    if t == "snapshot":
        return "console.log(await accessibilitySnapshot({ page }))"
    if t == "title":
        return "console.log(await page.title())"
    if t == "click":
        if selector:
            return f"await page.locator({json.dumps(selector)}).click()"
        return "await page.getByRole('link').first().click()"
    if t == "content":
        return "console.log(await page.content())"
    return f"await page.goto('{url}')"


def _resolve_playwriter_bin() -> str:
    for candidate in ("playwriter", "playwriter.cmd"):
        found = shutil.which(candidate)
        if found:
            return found
    return "playwriter"


def run_playwriter(session_id: str, expr: str, timeout_ms: int) -> subprocess.CompletedProcess[str]:
    bin_path = _resolve_playwriter_bin()
    cmd = [bin_path, "-s", session_id, "-e", expr, "--timeout", str(timeout_ms)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Playwriter task for browser tentacle lane.")
    parser.add_argument("--session", required=True, help="Playwriter session id.")
    parser.add_argument("--task", default="navigate", help="navigate|snapshot|title|click|content")
    parser.add_argument("--domain", default="", help="Domain used when URL is omitted.")
    parser.add_argument("--url", default="", help="Target URL; defaults to https://<domain>.")
    parser.add_argument("--selector", default="", help="CSS/Playwright locator selector for click task.")
    parser.add_argument("--expr", default="", help="Raw playwriter JS expression. Overrides --task.")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--assignment-id", default="", help="Optional assignment id for audit links.")
    parser.add_argument("--dry-run", action="store_true", help="Print expression without executing.")
    args = parser.parse_args()

    if args.url:
        url = args.url.strip()
    elif args.domain:
        url = f"https://{args.domain.strip()}"
    else:
        url = "https://example.com"

    expr = args.expr.strip() or build_expression(args.task, url, args.selector)
    if args.dry_run:
        print(json.dumps({"ok": True, "session": args.session, "expr": expr}, indent=2))
        return 0

    result = run_playwriter(args.session, expr, args.timeout_ms)
    ok = result.returncode == 0
    payload = {
        "created_at": utc_now(),
        "assignment_id": args.assignment_id,
        "session_id": args.session,
        "task": args.task,
        "url": url,
        "expr": expr,
        "ok": ok,
        "return_code": result.returncode,
        "stdout": (result.stdout or "").strip()[:4000],
        "stderr": (result.stderr or "").strip()[:2000],
    }
    append_jsonl(EXEC_LOG, payload)
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
