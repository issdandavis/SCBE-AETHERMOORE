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

from python.scbe.prime_token_benchmark import (  # noqa: E402
    audit_benchmark_disjointness,
    evaluate_catalog,
    evaluate_explicit_routed_catalog,
    evaluate_late_output_fused_catalog,
    evaluate_lexical_banded_catalog,
    evaluate_lexical_first_catalog,
    load_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--control-seed", type=int, action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--candidate",
        choices=(
            "full",
            "lexical-first",
            "lexical-banded",
            "explicit-routed",
            "late-output-fused",
        ),
        default="full",
    )
    parser.add_argument("--lexical-band-width", type=float)
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="write an exact/normalized query leakage receipt without scoring retrieval",
    )
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    benchmark, benchmark_hash = load_benchmark(args.benchmark)
    if args.audit_only:
        result = audit_benchmark_disjointness(
            args.database,
            benchmark,
            benchmark_sha256=benchmark_hash,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {key: result[key] for key in ("status", "query_count", "collision_count")},
                indent=2,
            )
        )
        return 0
    common = {
        "benchmark_sha256": benchmark_hash,
        "control_seeds": args.control_seed or (0, 1, 2),
        "limit": args.limit,
    }
    if args.candidate == "lexical-first":
        result = evaluate_lexical_first_catalog(args.database, benchmark, **common)
    elif args.candidate == "late-output-fused":
        if args.lexical_band_width is not None:
            parser.error("late-output-fused does not accept --lexical-band-width")
        result = evaluate_late_output_fused_catalog(
            args.database,
            benchmark,
            **common,
        )
    elif args.candidate == "explicit-routed":
        if args.lexical_band_width not in (None, 0.005):
            parser.error("explicit-routed freezes --lexical-band-width at 0.005")
        result = evaluate_explicit_routed_catalog(
            args.database,
            benchmark,
            lexical_band_width=0.005,
            **common,
        )
    elif args.candidate == "lexical-banded":
        if args.lexical_band_width is None:
            parser.error("--lexical-band-width is required for lexical-banded")
        result = evaluate_lexical_banded_catalog(
            args.database,
            benchmark,
            lexical_band_width=args.lexical_band_width,
            **common,
        )
    else:
        result = evaluate_catalog(args.database, benchmark, **common)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "query_count", "gates")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
