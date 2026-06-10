#!/usr/bin/env python3
"""Check whether this machine can run official SWE-bench Verified locally."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "artifacts" / "swe_verified_readiness"


def _probe(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    exe = shutil.which(cmd[0])
    if exe is None:
        return {"ok": False, "command": cmd, "reason": "missing_executable"}
    run_cmd = cmd
    if sys.platform == "win32" and exe.lower().endswith((".bat", ".cmd")):
        run_cmd = ["cmd", "/c"] + cmd
    try:
        proc = subprocess.run(
            run_cmd,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "command": cmd, "reason": "missing_executable", "error": str(exc)}
    return {
        "ok": proc.returncode == 0,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-1000:],
        "stderr_tail": proc.stderr[-1000:],
    }


def main() -> int:
    probes = {
        "python": _probe([sys.executable, "--version"]),
        "git": _probe(["git", "--version"]),
        "docker": _probe(["docker", "--version"]),
        "swebench_harness": _probe(
            [sys.executable, "-m", "swebench.harness.run_evaluation", "--help"], timeout=60
        ),
    }
    missing = [name for name, row in probes.items() if not row.get("ok")]
    payload = {
        "schema_version": "scbe_swe_bench_verified_readiness_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": not missing,
        "official_swe_bench_verified_local_ready": not missing,
        "claim_boundary": "readiness_only_no_official_score",
        "missing_or_failed": missing,
        "probes": probes,
        "next_step": (
            "run official SWE-bench harness"
            if not missing
            else "install missing prerequisites or use a GitHub Actions/Linux runner with Docker"
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
