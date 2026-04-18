#!/usr/bin/env python3
"""Background watcher: polls Kaggle kernel every 2 min, alerts on status change."""

import subprocess
import sys
import time
from datetime import datetime, timezone

KERNEL = sys.argv[1] if len(sys.argv) > 1 else "issacizrealdavis/polly-auto-r8"
INTERVAL = int(sys.argv[2]) if len(sys.argv) > 2 else 120
ROUND_NAME = KERNEL.split("/polly-auto-")[-1]

def ts():
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

def get_status():
    r = subprocess.run(
        ["kaggle", "kernels", "status", KERNEL],
        capture_output=True, text=True,
    )
    out = r.stdout + r.stderr
    if "RUNNING" in out or "running" in out.lower():
        return "running"
    elif "complete" in out.lower():
        return "complete"
    elif "error" in out.lower() or "failed" in out.lower() or "FAILED" in out:
        return "error"
    elif "queued" in out.lower():
        return "queued"
    return out.strip()[:80]

def pull_output():
    dest = f"artifacts/kaggle_output/{KERNEL.split('/')[-1]}"
    r = subprocess.run(
        ["kaggle", "kernels", "output", KERNEL, "-p", dest],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(f"Pull warning: {r.stderr[:200]}")
    return dest

print(f"[{ts()}] Watching {KERNEL} every {INTERVAL}s")
print("-" * 60)

last_status = None
elapsed = 0

while True:
    status = get_status()

    if status != last_status:
        print(f"\n[{ts()}] STATUS CHANGED: {last_status!r} -> {status!r}")
        last_status = status

    if status == "complete":
        print(f"[{ts()}] DONE — pulling output...")
        dest = pull_output()
        print(f"[{ts()}] Output at: {dest}")
        print(f"\n>>> Push to HF: python scripts/kaggle_auto/launch.py --pull --round {ROUND_NAME}")
        sys.exit(0)
    elif status == "error":
        print(f"[{ts()}] KERNEL ERRORED — pulling whatever was written...")
        pull_output()
        print(f">>> Check logs at: https://www.kaggle.com/code/{KERNEL}")
        sys.exit(1)
    else:
        mins = elapsed // 60
        print(f"[{ts()}] {status} ({mins}m elapsed)", end="\r", flush=True)

    time.sleep(INTERVAL)
    elapsed += INTERVAL
