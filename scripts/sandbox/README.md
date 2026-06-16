# GeoSeal gate sandbox

A throwaway test surface for the GeoSeal **execution gate** — so the path that
actually launches subprocesses (`execute_governed_command`) is never exercised
on a real machine.

## Why a sandbox at all?
For most gate testing you **don't need one**: a blocked command is proven by
`scan_command` / `simulate_command` returning `DENY` / `would_run=False` — pure
analysis, no execution (see `tests/crypto/test_geoseal_execution_gate.py` and
`geoseal simulate`). The sandbox is only for exercising the *execution* path
end-to-end (benign commands actually run; destructive ones are confirmed
refused). Even here, nothing destructive ever runs — the gate denies it before
any subprocess starts. The container is belt-and-suspenders.

## Two surfaces

### 1. Local — Docker (fast loop)
```bash
scripts/sandbox/run-geoseal-gate-sandbox.sh        # bash
scripts/sandbox/run-geoseal-gate-sandbox.ps1       # Windows PowerShell
```
Runs `--rm --network none --cap-drop ALL --security-opt no-new-privileges`, as an
unprivileged user. Anything that runs only touches the container, destroyed on exit.
(For extra hardening you can add `--read-only --tmpfs /tmp`.)

### 2. External — GitHub Actions (repeatable)
`.github/workflows/geoseal-gate.yml` runs the same tests on an ephemeral runner
that GitHub destroys after the job — a true "outside the system" surface. Triggers
on changes to the gate/CLI/tests/sandbox, and via **workflow_dispatch**.

## Safety guards
- `sandbox_exec_smoke.py` refuses to run unless `SCBE_SANDBOX=1` (set only by the
  container image and CI) — so it can't execute on a dev host.
- `SCBE_FORCE_SKIP_LIBOQS=1` lets the PQC code import without the liboqs C lib.
- The smoke asserts: a benign command runs, and `rm -rf …`, `shutil.rmtree(…)`,
  and node `child_process` are all **refused** (never executed).

## What it does NOT do
It does not run destructive commands for real anywhere. The point is to confirm
the gate **stops** them at the execution boundary — in a place where, even if a
future regression let one through, it would hit a throwaway container/VM, not you.
