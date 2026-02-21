#!/usr/bin/env python3
"""Export SCBE monthly billable usage from the metering store."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.metering import export_monthly_billable_usage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export monthly billable usage")
    parser.add_argument("--year", type=int, default=datetime.utcnow().year)
    parser.add_argument("--month", type=int, default=datetime.utcnow().month)
    parser.add_argument("--tenant-id", type=str, default=None)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = export_monthly_billable_usage(
        year=args.year,
        month=args.month,
        tenant_id=args.tenant_id,
    )
    if args.pretty:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
