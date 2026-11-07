#!/usr/bin/env python3
"""Create or finalize a private independent-request retrieval benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_query_harvest import (  # noqa: E402
    build_explicit_route_review_scope,
    build_reviewed_benchmark,
    harvest_review_queue,
    load_labels,
    query_hashes_from_benchmark,
    write_json_exclusive,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset", help="scrubbed private session chunks JSONL")
    source.add_argument("--input-queue", help="existing hash-bound review queue or scope")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--labels",
        help="hash-bound reviewer labels; emits final benchmark when supplied",
    )
    parser.add_argument("--minimum-queries", type=int, default=30)
    parser.add_argument(
        "--authored-after-utc",
        help="prospective-only cutoff; every dataset row must include timezone-aware authored_at_utc",
    )
    parser.add_argument(
        "--explicit-route-scope",
        action="store_true",
        help="seal the preregistered balanced explicit-route review scope",
    )
    parser.add_argument(
        "--exclude-benchmark",
        action="append",
        default=[],
        help="benchmark whose exact query hashes must be excluded; repeatable",
    )
    args = parser.parse_args()

    if args.input_queue:
        if args.authored_after_utc:
            parser.error("--authored-after-utc requires --dataset")
        queue = json.loads(Path(args.input_queue).read_text(encoding="utf-8"))
    else:
        queue = harvest_review_queue(
            args.dataset,
            authored_after_utc=args.authored_after_utc,
        )
    if args.explicit_route_scope:
        if not args.input_queue:
            parser.error("--explicit-route-scope requires --input-queue")
        excluded = set()
        for benchmark_path in args.exclude_benchmark:
            benchmark = json.loads(Path(benchmark_path).read_text(encoding="utf-8"))
            excluded.update(query_hashes_from_benchmark(benchmark))
        queue = build_explicit_route_review_scope(
            queue,
            excluded_query_sha256=excluded,
        )
    payload = queue
    if args.labels:
        payload = build_reviewed_benchmark(
            queue,
            load_labels(args.labels),
            minimum_queries=args.minimum_queries,
        )
    write_json_exclusive(args.output, payload)
    print(f"wrote {args.output}: " f"{payload.get('candidate_count', len(payload.get('queries', [])))} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
