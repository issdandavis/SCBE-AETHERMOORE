"""
AetherBrowser Launcher
=======================

One command to boot the entire AetherBrowser stack:
1. Starts Chrome with CDP debugging on port 9222
2. Starts the FastAPI server on port 8002
3. Opens the Swagger docs in Chrome

Usage:
    python scripts/launch_aetherbrowser.py
    python scripts/launch_aetherbrowser.py --no-chrome    # server only
    python scripts/launch_aetherbrowser.py --port 9999    # custom server port
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import signal
import subprocess
import sys
import time


# Chrome paths by platform
_CHROME_PATHS_WIN = [
    os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Dev\Application\chrome.exe"),
]

_CHROME_PATHS_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev",
]

_CHROME_PATHS_LINUX = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]


def find_chrome() -> str | None:
    """Find Chrome executable on this system."""
    if platform.system() == "Windows":
        paths = _CHROME_PATHS_WIN
    elif platform.system() == "Darwin":
        paths = _CHROME_PATHS_MAC
    else:
        paths = _CHROME_PATHS_LINUX

    for p in paths:
        if os.path.isfile(p):
            return p

    # Try PATH
    chrome = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
    return chrome


def start_chrome(cdp_port: int = 9222, profile_dir: str | None = None) -> subprocess.Popen | None:
    """Start Chrome with CDP debugging enabled."""
    chrome = find_chrome()
    if not chrome:
        print("[LAUNCH] Chrome not found. Install Chrome or use --no-chrome")
        return None

    if profile_dir is None:
        profile_dir = os.path.join(os.path.expanduser("~"), ".aetherbrowser-profile")

    args = [
        chrome,
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-size=1280,900",
        "about:blank",
    ]

    print(f"[LAUNCH] Starting Chrome on CDP port {cdp_port}")
    print(f"[LAUNCH] Profile: {profile_dir}")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # Give Chrome time to start
    return proc


def start_server(port: int = 8002) -> subprocess.Popen:
    """Start the AetherBrowser FastAPI server."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    args = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.aetherbrowser.serve:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    print(f"[LAUNCH] Starting AetherBrowser server on port {port}")
    proc = subprocess.Popen(
        args,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(2)  # Give server time to start
    return proc


def check_server(port: int = 8002) -> bool:
    """Check if the server is healthy."""
    import urllib.request

    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
        return resp.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Launch AetherBrowser")
    parser.add_argument("--no-chrome", action="store_true", help="Server only, no Chrome")
    parser.add_argument("--port", type=int, default=8002, help="Server port (default: 8002)")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome CDP port (default: 9222)")
    parser.add_argument("--open-docs", action="store_true", default=True, help="Open API docs in browser")
    args = parser.parse_args()

    procs: list[subprocess.Popen] = []

    def cleanup(sig=None, frame=None):
        print("\n[LAUNCH] Shutting down...")
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=" * 60)
    print("  AetherBrowser — Governed 3-Lane Browser Service")
    print("  SCBE-AETHERMOORE by Issac Daniel Davis")
    print("=" * 60)
    print()

    # 1. Start Chrome
    chrome_proc = None
    if not args.no_chrome:
        chrome_proc = start_chrome(args.cdp_port)
        if chrome_proc:
            procs.append(chrome_proc)
        else:
            print("[LAUNCH] Continuing without Chrome (headless lane won't connect)")

    # 2. Start server
    server_proc = start_server(args.port)
    procs.append(server_proc)

    # 3. Check health
    healthy = False
    for attempt in range(5):
        if check_server(args.port):
            healthy = True
            break
        time.sleep(1)

    if healthy:
        print()
        print(f"[LAUNCH] AetherBrowser is LIVE")
        print(f"         Health:    http://127.0.0.1:{args.port}/health")
        print(f"         API Docs:  http://127.0.0.1:{args.port}/docs")
        print(f"         Classify:  http://127.0.0.1:{args.port}/v1/browse/classify?task=your+task")
        print(f"         Browse:    POST http://127.0.0.1:{args.port}/v1/browse")
        print(f"         Stats:     http://127.0.0.1:{args.port}/v1/browse/stats")
        if chrome_proc:
            print(f"         Chrome:    CDP on port {args.cdp_port}")
        print()
        print("  Press Ctrl+C to stop")
        print()

        # Open docs in browser
        if args.open_docs and chrome_proc:
            try:
                import webbrowser

                webbrowser.open(f"http://127.0.0.1:{args.port}/docs")
            except Exception:
                pass
    else:
        print("[LAUNCH] Server failed to start. Check logs above.")
        cleanup()

    # Wait for server to exit
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
