#!/usr/bin/env python3
"""Evaluate a six-view prime token catalog against explicit controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_benchmark import evaluate_catalog, load_benchmark  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--control-seed", type=int, action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    benchmark, benchmark_hash = load_benchmark(args.benchmark)
    result = evaluate_catalog(
        args.database,
        benchmark,
        benchmark_sha256=benchmark_hash,
        control_seeds=args.control_seed or (0, 1, 2),
        limit=args.limit,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "query_count", "gates")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
