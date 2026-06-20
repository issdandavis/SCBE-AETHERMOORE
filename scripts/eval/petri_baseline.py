"""Petri baseline — load every real Petri seed and characterise the corpus.

Run after populating ``external/benchmarks/petri-seeds/`` per
``docs/external/PETRI_SEEDS.md``. Reports:

  - total count + per-tag distribution
  - body-length stats (min/median/p95/max chars)
  - training-blocked ratio (must be 100% for the canary contract to hold)
  - any per-file load refusals

Usage:
    python scripts/eval/petri_baseline.py
    python scripts/eval/petri_baseline.py --seeds-dir <path> --json-out <path>
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

from src.cli.petri_seed_loader import (
    PetriLoadError,
    load_seed_directory,
    split_by_training_safety,
)

DEFAULT_SEEDS_DIR = Path("external/benchmarks/petri-seeds")


def run_baseline(seeds_dir: Path) -> Dict[str, object]:
    seeds = load_seed_directory(seeds_dir)
    blocked, safe = split_by_training_safety(seeds)

    tag_counter: Counter[str] = Counter()
    untagged = 0
    for s in seeds:
        tags = s.metadata.get("tags") or []
        if not tags:
            untagged += 1
        for t in tags:
            tag_counter[t] += 1

    body_lens = [len(s.input) for s in seeds]
    body_lens_sorted = sorted(body_lens)

    def _percentile(p: float) -> int:
        if not body_lens_sorted:
            return 0
        idx = max(0, min(len(body_lens_sorted) - 1, int(round((p / 100) * (len(body_lens_sorted) - 1)))))
        return body_lens_sorted[idx]

    return {
        "total_seeds": len(seeds),
        "training_blocked": len(blocked),
        "training_safe": len(safe),
        "training_blocked_ratio": (len(blocked) / len(seeds)) if seeds else 0.0,
        "tag_distribution": dict(tag_counter.most_common()),
        "untagged_seeds": untagged,
        "body_length_chars": {
            "min": min(body_lens) if body_lens else 0,
            "median": int(statistics.median(body_lens)) if body_lens else 0,
            "p95": _percentile(95),
            "max": max(body_lens) if body_lens else 0,
            "mean": int(statistics.mean(body_lens)) if body_lens else 0,
        },
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--seeds-dir",
        type=Path,
        default=DEFAULT_SEEDS_DIR,
        help=f"directory of .md seed files (default: {DEFAULT_SEEDS_DIR})",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="optional path to write the report JSON",
    )
    args = parser.parse_args(argv)

    try:
        report = run_baseline(args.seeds_dir)
    except PetriLoadError as exc:
        print(f"baseline aborted: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # Hard contract: real Petri seeds must all be canary-marked. If any
    # land in the safe partition, either upstream removed the canary or
    # our detector regressed — either way, halt loudly.
    if report["training_safe"] != 0:
        print(
            f"FAIL: {report['training_safe']} seeds slipped past the canary "
            "detector — training-safety contract broken",
            file=sys.stderr,
        )
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
