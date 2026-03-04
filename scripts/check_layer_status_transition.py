#!/usr/bin/env python3
"""
Enforce allowed layer status transitions against a baseline manifest.

Policy:
- Same status: allowed
- Upgrades: allowed
- Downgrades: blocked
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STATUS_ORDER = {
    "conceptual": 0,
    "partial": 1,
    "implemented_with_config": 2,
    "implemented": 3,
}


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to load JSON: {path} ({exc})")


def _layer_map(doc: dict) -> dict[str, dict]:
    layers = doc.get("layers", [])
    if not isinstance(layers, list):
        raise RuntimeError("Manifest 'layers' must be an array")
    result: dict[str, dict] = {}
    for layer in layers:
        layer_id = layer.get("id")
        if isinstance(layer_id, str):
            result[layer_id] = layer
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check manifest layer status transitions")
    parser.add_argument("--base", required=True, help="Baseline manifest path")
    parser.add_argument("--current", required=True, help="Current manifest path")
    args = parser.parse_args()

    base_path = Path(args.base)
    current_path = Path(args.current)

    try:
        base = _load(base_path)
        current = _load(current_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    base_layers = _layer_map(base)
    current_layers = _layer_map(current)

    errors: list[str] = []

    for layer_id, base_layer in base_layers.items():
        if layer_id not in current_layers:
            errors.append(f"Layer removed from current manifest: {layer_id}")
            continue

        base_status = base_layer.get("status")
        curr_status = current_layers[layer_id].get("status")

        if base_status not in STATUS_ORDER:
            errors.append(f"Unknown baseline status for {layer_id}: {base_status}")
            continue
        if curr_status not in STATUS_ORDER:
            errors.append(f"Unknown current status for {layer_id}: {curr_status}")
            continue

        if STATUS_ORDER[curr_status] < STATUS_ORDER[base_status]:
            errors.append(
                f"Downgrade blocked for {layer_id}: {base_status} -> {curr_status}"
            )

    if errors:
        print("Layer status transition check failed:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Layer status transitions are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
