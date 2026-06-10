#!/usr/bin/env python3
"""Deployment readiness gate for SCBE runtime surfaces.

This script is intentionally strict about runtime/deployment boundaries and can
optionally run a small smoke test lane.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _run_cmd(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to start command: {exc}"
    if completed.returncode == 0:
        return True, (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    tail = stderr if stderr else stdout
    return False, f"exit={completed.returncode}: {tail[-600:]}"


def _exists(repo_root: Path, rel: str) -> CheckResult:
    path = repo_root / rel
    return CheckResult(name=f"exists:{rel}", ok=path.exists(), detail=str(path))


def _check_deploy_profile(repo_root: Path) -> CheckResult:
    profile_file = repo_root / "config" / "offline_bundle_profiles.json"
    if not profile_file.exists():
        return CheckResult("offline_bundle_profile", False, "config/offline_bundle_profiles.json missing")
    try:
        payload = json.loads(profile_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CheckResult("offline_bundle_profile", False, f"invalid JSON: {exc}")
    profiles = payload.get("profiles", {})
    if "deploy-runtime-core" not in profiles:
        return CheckResult("offline_bundle_profile", False, "missing profiles.deploy-runtime-core")
    return CheckResult("offline_bundle_profile", True, "deploy-runtime-core present")


def run_gate(repo_root: Path, run_smoke: bool) -> dict[str, object]:
    checks: list[CheckResult] = [
        _exists(repo_root, "docs/specs/CANONICAL_SYSTEM_STATE.md"),
        _exists(repo_root, "docs/specs/CANONICAL_FORMULA_REGISTRY.md"),
        _exists(repo_root, "docs/specs/MASTER_ARCHITECTURE_CONTRACT_21D_M4_SQUAD.md"),
        _exists(repo_root, "api/main.py"),
        _exists(repo_root, "src/api/main.py"),
        _exists(repo_root, "scripts/scbe-system-cli.py"),
        _check_deploy_profile(repo_root),
    ]

    smoke_results: list[CheckResult] = []
    if run_smoke:
        ok_compile, detail_compile = _run_cmd([sys.executable, "-m", "py_compile", "scripts/scbe-system-cli.py"], repo_root)
        smoke_results.append(CheckResult("smoke:compile_scbe_system_cli", ok_compile, detail_compile))

        ok_test, detail_test = _run_cmd(
            [sys.executable, "-m", "pytest", "tests/test_hypersphere_index.py", "tests/test_spin_voxel.py", "-q"],
            repo_root,
        )
        smoke_results.append(CheckResult("smoke:prototype_tests", ok_test, detail_test))

    all_checks = checks + smoke_results
    passed = all(result.ok for result in all_checks)
    payload = {
        "schema_version": "scbe_deployment_readiness_gate_v1",
        "repo_root": str(repo_root),
        "run_smoke": run_smoke,
        "passed": passed,
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in all_checks],
        "failed_checks": [c.name for c in all_checks if not c.ok],
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCBE deployment readiness checks.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-smoke", action="store_true", help="Run compile + focused prototype tests")
    parser.add_argument("--output", default="artifacts/deploy/deployment_readiness_gate.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    payload = run_gate(repo_root=repo_root, run_smoke=bool(args.run_smoke))

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
