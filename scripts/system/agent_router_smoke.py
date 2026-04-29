#!/usr/bin/env python3
"""Fast local/CI smoke tasks for the SCBE agent router.

These lanes are intentionally small enough for GitHub Actions dispatches and
disk-constrained local machines. Heavier training or full builds stay separate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(command: list[str], timeout: int = 120) -> dict[str, Any]:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def _path_check(path: str, kind: str = "file") -> dict[str, Any]:
    resolved = REPO_ROOT / path
    exists = resolved.is_dir() if kind == "dir" else resolved.is_file()
    return {
        "path": path,
        "kind": kind,
        "exists": exists,
        "bytes": resolved.stat().st_size if exists and resolved.is_file() else 0,
        "ok": exists,
    }


def _package_scripts() -> dict[str, Any]:
    path = REPO_ROOT / "package.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    scripts = package.get("scripts") or {}
    required = ["build", "typecheck", "test", "test:python", "training:hub"]
    return {
        "path": "package.json",
        "required": required,
        "missing": [name for name in required if name not in scripts],
        "ok": all(name in scripts for name in required),
    }


def coding_smoke() -> dict[str, Any]:
    command = [sys.executable, "scripts/benchmark/coding_system_industry_benchmark.py"]
    run = _run(command, timeout=180)
    parsed: dict[str, Any] = {}
    if run["stdout"].strip():
        try:
            parsed = json.loads(run["stdout"])
        except json.JSONDecodeError:
            parsed = {"parse_error": "benchmark stdout was not JSON"}
    return {
        "schema_version": "scbe_agent_router_coding_smoke_v1",
        "created_at": _utc_now(),
        "ok": run["ok"] and parsed.get("decision") == "PASS",
        "task": "coding",
        "lane": "agentic_coding_benchmark",
        "run": run,
        "benchmark": parsed,
    }


def system_build_smoke() -> dict[str, Any]:
    checks = [
        _path_check("package.json"),
        _path_check("tsconfig.json"),
        _path_check("api/_agent_common.js"),
        _path_check("api/agent/dispatch.js"),
        _path_check(".github/workflows/agent-router.yml"),
        _path_check("src", "dir"),
        _path_check("tests", "dir"),
    ]
    scripts = _package_scripts()
    node_checks = [
        _run(["node", "--check", "api/_agent_common.js"]),
        _run(["node", "--check", "api/agent/dispatch.js"]),
        _run(["node", "--check", "api/agent/health.js"]),
        _run(["node", "--check", "api/agent/status.js"]),
    ]
    py_compile = _run(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "agents",
            "scripts/system",
            "scripts/benchmark",
        ],
        timeout=180,
    )
    ok = (
        all(item["ok"] for item in checks)
        and scripts["ok"]
        and all(item["ok"] for item in node_checks)
        and py_compile["ok"]
    )
    return {
        "schema_version": "scbe_agent_router_system_build_smoke_v1",
        "created_at": _utc_now(),
        "ok": ok,
        "task": "system_build",
        "lane": "repo_entrypoint_and_syntax_smoke",
        "path_checks": checks,
        "package_scripts": scripts,
        "node_checks": node_checks,
        "python_compile": py_compile,
        "notes": [
            "Fast smoke only: no npm install, no full TypeScript compile, no generated artifact cleanup.",
            "Use npm run build and npm run test:all as the heavier promotion gate.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SCBE agent-router smoke tasks.")
    parser.add_argument("task", choices=["coding", "system_build"])
    args = parser.parse_args()

    result = coding_smoke() if args.task == "coding" else system_build_smoke()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
