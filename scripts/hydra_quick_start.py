#!/usr/bin/env python3
"""
HYDRA Browser Quick-Start — 3 modes, one script.
=================================================

Usage:
    # 1. Single scrape task (headless driver)
    python scripts/hydra_quick_start.py scrape "https://example.com" --extract "h1"

    # 2. Multi-agent swarm task (6 Sacred Tongue agents)
    python scripts/hydra_quick_start.py swarm "find pricing on competitor.com"

    # 3. Start the governed API server (FastAPI on port 8001)
    python scripts/hydra_quick_start.py server

    # 4. Health check — verify all deps installed
    python scripts/hydra_quick_start.py check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

# Ensure repo root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)


# ---------------------------------------------------------------------------
#  Health check
# ---------------------------------------------------------------------------

def check_deps() -> bool:
    """Verify all required dependencies are installed."""
    ok = True
    checks = {
        "playwright": "pip install 'playwright>=1.40.0' && python -m playwright install chromium",
        "fastapi": "pip install fastapi",
        "uvicorn": "pip install uvicorn",
        "pydantic": "pip install pydantic",
        "httpx": "pip install httpx",
    }

    for pkg, fix in checks.items():
        try:
            __import__(pkg)
            print(f"  [OK]  {pkg}")
        except ImportError:
            print(f"  [MISSING]  {pkg}  ->  {fix}")
            ok = False

    # Check Chromium binary
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("  [OK]  Chromium binary")
    except Exception as e:
        print(f"  [MISSING]  Chromium binary  ->  python -m playwright install chromium")
        print(f"             Error: {e}")
        ok = False

    # Check headless driver importable
    try:
        from src.symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.headless_driver import (
            HeadlessBrowserDriver,
        )
        print("  [OK]  HeadlessBrowserDriver")
    except Exception as e:
        print(f"  [WARN]  HeadlessBrowserDriver import: {e}")

    # Check swarm importable
    try:
        from hydra.swarm_browser import SwarmBrowser
        print("  [OK]  SwarmBrowser (HYDRA)")
    except Exception as e:
        print(f"  [WARN]  SwarmBrowser import: {e}")

    # Check FastAPI app importable
    try:
        from agents.browser.main import app
        print("  [OK]  FastAPI browser app")
    except Exception as e:
        print(f"  [WARN]  FastAPI browser app: {e}")

    print()
    if ok:
        print("All dependencies installed. HYDRA is ready.")
    else:
        print("Some dependencies missing. Install them and retry.")
    return ok


# ---------------------------------------------------------------------------
#  Mode 1: Single scrape
# ---------------------------------------------------------------------------

async def run_scrape(url: str, extract_selector: str, screenshot: bool, output: str | None):
    """Scrape a single page with the HeadlessBrowserDriver."""
    from src.symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.headless_driver import (
        HeadlessBrowserDriver,
        DriverMode,
    )

    driver = HeadlessBrowserDriver(mode=DriverMode.HEADLESS, stealth=False, fast_mode=True)
    await driver.start()

    result = {"url": url, "ts": time.time()}

    r = await driver.navigate(url)
    result["navigate"] = {"success": r.success, "duration_ms": r.duration_ms}
    if not r.success:
        result["error"] = r.error
        print(json.dumps(result, indent=2))
        await driver.stop()
        return

    if extract_selector:
        r = await driver.extract_text(extract_selector)
        result["extract"] = {"success": r.success, "data": r.data, "error": r.error}

    if screenshot:
        r = await driver.screenshot()
        result["screenshot"] = {"success": r.success, "path": r.screenshot_path}

    # Always grab page title
    r = await driver.evaluate("document.title")
    if r.success:
        result["title"] = r.data

    await driver.stop()

    payload = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(payload)
        print(f"Result written to {output}")
    else:
        print(payload)


# ---------------------------------------------------------------------------
#  Mode 2: Swarm task
# ---------------------------------------------------------------------------

async def run_swarm(task: str, dry_run: bool, backend: str, provider: str):
    """Run a multi-agent swarm browser task."""
    from hydra.swarm_browser import SwarmBrowser

    swarm = SwarmBrowser(
        provider_type=provider,
        backend_type=backend,
        dry_run=dry_run,
    )
    await swarm.launch()
    result = await swarm.execute_task(task)
    await swarm.shutdown()
    print(json.dumps(result, indent=2, default=str))


# ---------------------------------------------------------------------------
#  Mode 3: API server
# ---------------------------------------------------------------------------

def run_server(host: str, port: int):
    """Start the governed FastAPI browser server."""
    import uvicorn
    print(f"\nStarting HYDRA Browser API on http://{host}:{port}")
    print("Endpoints:")
    print(f"  POST /browse          — execute a governed browser action")
    print(f"  POST /safety-check    — check action safety without executing")
    print(f"  GET  /stats           — session pool statistics")
    print(f"  GET  /health          — health check")
    print()
    uvicorn.run("agents.browser.main:app", host=host, port=port, reload=False)


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="HYDRA Browser Quick-Start",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # --- check ---
    sub.add_parser("check", help="Verify all dependencies are installed")

    # --- scrape ---
    p_scrape = sub.add_parser("scrape", help="Scrape a single URL")
    p_scrape.add_argument("url", help="URL to scrape")
    p_scrape.add_argument("--extract", "-e", default="body", help="CSS selector to extract text from (default: body)")
    p_scrape.add_argument("--screenshot", "-s", action="store_true", help="Take a screenshot")
    p_scrape.add_argument("--output", "-o", help="Write JSON result to file")

    # --- swarm ---
    p_swarm = sub.add_parser("swarm", help="Run a multi-agent swarm task")
    p_swarm.add_argument("task", help="Natural language task description")
    p_swarm.add_argument("--dry-run", action="store_true", help="Mock mode — no real browser")
    p_swarm.add_argument("--backend", default="playwright", choices=["playwright", "selenium", "cdp"])
    p_swarm.add_argument("--provider", default="local", choices=["local", "hf", "huggingface"])

    # --- server ---
    p_server = sub.add_parser("server", help="Start the governed API server")
    p_server.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    p_server.add_argument("--port", type=int, default=8001, help="Bind port (default: 8001)")

    args = parser.parse_args()

    if args.mode == "check":
        check_deps()
    elif args.mode == "scrape":
        asyncio.run(run_scrape(args.url, args.extract, args.screenshot, args.output))
    elif args.mode == "swarm":
        asyncio.run(run_swarm(args.task, args.dry_run, args.backend, args.provider))
    elif args.mode == "server":
        run_server(args.host, args.port)


if __name__ == "__main__":
    main()
