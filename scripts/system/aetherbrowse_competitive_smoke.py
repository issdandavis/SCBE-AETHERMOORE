#!/usr/bin/env python3
"""Cross-browser smoke benchmark for AetherBrowse landing + search UX.

Usage:
  python scripts/system/aetherbrowse_competitive_smoke.py --base-url http://127.0.0.1:8400
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "aetherbrowse_benchmark" / "latest_smoke.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check_health(base_url: str) -> dict[str, Any]:
    with urlopen(f"{base_url.rstrip('/')}/health", timeout=6) as resp:  # nosec B310 - local trusted endpoint
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    return payload


def run_browser_case(playwright, browser_name: str, base_url: str, query: str, out_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "browser": browser_name,
        "ok": False,
        "skipped": False,
        "error": "",
        "landing_url": "",
        "search_url": "",
        "landing_title": "",
        "search_title": "",
        "results_count": 0,
        "timings_ms": {},
        "screenshot": "",
    }

    browser_launcher = getattr(playwright, browser_name, None)
    if browser_launcher is None:
        result["skipped"] = True
        result["error"] = f"unknown browser engine: {browser_name}"
        return result

    t0 = time.perf_counter()
    browser = None
    context = None
    page = None
    try:
        browser = browser_launcher.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        t1 = time.perf_counter()
        page.goto(f"{base_url.rstrip('/')}/landing", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("h1", timeout=10000)
        landing_ok = page.locator("h1", has_text="AetherBrowse").count() > 0
        if not landing_ok:
            raise RuntimeError("landing heading not found")

        landing_ms = round((time.perf_counter() - t1) * 1000.0, 2)
        result["landing_url"] = page.url
        result["landing_title"] = page.title()

        t2 = time.perf_counter()
        page.fill("input[type='search']", query)
        page.press("input[type='search']", "Enter")
        page.wait_for_url("**/search**", timeout=20000)
        page.wait_for_selector(".result", timeout=20000)
        search_ms = round((time.perf_counter() - t2) * 1000.0, 2)

        results_count = page.locator(".result").count()
        result["search_url"] = page.url
        result["search_title"] = page.title()
        result["results_count"] = int(results_count)
        result["timings_ms"] = {
            "landing_load": landing_ms,
            "search_load": search_ms,
            "total": round((time.perf_counter() - t0) * 1000.0, 2),
        }

        screenshot_path = out_dir / f"{browser_name}_search.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        result["screenshot"] = str(screenshot_path)
        result["ok"] = results_count > 0
        if not result["ok"]:
            result["error"] = "search returned zero results"
        return result
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        text = str(exc)
        if "Executable doesn't exist" in text or "Please run the following command" in text:
            result["skipped"] = True
        result["error"] = text
        return result
    finally:
        if context:
            context.close()
        if browser:
            browser.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run AetherBrowse cross-browser smoke benchmark.")
    p.add_argument("--base-url", default="http://127.0.0.1:8400", help="Aether runtime base URL")
    p.add_argument("--query", default="aetherbrowse side panel ai browser", help="Search query")
    p.add_argument("--browsers", default="chromium,firefox,webkit", help="Comma-separated Playwright browsers")
    p.add_argument("--output", default=str(DEFAULT_OUT), help="JSON output path")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    health = check_health(args.base_url)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install") from exc

    browsers = [b.strip().lower() for b in args.browsers.split(",") if b.strip()]
    run_dir = output_path.parent / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, Any]] = []
    with sync_playwright() as p:
        for browser_name in browsers:
            cases.append(run_browser_case(p, browser_name, args.base_url, args.query, run_dir))

    ok_count = sum(1 for c in cases if c.get("ok"))
    skipped_count = sum(1 for c in cases if c.get("skipped"))
    payload = {
        "generated_at": now_iso(),
        "base_url": args.base_url,
        "query": args.query,
        "health": health,
        "summary": {
            "total": len(cases),
            "ok": ok_count,
            "failed": len(cases) - ok_count - skipped_count,
            "skipped": skipped_count,
        },
        "results": cases,
        "run_dir": str(run_dir),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
