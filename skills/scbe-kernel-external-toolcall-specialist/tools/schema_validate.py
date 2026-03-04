#!/usr/bin/env python3
"""Validate JSON/YAML data against a JSON schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import jsonschema

try:
    import yaml
except Exception:  # noqa: BLE001
    yaml = None


def load_data(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required for YAML input")
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("input must decode to an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema validation utility")
    parser.add_argument("--schema", required=True, help="path to schema .json file")
    parser.add_argument("--input", required=True, help="path to json/yaml input file")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    input_path = Path(args.input)

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = load_data(input_path)

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)

    if errors:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema": str(schema_path),
                    "input": str(input_path),
                    "errors": [
                        {
                            "message": err.message,
                            "path": list(err.path),
                        }
                        for err in errors
                    ],
                },
                indent=2,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "schema": str(schema_path),
                "input": str(input_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
