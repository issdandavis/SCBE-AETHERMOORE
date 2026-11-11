#!/usr/bin/env python3
"""Build an immutable, target-invariant prime-token material case bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.prime_token_material_cases import build_material_case_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--source-family-audit", required=True, type=Path)
    parser.add_argument("--source-queue", required=True, type=Path)
    parser.add_argument("--closed-source-snapshot", required=True, type=Path)
    parser.add_argument("--ordinary-source", required=True, type=Path)
    parser.add_argument("--retention-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-final-test", type=int, default=30)
    parser.add_argument("--maximum-source-fraction", type=float, default=0.40)
    parser.add_argument("--maximum-family-fraction", type=float, default=0.60)
    parser.add_argument("--max-query-bytes", type=int, default=510)
    parser.add_argument("--start-token-id", type=int, default=224)
    args = parser.parse_args()
    receipt = build_material_case_bundle(
        benchmark_path=args.benchmark,
        source_family_audit_path=args.source_family_audit,
        source_queue_path=args.source_queue,
        closed_source_snapshot_path=args.closed_source_snapshot,
        ordinary_source_path=args.ordinary_source,
        retention_source_path=args.retention_source,
        output_dir=args.output,
        minimum_final_test=args.minimum_final_test,
        maximum_source_fraction=args.maximum_source_fraction,
        maximum_family_fraction=args.maximum_family_fraction,
        max_query_bytes=args.max_query_bytes,
        start_token_id=args.start_token_id,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
