#!/usr/bin/env python3
"""Fail-fast checks for the zero-cost local training profile.

Validates that every dataset path in `scbe-zero-cost-local-0.5b.json` exists
under the repo root so Colab/local emit steps do not die mid-run with missing files.

Usage:
    python scripts/system/preflight_zero_cost_training.py
    python scripts/system/preflight_zero_cost_training.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = (
    REPO_ROOT / "config" / "model_training" / "scbe-zero-cost-local-0.5b.json"
)


def _load_profile(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"profile must be a JSON object: {path}")
    return data


def _dataset_paths(profile: dict[str, Any]) -> list[str]:
    ds = profile.get("dataset") or {}
    if not isinstance(ds, dict):
        return []
    train = ds.get("train_files") or []
    eval_files = ds.get("eval_files") or []
    out: list[str] = []
    for item in list(train) + list(eval_files):
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _resolve_path(rel: str, dataset_root: str) -> Path:
    root = (dataset_root or ".").strip() or "."
    base = REPO_ROOT / root if root in (".", "") else REPO_ROOT / root
    return (
        (base / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
    )


def run_preflight(profile_path: Path) -> dict[str, Any]:
    profile = _load_profile(profile_path)
    profile_id = str(profile.get("profile_id", profile_path.stem))
    ds = profile.get("dataset") or {}
    dataset_root = str(ds.get("root", ".")) if isinstance(ds, dict) else "."

    checks: list[dict[str, Any]] = []
    missing: list[str] = []
    empty: list[str] = []

    for rel in _dataset_paths(profile):
        path = _resolve_path(rel, dataset_root)
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        ok = exists and size > 0
        checks.append(
            {
                "path": rel,
                "resolved": (
                    str(path.relative_to(REPO_ROOT))
                    if path.is_relative_to(REPO_ROOT)
                    else str(path)
                ),
                "exists": exists,
                "bytes": size,
                "ok": ok,
            }
        )
        if not exists:
            missing.append(rel)
        elif size == 0:
            empty.append(rel)

    result = {
        "schema_version": "scbe_zero_cost_preflight_v1",
        "profile_id": profile_id,
        "profile_path": str(profile_path.relative_to(REPO_ROOT)),
        "ok": not missing and not empty,
        "missing_count": len(missing),
        "empty_count": len(empty),
        "missing": missing,
        "empty": empty,
        "checks": checks,
        "fix_commands": {
            "consolidate_regularized_jsonl": "python scripts/system/consolidate_ai_training.py",
            "consolidate_with_remote_buckets": (
                "python scripts/system/consolidate_ai_training.py "
                "--include-kaggle --include-hf --include-cloud"
            ),
            "agentic_workbench": "npm run training:agentic-workbench",
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight zero-cost training dataset paths"
    )
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help="Path to scbe-zero-cost-local-0.5b.json (or compatible profile)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON only"
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = (REPO_ROOT / profile_path).resolve()
    if not profile_path.is_file():
        print(f"[preflight] profile not found: {profile_path}", file=sys.stderr)
        return 2

    result = run_preflight(profile_path)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "OK" if result["ok"] else "FAIL"
        print(f"[preflight] {status} profile={result['profile_id']}")
        print(
            f"  files checked={len(result['checks'])} "
            f"missing={result['missing_count']} empty={result['empty_count']}"
        )
        for c in result["checks"]:
            if not c["ok"]:
                print(f"  - {c['path']} -> {c['resolved']}", file=sys.stderr)
        if not result["ok"]:
            print("\n[preflight] Fix:", file=sys.stderr)
            print(
                f"  {result['fix_commands']['consolidate_regularized_jsonl']}",
                file=sys.stderr,
            )
            print(f"  {result['fix_commands']['agentic_workbench']}", file=sys.stderr)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
