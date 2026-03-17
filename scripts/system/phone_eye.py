#!/usr/bin/env python3
"""Phone Eye — continuous screenshot capture for AI vision.

Captures the emulator screen every N seconds to a fixed file path
so the AI agent can read the latest frame anytime.

Usage:
    python scripts/system/phone_eye.py              # 2 sec interval
    python scripts/system/phone_eye.py --interval 1 # 1 sec interval
    python scripts/system/phone_eye.py --once        # single shot
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADB = str(REPO_ROOT / "android-sdk" / "platform-tools" / "adb.exe")
OUT_DIR = REPO_ROOT / "artifacts" / "kindle" / "emulator"
LATEST = OUT_DIR / "eye_latest.png"
HISTORY_DIR = OUT_DIR / "eye_history"


def capture(save_history: bool = False) -> bool:
    """Capture one screenshot. Returns True on success."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [ADB, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0 and len(result.stdout) > 1000:
            LATEST.write_bytes(result.stdout)
            if save_history:
                HISTORY_DIR.mkdir(parents=True, exist_ok=True)
                ts = time.strftime("%Y%m%dT%H%M%S")
                (HISTORY_DIR / f"frame_{ts}.png").write_bytes(result.stdout)
            return True
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)
    return False


def run_loop(interval: float = 2.0, save_history: bool = False):
    """Continuous capture loop."""
    print(f"Phone Eye running — {interval}s interval — {LATEST}")
    print("Ctrl+C to stop")
    frames = 0
    while True:
        if capture(save_history):
            frames += 1
            print(f"\rFrame {frames} captured", end="", flush=True)
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Phone Eye — continuous emulator screenshots")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between captures")
    parser.add_argument("--once", action="store_true", help="Single capture then exit")
    parser.add_argument("--history", action="store_true", help="Save timestamped history frames")
    args = parser.parse_args()

    if args.once:
        if capture(args.history):
            print(f"Saved: {LATEST}")
        else:
            print("Capture failed", file=sys.stderr)
            return 1
        return 0

    try:
        run_loop(args.interval, args.history)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
