#!/usr/bin/env python3
"""
Validate docs/scbe_full_system_layer_manifest.json.

This validator is intentionally dependency-free (stdlib only) so it can run in CI
without extra package installs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "scbe_full_system_layer_manifest.json"
SCHEMA_PATH = ROOT / "docs" / "scbe_full_system_layer_manifest.schema.json"

STATUS_ALLOWED = {
    "implemented",
    "implemented_with_config",
    "partial",
    "conceptual",
}

LAYER_ID_RE = re.compile(r"^L\d+$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"Missing required file: {path}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SCBE layer manifest")
    parser.add_argument(
        "--strict-local-paths",
        action="store_true",
        help="Fail if local path references for canonical repo layers do not exist",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    try:
        # Presence + parse check for schema document itself.
        _ = _load_json(SCHEMA_PATH)
        manifest = _load_json(MANIFEST_PATH)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    required_top = {
        "schema_version",
        "generated_at_utc",
        "canonical_repo",
        "layers",
        "consolidation_priorities",
        "secret_dependencies",
    }
    missing_top = required_top - set(manifest.keys())
    if missing_top:
        errors.append(f"Top-level keys missing: {sorted(missing_top)}")

    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or not SEMVER_RE.match(schema_version):
        errors.append("schema_version must be semver (e.g., 1.1.0)")

    layers = manifest.get("layers")
    if not isinstance(layers, list) or not layers:
        errors.append("layers must be a non-empty array")
        layers = []

    layer_ids: list[str] = []
    for idx, layer in enumerate(layers):
        loc = f"layers[{idx}]"
        if not isinstance(layer, dict):
            errors.append(f"{loc} must be an object")
            continue

        for key in ("id", "name", "status", "repos", "paths", "depends_on", "last_verified_commit"):
            if key not in layer:
                errors.append(f"{loc} missing key: {key}")

        layer_id = layer.get("id")
        if not isinstance(layer_id, str) or not LAYER_ID_RE.match(layer_id):
            errors.append(f"{loc}.id must match pattern L<integer>")
        else:
            layer_ids.append(layer_id)

        status = layer.get("status")
        if status not in STATUS_ALLOWED:
            errors.append(f"{loc}.status must be one of {sorted(STATUS_ALLOWED)}")

        repos = layer.get("repos")
        if not isinstance(repos, list) or not repos or not all(isinstance(x, str) and x for x in repos):
            errors.append(f"{loc}.repos must be a non-empty array of strings")

        paths = layer.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(x, str) and x for x in paths):
            errors.append(f"{loc}.paths must be a non-empty array of strings")
        elif isinstance(manifest.get("canonical_repo"), str) and manifest["canonical_repo"] in repos:
            for path in paths:
                if path.startswith("phdm-21d-embedding/"):
                    continue
                if path.startswith("spiralverse-protocol/"):
                    continue
                if path.startswith("scbe-security-gate/"):
                    continue
                if path.startswith("scbe-aethermoore-demo/"):
                    continue
                local = ROOT / path
                if not local.exists():
                    msg = f"{loc}.paths local reference not found: {path}"
                    if args.strict_local_paths:
                        errors.append(msg)
                    else:
                        warnings.append(msg)

        depends_on = layer.get("depends_on")
        if not isinstance(depends_on, list) or not all(isinstance(x, str) and LAYER_ID_RE.match(x) for x in depends_on):
            errors.append(f"{loc}.depends_on must be an array of layer IDs")

        lvc = layer.get("last_verified_commit")
        if lvc is not None and (not isinstance(lvc, str) or not COMMIT_RE.match(lvc)):
            errors.append(f"{loc}.last_verified_commit must be null or a git commit hash")

    dup_ids = sorted({layer_id for layer_id in layer_ids if layer_ids.count(layer_id) > 1})
    if dup_ids:
        errors.append(f"Duplicate layer IDs found: {dup_ids}")

    id_set = set(layer_ids)
    for idx, layer in enumerate(layers):
        for dep in layer.get("depends_on", []):
            if dep not in id_set:
                errors.append(f"layers[{idx}].depends_on references unknown layer: {dep}")

    if errors:
        print("Manifest validation failed:")
        for err in errors:
            print(f"  - {err}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1

    print("Manifest validation passed.")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
