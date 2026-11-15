"""Measure the lazy 21D/14-layer geometry of a frozen B256 token table."""

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
from python.scbe.token_layer_geometry import summarize_token_nest_layer_geometry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stream a frozen B256 token nest through the lazy 21D geometry "
            "and write aggregate evidence without copying fourteen tables."
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
    nest_receipt = build_b256_token_honeycomb(payload)
    summary = summarize_token_nest_layer_geometry(nest_receipt["nest"])
    body = {
        "source_table_sha256": nest_receipt["source_table"]["table_sha256"],
        "source_nest_sha256": nest_receipt["nest"]["nest_sha256"],
        "source_receipt_sha256": nest_receipt["receipt_sha256"],
        "layer_geometry": summary,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(body) + b"\n")
    print(
        f"wrote {output_path} tokens={summary['token_count']} "
        f"derived_points={summary['derived_point_count']} "
        f"max_radius={summary['maximum_radius']:.9f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
