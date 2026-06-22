#!/usr/bin/env python3
"""Audit the repo release-surface contract.

This is a lightweight packaging guard. It does not run the expensive builds.
It verifies that every declared release surface has owner files, workflows,
required paths, and npm script references that actually exist.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "release_surfaces.v1.json"
VALID_STATUS = {"ship", "preview", "internal", "deprecated"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _npm_scripts() -> set[str]:
    package_json = REPO_ROOT / "package.json"
    if not package_json.exists():
        return set()
    payload = _load_json(package_json)
    scripts = payload.get("scripts", {})
    if not isinstance(scripts, dict):
        return set()
    return set(scripts)


def _script_from_command(command: str) -> str | None:
    match = re.match(r"^npm\s+run\s+([A-Za-z0-9:_@./-]+)(?:\s|$)", command.strip())
    if not match:
        return None
    return match.group(1)


def audit(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = _load_json(config_path)
    scripts = _npm_scripts()
    errors: list[str] = []
    warnings: list[str] = []
    surface_reports: list[dict[str, Any]] = []

    if payload.get("schema") != "scbe_release_surfaces_v1":
        errors.append(f"{config_path}: unsupported schema {payload.get('schema')!r}")

    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append(f"{config_path}: surfaces must be a non-empty list")
        surfaces = []

    seen_ids: set[str] = set()
    for index, surface in enumerate(surfaces):
        sid = str(surface.get("id", "")).strip()
        prefix = sid or f"surface[{index}]"
        if not sid:
            errors.append(f"{prefix}: missing id")
        elif sid in seen_ids:
            errors.append(f"{prefix}: duplicate id")
        seen_ids.add(sid)

        status = surface.get("status")
        if status not in VALID_STATUS:
            errors.append(f"{prefix}: invalid status {status!r}; expected one of {sorted(VALID_STATUS)}")

        repo = surface.get("repo", "SCBE-AETHERMOORE")
        is_local_scbe = repo == "SCBE-AETHERMOORE"
        missing_paths: list[str] = []
        missing_scripts: list[str] = []

        for field in ("owner_files", "required_paths", "workflows"):
            values = surface.get(field, [])
            if not isinstance(values, list):
                errors.append(f"{prefix}: {field} must be a list")
                continue
            if field == "owner_files" and not values:
                errors.append(f"{prefix}: owner_files must not be empty")
            if not is_local_scbe:
                continue
            for rel in values:
                if not isinstance(rel, str):
                    errors.append(f"{prefix}: {field} contains a non-string value")
                    continue
                if not (REPO_ROOT / rel).exists():
                    missing_paths.append(rel)

        for field in ("build_commands", "verification_commands"):
            values = surface.get(field, [])
            if not isinstance(values, list):
                errors.append(f"{prefix}: {field} must be a list")
                continue
            for command in values:
                if not isinstance(command, str):
                    errors.append(f"{prefix}: {field} contains a non-string value")
                    continue
                script_name = _script_from_command(command)
                if script_name and is_local_scbe and script_name not in scripts:
                    missing_scripts.append(script_name)

        for rel in missing_paths:
            errors.append(f"{prefix}: missing path {rel}")
        for script_name in missing_scripts:
            errors.append(f"{prefix}: package.json missing script {script_name}")

        if not is_local_scbe:
            warnings.append(f"{prefix}: external repo surface; local path checks skipped")

        surface_reports.append(
            {
                "id": prefix,
                "repo": repo,
                "status": status,
                "missing_paths": missing_paths,
                "missing_scripts": missing_scripts,
            }
        )

    return {
        "ok": not errors,
        "config": str(config_path),
        "surface_count": len(surface_reports),
        "errors": errors,
        "warnings": warnings,
        "surfaces": surface_reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit SCBE release-surface packaging contract.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to release surface config JSON.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    report = audit(Path(args.config))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = "PASS" if report["ok"] else "FAIL"
        print(f"release_surface_audit: {status} ({report['surface_count']} surfaces)")
        for warning in report["warnings"]:
            print(f"WARN: {warning}")
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
