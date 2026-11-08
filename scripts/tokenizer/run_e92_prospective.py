#!/usr/bin/env python3
"""Run the sealed E92 prospective evaluation after strict independent review."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_prospective import (  # noqa: E402
    SOURCE_CHAIN_BUNDLE_FILES,
    build_e92_prospective_run,
    json_bytes,
)


def _write_exclusive(path: Path, payload: dict) -> None:
    with path.open("xb") as handle:
        handle.write(json_bytes(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--preparation-receipt", required=True)
    parser.add_argument("--source-inventory", required=True)
    parser.add_argument("--catalog-database", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--control-seed", type=int, action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output}")
    pending = output.with_name(output.name + ".pending")
    if pending.exists():
        raise FileExistsError(f"pending output requires audit before retry: {pending}")
    bundle = build_e92_prospective_run(
        queue_path=args.queue,
        labels_path=args.labels,
        preparation_receipt_path=args.preparation_receipt,
        source_inventory_path=args.source_inventory,
        catalog_database=args.catalog_database,
        control_seeds=args.control_seed or (11, 29, 47),
        limit=args.limit,
    )
    pending.parent.mkdir(parents=True, exist_ok=True)
    try:
        pending.mkdir()
        _write_exclusive(pending / "BENCHMARK.json", bundle["benchmark"])
        _write_exclusive(pending / "RESULT.json", bundle["result"])
        for role, filename in SOURCE_CHAIN_BUNDLE_FILES.items():
            _write_exclusive(pending / filename, bundle["source_chain"][role])
        _write_exclusive(pending / "RUN_RECEIPT.json", bundle["receipt"])
        os.replace(pending, output)
    except BaseException:
        if pending.exists() and not any(pending.iterdir()):
            shutil.rmtree(pending)
        raise
    print(
        json.dumps(
            {
                "status": bundle["receipt"]["status"],
                "result_status": bundle["result"]["status"],
                "query_count": bundle["result"]["query_count"],
                "promotion": bundle["receipt"]["promotion"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
