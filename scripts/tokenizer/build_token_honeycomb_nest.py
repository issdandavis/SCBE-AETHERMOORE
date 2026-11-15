"""Build a collision-safe weighted nest for a frozen B256 token table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.intermodel_token_ledger import canonical_json
from python.scbe.token_honeycomb_nest import build_b256_token_honeycomb


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Place a hash-pinned B256 vocabulary into weight-derived radial "
            "cells with unique honeycomb sub-addresses."
        )
    )
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    table_path = args.table.resolve()
    output_path = args.output.resolve()
    if not table_path.is_file():
        raise SystemExit(f"B256 table does not exist: {table_path}")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output_path}")
    payload = json.loads(table_path.read_text(encoding="utf-8", errors="strict"))
    receipt = build_b256_token_honeycomb(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(receipt) + b"\n")
    metrics = receipt["nest"]["metrics"]
    print(
        f"wrote {output_path} tokens={metrics['token_count']} "
        f"radial_collisions={metrics['radial_collision_token_count']} "
        f"address_collisions={metrics['nested_address_collision_count']} "
        f"sha256={receipt['receipt_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
