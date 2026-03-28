"""SCBE-AETHERMOORE Onion Site — Tor hidden service for the research portal.

Serves the website from /tmp/aethermoorgames (or a specified directory)
as a Tor .onion hidden service. Two processes:
  1. A lightweight HTTP server on 127.0.0.1:8200
  2. Tor process mapping the hidden service to that port

Usage:
    python scripts/system/onion_site.py
    python scripts/system/onion_site.py --web-dir /tmp/aethermoorgames --port 8200
    python scripts/system/onion_site.py --generate-only  # Just generate the .onion address

First run: Tor generates the keypair and .onion address.
Subsequent runs: same .onion address (keys persist in config/tor/hidden_service/).
"""

from __future__ import annotations

import argparse
import http.server
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TOR_DIR = PROJECT_ROOT / "config" / "tor"
TORRC = TOR_DIR / "torrc"
HIDDEN_SERVICE_DIR = TOR_DIR / "hidden_service"
HOSTNAME_FILE = HIDDEN_SERVICE_DIR / "hostname"

DEFAULT_WEB_DIR = "/tmp/aethermoorgames"
DEFAULT_PORT = 8200


def find_tor() -> str:
    """Find the tor executable."""
    for candidate in ["tor", "tor.exe", "C:/ProgramData/chocolatey/bin/tor.exe"]:
        if shutil.which(candidate):
            return candidate
    raise FileNotFoundError("Tor not found. Install with: choco install tor")


def start_web_server(web_dir: str, port: int) -> http.server.HTTPServer:
    """Start a simple HTTP server serving the website directory."""
    os.chdir(web_dir)
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"  Web server running on 127.0.0.1:{port}")
    print(f"  Serving files from: {web_dir}")
    return server


def write_torrc(port: int) -> None:
    """Write the torrc config file."""
    hs_dir = str(HIDDEN_SERVICE_DIR).replace("\\", "/")
    log_path = str(TOR_DIR / "tor.log").replace("\\", "/")

    # Tor on Windows needs forward slashes and the directory must
    # have restricted permissions. We'll let Tor handle that.
    content = f"""# SCBE-AETHERMOORE Tor Hidden Service
HiddenServiceDir {hs_dir}
HiddenServicePort 80 127.0.0.1:{port}
SocksPort 9050
Log notice file {log_path}
DataDirectory {str(TOR_DIR / 'data').replace(chr(92), '/')}
"""
    TORRC.write_text(content, encoding="utf-8")


def start_tor() -> subprocess.Popen:
    """Start the Tor process with our torrc."""
    tor_bin = find_tor()
    torrc_path = str(TORRC).replace("\\", "/")

    # Create data directory
    data_dir = TOR_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    proc = subprocess.Popen(
        [tor_bin, "-f", torrc_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def wait_for_onion(timeout: int = 120) -> str:
    """Wait for Tor to generate the .onion hostname."""
    start = time.time()
    while time.time() - start < timeout:
        if HOSTNAME_FILE.exists():
            hostname = HOSTNAME_FILE.read_text(encoding="utf-8").strip()
            if hostname and ".onion" in hostname:
                return hostname
        time.sleep(2)
    raise TimeoutError(f"Tor did not generate .onion address within {timeout}s")


def main():
    parser = argparse.ArgumentParser(description="SCBE Onion Site")
    parser.add_argument("--web-dir", default=DEFAULT_WEB_DIR, help="Directory to serve")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Local HTTP port")
    parser.add_argument("--generate-only", action="store_true", help="Just show/generate the .onion address")
    args = parser.parse_args()

    print("=" * 60)
    print("  SCBE-AETHERMOORE ONION SITE")
    print("=" * 60)

    # Check if we already have an address
    if HOSTNAME_FILE.exists():
        existing = HOSTNAME_FILE.read_text(encoding="utf-8").strip()
        if existing:
            print(f"\n  Existing .onion address: {existing}")
            if args.generate_only:
                return

    # Verify web directory
    web_dir = Path(args.web_dir)
    if not web_dir.exists():
        # Fall back to docs/ in the repo
        web_dir = PROJECT_ROOT / "docs"
        if not web_dir.exists():
            print(f"  ERROR: Web directory not found: {args.web_dir}")
            sys.exit(1)
    print(f"\n  Web root: {web_dir}")

    # Write torrc
    write_torrc(args.port)
    print(f"  Torrc written: {TORRC}")

    # Start web server
    server = start_web_server(str(web_dir), args.port)

    # Start Tor
    print("\n  Starting Tor (first run may take 30-60 seconds)...")
    tor_proc = start_tor()

    # Handle shutdown
    def shutdown(sig, frame):
        print("\n  Shutting down...")
        tor_proc.terminate()
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for .onion address
    try:
        hostname = wait_for_onion()
        print("\n" + "=" * 60)
        print(f"  ONION SITE LIVE!")
        print(f"  Address: http://{hostname}")
        print(f"  Local:   http://127.0.0.1:{args.port}")
        print(f"  Web dir: {web_dir}")
        print("=" * 60)
        print("\n  Press Ctrl+C to stop.\n")

        # Stream Tor output
        while True:
            if tor_proc.stdout:
                line = tor_proc.stdout.readline()
                if line:
                    # Only show important lines
                    if any(k in line.lower() for k in ["bootstrapped", "error", "warn", "established"]):
                        print(f"  [tor] {line.strip()}")
            if tor_proc.poll() is not None:
                print("  Tor process exited.")
                break
            time.sleep(0.5)

    except TimeoutError as e:
        print(f"\n  ERROR: {e}")
        print("  Check config/tor/tor.log for details.")
        tor_proc.terminate()
        server.shutdown()
        sys.exit(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
