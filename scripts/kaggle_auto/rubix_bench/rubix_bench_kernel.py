#!/usr/bin/env python3
"""Kaggle kernel: Rubik's-Cube Coding System speed benchmark (free CPU).

Clones the public SCBE-AETHERMOORE repo and runs the polyglot emit-throughput
benchmark: one CA-opcode core -> all 18 language faces. No GPU needed.
"""

import os
import subprocess
import sys

os.environ.setdefault("PYTHONUTF8", "1")
WORK = "/kaggle/working/scbe"
REPO = "https://github.com/issdandavis/SCBE-AETHERMOORE.git"

if not os.path.isdir(WORK):
    subprocess.run(["git", "clone", "--depth", "1", REPO, WORK], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "numpy"], check=False)

env = dict(os.environ, PYTHONPATH=WORK)
print("=" * 56)
print("RUBIK'S-CUBE CODING SYSTEM — KAGGLE SPEED BENCHMARK")
print("=" * 56)
for n, L in [(5000, 12), (20000, 16)]:
    print(f"\n--- {n} programs x {L} ops ---", flush=True)
    subprocess.run(
        [sys.executable, "scripts/benchmark/rubix_cube_speed_benchmark.py", "--programs", str(n), "--len", str(L)],
        cwd=WORK,
        env=env,
        check=True,
    )
# machine + scale context
import multiprocessing
import platform

print(f"\nkaggle node: {platform.platform()}  cores={multiprocessing.cpu_count()}")
