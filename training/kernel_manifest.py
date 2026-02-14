#!/usr/bin/env python3
"""Kernel manifest utilities for training provenance.

This script validates and prints the canonical kernel file set so CI/training
pipelines know exactly which files define the model surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def load_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path else Path(__file__).with_name("kernel_manifest.yaml")
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "kernel" not in data:
        raise ValueError("Invalid manifest format: expected top-level 'kernel' list")

    if not isinstance(data["kernel"], list):
        raise ValueError("Invalid manifest format: 'kernel' must be a list")

    return data


def validate_manifest_entries(manifest: dict[str, Any], repo_root: str | Path = ".") -> list[str]:
    root = Path(repo_root)
    missing: list[str] = []
    for entry in manifest["kernel"]:
        if not isinstance(entry, str):
            missing.append(str(entry))
            continue
        if not (root / entry).exists():
            missing.append(entry)
    return missing


def compute_manifest_sha(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest["kernel"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def to_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": manifest.get("version", 1),
        "kernel_file_count": len(manifest["kernel"]),
        "kernel_manifest_sha": compute_manifest_sha(manifest),
        "kernel": manifest["kernel"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/print SCBE kernel manifest")
    parser.add_argument("--manifest", default=None, help="Path to manifest YAML")
    parser.add_argument("--check", action="store_true", help="Validate file existence")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)

    if args.check:
        missing = validate_manifest_entries(manifest)
        if missing:
            print("Missing kernel files:")
            for path in missing:
                print(f" - {path}")
            return 1

    summary = to_summary(manifest)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Kernel manifest v{summary['version']}")
        print(f"Files: {summary['kernel_file_count']}")
        print(f"SHA: {summary['kernel_manifest_sha']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
