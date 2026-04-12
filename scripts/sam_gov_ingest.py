#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.darpa_prep.client import SamGovClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Search and normalize SAM.gov opportunities into SCBE DARPA-prep records")
    parser.add_argument("query", help="SAM.gov search query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    parser.add_argument("--active-only", action="store_true", default=False)
    args = parser.parse_args()

    client = SamGovClient()
    raw_results = client.search_opportunities(query=args.query, limit=args.limit, active_only=args.active_only)
    normalized = [client.normalize_opportunity(item).model_dump() for item in raw_results]

    payload = {
        "query": args.query,
        "count": len(normalized),
        "opportunities": normalized,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
