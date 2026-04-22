"""Recover a tongue-table run into a usable final adapter.

Typical uses:
  python scripts/train/recover_tongue_table_run.py --run artifacts/tongue-table-lora-v2-weighted-rerun
  python scripts/train/recover_tongue_table_run.py --run artifacts/tongue-table-lora-v2-weighted --alias artifacts/tongue-table-lora-v2-weighted-rerun
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.train.tongue_table_run_support import (
    materialize_final_adapter,
    resolve_best_available_adapter,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="Canonical run directory to populate or inspect.")
    parser.add_argument(
        "--alias",
        default="",
        help="Optional alternate run directory to resolve from when --run is missing or empty.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing lora_final directory.")
    args = parser.parse_args()

    run_dir = (REPO_ROOT / args.run).resolve() if not Path(args.run).is_absolute() else Path(args.run)
    alias_dir = None
    if args.alias.strip():
        alias_path = Path(args.alias)
        alias_dir = (REPO_ROOT / alias_path).resolve() if not alias_path.is_absolute() else alias_path

    resolution = resolve_best_available_adapter(run_dir)
    if resolution is None and alias_dir is not None:
        resolution = resolve_best_available_adapter(alias_dir)
    if resolution is None:
        raise SystemExit(f"No recoverable adapter found for run={run_dir} alias={alias_dir}")

    run_dir.mkdir(parents=True, exist_ok=True)
    final_dir = materialize_final_adapter(
        run_dir,
        source_dir=resolution.adapter_dir,
        overwrite=args.overwrite,
    )

    report = {
        "run_dir": str(run_dir),
        "resolved_run_dir": str(resolution.run_dir),
        "resolved_adapter_dir": str(resolution.adapter_dir),
        "resolved_source": resolution.source,
        "final_dir": str(final_dir),
    }
    report_path = run_dir / "recovery_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
