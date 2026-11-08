#!/usr/bin/env python3
"""Build an immutable offline receipt for late-output route evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_benchmark import (  # noqa: E402
    build_late_output_route_evidence,
    load_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--control-seed", action="append", type=int, default=[])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite receipt: {output}")
    benchmark, benchmark_hash = load_benchmark(args.benchmark)
    receipt = build_late_output_route_evidence(
        args.catalog,
        benchmark,
        benchmark_sha256=benchmark_hash,
        control_seeds=args.control_seed or (11, 29, 47),
        limit=args.limit,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "query_count": receipt["query_count"],
                "promotion": receipt["promotion"],
                "output": str(output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
