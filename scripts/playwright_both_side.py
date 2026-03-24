#!/usr/bin/env python3
"""Handle two browser sides (left/right) in one Playwright session.

Example:
  python scripts/playwright_both_side.py \
    --left-url https://www.linkedin.com/ \
    --right-url https://telegra.ph/
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def looks_like_bot_check(page: Any) -> bool:
    checks = [
        "captcha",
        "bot",
        "verify",
        "are you human",
    ]
    try:
        text = f"{page.url} {page.title()}".lower()
    except Exception:
        return False
    return any(token in text for token in checks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open and manage both browser sides in one Playwright run.")
    parser.add_argument("--left-url", required=True, help="Left side URL")
    parser.add_argument("--right-url", required=True, help="Right side URL")
    parser.add_argument("--user-data-dir", default="", help="Persistent profile directory")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--timeout-ms", type=int, default=60000, help="Navigation timeout")
    parser.add_argument(
        "--screenshot-dir", default="artifacts/playwright-both-side", help="Screenshot/report output dir"
    )
    parser.add_argument("--left-name", default="left", help="Name label for left side")
    parser.add_argument("--right-name", default="right", help="Name label for right side")
    parser.add_argument("--keep-open", action="store_true", help="Keep browser open until Enter")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    out_dir = Path(args.screenshot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    profile_dir = args.user_data_dir or str(Path.home() / ".scbe-playwright-both-side")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=profile_dir, headless=args.headless)
        left = context.new_page()
        right = context.new_page()

        left.goto(args.left_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        right.goto(args.right_url, wait_until="domcontentloaded", timeout=args.timeout_ms)

        left_png = out_dir / f"{stamp}-{args.left_name}.png"
        right_png = out_dir / f"{stamp}-{args.right_name}.png"
        left.screenshot(path=str(left_png), full_page=True)
        right.screenshot(path=str(right_png), full_page=True)

        report = {
            "generated_at": now_iso(),
            "left": {
                "name": args.left_name,
                "url": left.url,
                "title": left.title(),
                "bot_check_hint": looks_like_bot_check(left),
                "screenshot": str(left_png),
            },
            "right": {
                "name": args.right_name,
                "url": right.url,
                "title": right.title(),
                "bot_check_hint": looks_like_bot_check(right),
                "screenshot": str(right_png),
            },
            "headless": args.headless,
            "profile_dir": profile_dir,
        }

        report_path = out_dir / f"{stamp}-report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(f"[both-side] left={report['left']['url']}")
        print(f"[both-side] right={report['right']['url']}")
        print(f"[both-side] report={report_path}")

        if args.keep_open:
            input("Browser is open. Press Enter to close... ")

        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
