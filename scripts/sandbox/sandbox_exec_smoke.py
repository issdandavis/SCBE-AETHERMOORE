#!/usr/bin/env python3
"""Sandbox-only end-to-end smoke for the GeoSeal execution gate.

Exercises the EXECUTION path (execute_governed_command): a benign command
actually runs, and destructive commands are confirmed REFUSED (ran=False) so
they never execute. Note: nothing destructive ever runs even here — the gate
denies it before any subprocess starts; the container is just belt-and-suspenders.

DOUBLE-GUARD: refuses to run unless SCBE_SANDBOX=1, which only the sandbox
Docker image and the CI runner set. So this can never execute on a dev host —
run it through scripts/sandbox/run-geoseal-gate-sandbox.sh or in CI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if os.environ.get("SCBE_SANDBOX") != "1":
    print(
        "refusing to run on this host: set SCBE_SANDBOX=1 (only the sandbox "
        "container / CI runner does this). Use scripts/sandbox/run-geoseal-gate-sandbox.sh.",
        file=sys.stderr,
    )
    raise SystemExit(3)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.crypto.geoseal_execution_gate import (  # noqa: E402  (after the host guard)
    execute_governed_command,
    simulate_command,
)

# Destructive shapes/payloads the gate MUST refuse. Built from parts so the
# literal strings never appear in a shell/agent command line that runs this file.
_DANGER = [
    " ".join(["rm", "-rf", "/tmp/scbe-sandbox-target"]),
    f"{sys.executable} -c \"import shutil; shutil.rmtree('/tmp/scbe-x')\"",
    "node -c \"require('child_process').execSync('id')\"",
]

failures: list[str] = []

# 1) benign command actually runs through the gate
benign = f"{sys.executable} -c \"print('sandbox-ok')\""
res = execute_governed_command(benign, max_tier="QUARANTINE", audit_log=None)
if not (res.ran and "sandbox-ok" in res.stdout):
    failures.append(f"benign command did not run: ran={res.ran} err={res.error!r}")

# 2) destructive commands are refused at the gate — never executed
for danger in _DANGER:
    res = execute_governed_command(danger, max_tier="QUARANTINE", audit_log=None)
    sim = simulate_command(danger, max_tier="QUARANTINE")
    if res.ran:
        failures.append(f"DANGER EXECUTED (should be blocked): {danger!r}")
    if sim.would_run:
        failures.append(f"simulate says would-run (should be blocked): {danger!r}")

if failures:
    print("SANDBOX SMOKE FAILED:")
    for line in failures:
        print(f"  - {line}")
    raise SystemExit(1)

print("sandbox smoke OK — benign command ran; all destructive commands refused (never executed)")
