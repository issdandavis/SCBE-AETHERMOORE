#!/usr/bin/env python3
"""Independently verify a completed E92 prospective result bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_prospective_verify import (  # noqa: E402
    verify_e92_prospective_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite verification: {output}")
    verification = verify_e92_prospective_bundle(args.bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(
        json.dumps(
            {key: verification[key] for key in ("status", "query_count", "error_count", "promotion")},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if verification["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
