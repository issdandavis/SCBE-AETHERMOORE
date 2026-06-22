#!/usr/bin/env python3
"""
Safe single-process driver for the cold_spot × gradient_abs grid sweep
on prime_fog_of_war_probe.py.

Usage:
  python scripts/research/run_thermal_grid_sweep.py --limit 50000000

It runs one profile at a time, monitors memory, skips completed, writes results.
"""

import subprocess
import time
import json
import psutil
from pathlib import Path
from itertools import product
from datetime import datetime

GRID = list(product([2, 3, 4], [3, 4, 5, 6]))  # (cold_spot, gradient_abs)

BASE_CMD = [
    "python",
    "scripts/research/prime_fog_of_war_probe.py",
    "--imaginary-paths-limit",
    "50000000",
    "--field-scan",
]

OUT_DIR = Path("artifacts/prime_fog_sweep")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def mem_available_gb() -> float:
    return psutil.virtual_memory().available / (1024**3)


def run_profile(cold: int, gabs: int, limit_gb: float = 10.0, timeout_min: int = 60):
    profile = f"igct_c{cold}_g{gabs}"
    out_file = OUT_DIR / f"{profile}.jsonl"

    if out_file.exists():
        print(f"[skip] {profile} already done")
        return "skipped"

    cmd = BASE_CMD + ["--field-scan-profile", profile]
    print(f"\n=== Starting {profile} at {datetime.now().isoformat()} ===")
    print("Command:", " ".join(cmd))

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    start = time.time()
    lines = []

    try:
        for line in proc.stdout:
            lines.append(line.rstrip())
            print(line.rstrip())
            if mem_available_gb() < limit_gb:
                print(f"[WARN] Memory low ({mem_available_gb():.1f}GB). Killing {profile}")
                proc.kill()
                break
            if (time.time() - start) > timeout_min * 60:
                print(f"[WARN] Timeout for {profile}")
                proc.kill()
                break
    finally:
        if proc.poll() is None:
            proc.kill()

    rc = proc.wait()
    duration = time.time() - start

    result = {
        "profile": profile,
        "cold_spot": cold,
        "gradient_abs": gabs,
        "returncode": rc,
        "duration_sec": round(duration, 1),
        "timestamp": datetime.now().isoformat(),
        "last_lines": lines[-30:] if lines else [],
    }

    with open(OUT_DIR / f"{profile}.result.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"=== Finished {profile} rc={rc} in {duration:.1f}s ===\n")
    time.sleep(8)  # breathing room
    return result


if __name__ == "__main__":
    print("Thermal grid sweep driver")
    print(f"Grid size: {len(GRID)}")
    print(f"Output dir: {OUT_DIR}")

    results = []
    for cold, gabs in GRID:
        res = run_profile(cold, gabs)
        results.append(res)

    # Simple summary
    print("\n=== SWEEP SUMMARY ===")
    for r in results:
        if isinstance(r, dict):
            print(f"{r['profile']}: rc={r['returncode']} t={r['duration_sec']}s")
    print("Done. Check artifacts/prime_fog_sweep/ for results.")
