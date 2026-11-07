#!/usr/bin/env python3
"""Create or finalize a private independent-request retrieval benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_query_harvest import (  # noqa: E402
    build_reviewed_benchmark,
    harvest_review_queue,
    load_labels,
    write_json_exclusive,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="scrubbed private session chunks JSONL")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--labels",
        help="hash-bound reviewer labels; emits final benchmark when supplied",
    )
    parser.add_argument("--minimum-queries", type=int, default=30)
    args = parser.parse_args()

    queue = harvest_review_queue(args.dataset)
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
