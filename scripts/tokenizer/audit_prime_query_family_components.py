"""Audit indivisible query-session/target-family components before scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_query_family_components import (  # noqa: E402
    STATUS_INVALID,
    STATUS_VERIFIED,
    audit_query_session_family_components,
    write_json_exclusive,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--review-labels", type=Path, required=True)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--source-family-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fold-name", action="append", default=[])
    parser.add_argument("--minimum-accepted-queries", type=int, default=30)
    parser.add_argument("--minimum-sessions", type=int, default=3)
    parser.add_argument("--minimum-families", type=int, default=2)
    parser.add_argument("--maximum-component-share", type=float, default=0.8)
    args = parser.parse_args()

    report = audit_query_session_family_components(
        review_queue=args.review_queue,
        review_labels=args.review_labels,
        source_inventory=args.source_inventory,
        source_family_audit=args.source_family_audit,
        fold_names=args.fold_name or ("fold-0", "fold-1", "fold-2"),
        minimum_accepted_queries=args.minimum_accepted_queries,
        minimum_sessions=args.minimum_sessions,
        minimum_families=args.minimum_families,
        maximum_component_share=args.maximum_component_share,
    )
    write_json_exclusive(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "error_count": report["error_count"],
                "accepted_query_count": report["observed"]["accepted_query_count"],
                "indivisible_component_count": report["observed"]["indivisible_component_count"],
                "component_split_sha256": report["component_split_sha256"],
            },
            sort_keys=True,
        )
    )
    if report["status"] == STATUS_VERIFIED:
        return 0
    return 1 if report["status"] == STATUS_INVALID else 2


if __name__ == "__main__":
    raise SystemExit(main())
