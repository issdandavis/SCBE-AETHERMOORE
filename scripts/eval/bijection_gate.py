"""CLI wrapper for the strict SCBE governance bijection gate.

Usage:
    python scripts/eval/bijection_gate.py --truth truth.json --candidate candidate.json

Truth must be a JSON object of string source ids to string target ids.
Candidate must be a JSON object of string source ids to string target ids, or
null for an explicit miss. Exit code is 0 only when the map is usable as a
router.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.bijection_gate import evaluate_bijection


def _read_truth_map(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")

    out: dict[str, str] = {}
    for source_id, target_id in payload.items():
        if not isinstance(source_id, str) or not isinstance(target_id, str):
            raise ValueError(f"{path} must map string source ids to string target ids")
        out[source_id] = target_id
    return out


def _read_candidate_map(path: Path) -> dict[str, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")

    out: dict[str, str | None] = {}
    for source_id, target_id in payload.items():
        if not isinstance(source_id, str) or not (
            isinstance(target_id, str) or target_id is None
        ):
            raise ValueError(
                f"{path} must map string source ids to string target ids or null"
            )
        out[source_id] = target_id
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a candidate map against a known truth map"
    )
    parser.add_argument(
        "--truth",
        required=True,
        type=Path,
        help="JSON object: source id -> true target id",
    )
    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="JSON object: source id -> predicted target id or null",
    )
    args = parser.parse_args(argv)

    try:
        truth = _read_truth_map(args.truth)
        candidate = _read_candidate_map(args.candidate)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    audit = evaluate_bijection(truth, candidate)
    print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    return 0 if audit.usable_as_router else 1


if __name__ == "__main__":
    raise SystemExit(main())
