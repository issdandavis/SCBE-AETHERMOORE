#!/usr/bin/env python3
"""Generate arXiv submission manifest metadata."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate arXiv submission metadata manifest")
    parser.add_argument("--title", required=True)
    parser.add_argument("--authors", required=True, help="Comma-separated author list")
    parser.add_argument("--category", default="cs.CR")
    parser.add_argument("--abstract-file", default="")
    parser.add_argument("--output", default="artifacts/arxiv/manifest.json")
    args = parser.parse_args()

    abstract = ""
    if args.abstract_file:
        abstract = Path(args.abstract_file).read_text(encoding="utf-8").strip()

    manifest = {
        "schema_version": "1.0.0",
        "title": args.title,
        "authors": [x.strip() for x in args.authors.split(",") if x.strip()],
        "category": args.category,
        "abstract": abstract,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
