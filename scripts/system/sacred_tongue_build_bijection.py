#!/usr/bin/env python3
"""CLI: prove Sacred Tongue byte bijection for a file or self-check."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

# Allow `python scripts/...` without PYTHONPATH if repo cwd is root
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crypto.sacred_tongue_payload_bijection import (
    prove_bytes_all_tongues,
    prove_dict,
)  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-check", action="store_true", help="Run bijection on a tiny fixture dict"
    )
    parser.add_argument(
        "--file", type=Path, help="Read raw bytes from file and round-trip all tongues"
    )
    parser.add_argument(
        "--json-file", type=Path, help="Read JSON object and prove canonical encoding"
    )
    args = parser.parse_args()

    if args.self_check:
        fixture = {
            "check": "sacred_tongue_bijection",
            "n": 6,
            "lanes": ["ko", "av", "ru", "ca", "um", "dr"],
        }
        out = prove_dict(fixture)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0 if out["ok"] else 1

    if args.json_file:
        obj = json.loads(args.json_file.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            print(json.dumps({"ok": False, "error": "root must be object"}, indent=2))
            return 1
        out = prove_dict(obj)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0 if out["ok"] else 1

    if args.file:
        data = args.file.read_bytes()
        out: dict[str, Any] = {
            "schema_version": "scbe_sacred_tongue_raw_bijection_v1",
            **prove_bytes_all_tongues(data),
        }
        out["ok"] = out["all_ok"]
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0 if out["ok"] else 1

    parser.error("specify --self-check, --file, or --json-file")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
