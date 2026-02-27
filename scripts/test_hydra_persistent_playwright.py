#!/usr/bin/env python3
"""
Minimal Playwright persistent-context test harness.

Validates that:
  1. launchPersistentContext creates a browser with userDataDir
  2. Cookies / localStorage survive close → reopen
  3. Multiple isolated sessions don't leak state

Run:
    pip install playwright && playwright install chromium
    python scripts/test_hydra_persistent_playwright.py
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    tmp_root = Path(tempfile.mkdtemp(prefix="hydra_persist_"))
    user_data_dir = tmp_root / "session_alpha"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"[harness] userDataDir = {user_data_dir}")

    # ── Phase 1: Launch persistent context, set a cookie, close ──────
    print("\n── Phase 1: Launch + set cookie ──")
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://example.com", wait_until="domcontentloaded")
        title = await page.title()
        print(f"  Page title: {title}")

        # Set a cookie via JS
        await page.evaluate("""() => {
            document.cookie = "hydra_test=persistent_works; path=/; max-age=3600";
            localStorage.setItem("hydra_session", "alpha-001");
        }""")
        print("  Cookie + localStorage set")

        await ctx.close()

    print("  Context closed (data flushed to disk)")

    # ── Phase 2: Reopen same userDataDir, verify persistence ─────────
    print("\n── Phase 2: Reopen + verify persistence ──")
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://example.com", wait_until="domcontentloaded")

        cookie_val = await page.evaluate("() => document.cookie")
        ls_val = await page.evaluate("() => localStorage.getItem('hydra_session')")

        print(f"  cookie  = {cookie_val}")
        print(f"  localStorage = {ls_val}")

        cookie_ok = "hydra_test=persistent_works" in (cookie_val or "")
        ls_ok = ls_val == "alpha-001"

        await ctx.close()

    # ── Phase 3: Isolation — different userDataDir is empty ──────────
    print("\n── Phase 3: Session isolation ──")
    user_data_dir_b = tmp_root / "session_beta"
    user_data_dir_b.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(user_data_dir_b),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://example.com", wait_until="domcontentloaded")

        cookie_val = await page.evaluate("() => document.cookie")
        ls_val = await page.evaluate("() => localStorage.getItem('hydra_session')")

        print(f"  cookie (beta)  = {cookie_val!r}")
        print(f"  localStorage (beta) = {ls_val!r}")

        isolated = "hydra_test" not in (cookie_val or "") and ls_val is None

        await ctx.close()

    # ── Results ──────────────────────────────────────────────────────
    print("\n── Results ──")
    results = {
        "cookie_persisted": cookie_ok,
        "localstorage_persisted": ls_ok,
        "session_isolation": isolated,
    }
    print(json.dumps(results, indent=2))

    # Cleanup
    shutil.rmtree(tmp_root, ignore_errors=True)

    if all(results.values()):
        print("\n✓ All persistent browser checks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
