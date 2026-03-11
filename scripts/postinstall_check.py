#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Post-Install Check & Browser Bootstrap
========================================================

Runs automatically after `pip install scbe-aethermoore[browser]` or manually.
Verifies deps, installs Chromium if missing, and validates dual-view readiness.

Usage:
    scbe-browser-check           # CLI entry point after pip install
    python scripts/postinstall_check.py   # manual run
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
#  Colour helpers (graceful fallback on dumb terminals)
# ---------------------------------------------------------------------------

_GREEN = "\033[92m" if sys.stdout.isatty() else ""
_RED = "\033[91m" if sys.stdout.isatty() else ""
_YELLOW = "\033[93m" if sys.stdout.isatty() else ""
_RESET = "\033[0m" if sys.stdout.isatty() else ""
_BOLD = "\033[1m" if sys.stdout.isatty() else ""


def _ok(msg: str) -> None:
    print(f"  {_GREEN}[OK]{_RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}[WARN]{_RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {_RED}[FAIL]{_RESET}  {msg}")


# ---------------------------------------------------------------------------
#  Dep checks
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = {
    "playwright": "pip install 'playwright>=1.40.0'",
    "fastapi": "pip install fastapi",
    "uvicorn": "pip install uvicorn",
    "pydantic": "pip install pydantic",
    "httpx": "pip install httpx",
}

OPTIONAL_PACKAGES = {
    "playwright_stealth": "pip install playwright-stealth  (anti-bot evasion)",
    "openai": "pip install openai  (LLM provider for swarm planning)",
    "selenium": "pip install selenium  (fallback browser backend)",
}


def check_python_packages() -> list[str]:
    """Return list of missing required packages."""
    missing = []
    for pkg, fix in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(pkg)
            _ok(pkg)
        except ImportError:
            _fail(f"{pkg}  ->  {fix}")
            missing.append(pkg)

    for pkg, fix in OPTIONAL_PACKAGES.items():
        try:
            importlib.import_module(pkg)
            _ok(f"{pkg} (optional)")
        except ImportError:
            _warn(f"{pkg} not installed  ->  {fix}")

    return missing


def check_chromium() -> bool:
    """Check if Playwright Chromium is installed, offer to install."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        _ok("Chromium binary (headless)")

        # Check headed mode availability
        display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        if display or sys.platform == "win32" or sys.platform == "darwin":
            _ok("Headed mode available (display detected)")
        else:
            _warn("No DISPLAY set — headed mode requires X11/Wayland/VNC")
            _warn("  Set DISPLAY=:0 or use Xvfb for headed mode on servers")

        return True
    except Exception as e:
        _fail(f"Chromium not available: {e}")
        return False


def install_chromium() -> bool:
    """Attempt to install Playwright Chromium."""
    print(f"\n{_BOLD}Installing Chromium browser...{_RESET}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            _ok("Chromium installed successfully")
            return True
        else:
            _fail(f"Chromium install failed: {result.stderr[-200:]}")
            # Try with deps
            print("  Retrying with system deps...")
            result2 = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
                capture_output=True, text=True, timeout=300,
            )
            if result2.returncode == 0:
                _ok("Chromium installed with system deps")
                return True
            _fail("Chromium install failed. Install manually:")
            _fail("  python -m playwright install chromium")
            return False
    except Exception as e:
        _fail(f"Install error: {e}")
        return False


def check_dual_view() -> dict:
    """Report dual-view (headless + headed) readiness."""
    status = {"headless": False, "headed": False, "xvfb": False}

    # Headless always works if chromium is present
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        status["headless"] = True
    except Exception:
        pass

    # Headed needs a display
    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if sys.platform in ("win32", "darwin"):
        status["headed"] = True  # Always available on desktop OS
    elif display:
        status["headed"] = True
    else:
        # Check for Xvfb
        if shutil.which("xvfb-run") or shutil.which("Xvfb"):
            status["xvfb"] = True
            _ok("Xvfb available — headed mode works via virtual framebuffer")
            status["headed"] = True

    return status


def check_mcp_servers() -> None:
    """Verify MCP servers are importable."""
    servers = {
        "mcp.swarm_server": "HYDRA Swarm MCP",
        "mcp.scbe_server": "SCBE Crypto MCP",
        "mcp.orchestrator": "Orchestrator MCP",
    }
    # Just check files exist (importing requires mcp SDK)
    import os.path as osp
    root = osp.dirname(osp.dirname(osp.abspath(__file__)))
    for module, label in servers.items():
        fpath = osp.join(root, module.replace(".", "/") + ".py")
        if osp.exists(fpath):
            _ok(f"{label} ({module})")
        else:
            _warn(f"{label} not found at {fpath}")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"\n{_BOLD}SCBE-AETHERMOORE Browser Install Check{_RESET}")
    print("=" * 50)

    # 1. Python packages
    print(f"\n{_BOLD}Python packages:{_RESET}")
    missing = check_python_packages()

    # 2. Chromium
    print(f"\n{_BOLD}Browser binaries:{_RESET}")
    has_chromium = check_chromium()
    if not has_chromium and "playwright" not in missing:
        has_chromium = install_chromium()

    # 3. Dual-view status
    print(f"\n{_BOLD}Dual-view mode:{_RESET}")
    dv = check_dual_view()
    if dv["headless"]:
        _ok("Headless mode: READY")
    else:
        _fail("Headless mode: NOT READY")
    if dv["headed"]:
        _ok("Headed mode: READY" + (" (via Xvfb)" if dv["xvfb"] else ""))
    else:
        _warn("Headed mode: requires DISPLAY (set DISPLAY=:0 or install Xvfb)")

    # 4. MCP servers
    print(f"\n{_BOLD}MCP servers (for AI tool-use):{_RESET}")
    check_mcp_servers()

    # 5. Summary
    print(f"\n{_BOLD}Quick-start commands:{_RESET}")
    print("  python scripts/hydra_quick_start.py scrape <url>     # single scrape")
    print("  python scripts/hydra_quick_start.py swarm <task>     # 6-agent swarm")
    print("  python scripts/hydra_quick_start.py server           # API server")
    print("  python mcp/swarm_server.py                           # MCP for AI tools")

    all_ok = not missing and has_chromium
    print()
    if all_ok:
        print(f"{_GREEN}{_BOLD}All systems go. HYDRA browser is ready.{_RESET}")
    else:
        print(f"{_YELLOW}{_BOLD}Some items need attention (see above).{_RESET}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
