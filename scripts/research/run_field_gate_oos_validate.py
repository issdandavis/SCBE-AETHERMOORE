"""Out-of-sample validation for a frozen prime fog branch gate.

The gate is selected before this script runs. The script builds an old boundary
field and a larger test field, then scores only scan rows beyond the old
boundary. That is the closest local analogue of a blind search engine test:
rank new candidates, then verify future-anchor labels after ranking.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    build_rows,
    ensure_dynamic_profiles,
    score_profile,
    score_spec,
)


DEFAULT_OUT_DIR = Path("artifacts/prime_fog_gate_oos")
BASELINES = ("igct_c3_g6", "igct_c4_g5", "igct_c4_g6")


def spec_from_report(path: Path, selector: str) -> GateSpec:
    report = json.loads(path.read_text(encoding="utf-8"))
    key = {
        "holdout": "best_holdout_selected_branch",
        "train": "best_train_selected_branch",
        "full": "best_full_selected_branch",
    }[selector]
    payload = report[key]["spec"]
    return GateSpec(**payload)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Fog Frozen Gate OOS Validation",
        "",
        f"Train boundary limit: {report['config']['boundary_limit']:,}",
        f"Test limit: {report['config']['test_limit']:,}",
        f"Boundary max scan index: {report['summary']['boundary_max_scan_idx']:,}",
        f"Fresh rows: {report['summary']['fresh_row_count']:,}",
        "",
        "## Frozen Gate",
        "",
        f"Spec: `{report['frozen_gate']['spec']['spec_id']}`",
        f"Fresh top-{report['config']['top_n']}: {report['frozen_gate']['fresh']['top_hits']}/{report['frozen_gate']['fresh']['top_n']} ({report['frozen_gate']['fresh']['top_anchor_rate']:.1%})",
        f"Fresh AP: {report['frozen_gate']['fresh']['average_precision']:.6f}",
        "",
        "## Fresh-Range Baselines",
        "",
        "| Method | Hits | Rate | AP | Lift |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in report["baselines"]:
        fresh = item["fresh"]
        lines.append(
            "| {name} | {hits}/{top_n} | {rate:.1%} | {ap:.6f} | {lift:.2f}x |".format(
                name=item["name"],
                hits=fresh["top_hits"],
                top_n=fresh["top_n"],
                rate=fresh["top_anchor_rate"],
                ap=fresh["average_precision"],
                lift=fresh["lift"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    ensure_dynamic_profiles()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = spec_from_report(Path(args.report), args.selector)
    boundary_rows = build_rows(args.boundary_limit, args.window, args.history, args.anchor_threshold)
    boundary_max_scan_idx = max(row["scan_idx"] for row in boundary_rows)
    boundary_max_scan_prime = max(row["scan_prime"] for row in boundary_rows)

    test_rows = build_rows(args.test_limit, args.window, args.history, args.anchor_threshold)
    fresh_rows = [
        row
        for row in test_rows
        if row["scan_idx"] > boundary_max_scan_idx and row["scan_prime"] > boundary_max_scan_prime
    ]
    if not fresh_rows:
        raise RuntimeError("no fresh rows beyond boundary; increase --test-limit")

    frozen = score_spec(fresh_rows, spec, args.top_n)
    baselines = [{"name": profile, "fresh": score_profile(fresh_rows, profile, args.top_n)} for profile in BASELINES]
    report = {
        "schema_version": "prime_fog_gate_oos_validation_v1",
        "config": {
            "boundary_limit": args.boundary_limit,
            "test_limit": args.test_limit,
            "window": args.window,
            "history": args.history,
            "top_n": args.top_n,
            "anchor_threshold": args.anchor_threshold,
            "selector": args.selector,
            "source_report": str(Path(args.report)),
        },
        "summary": {
            "boundary_row_count": len(boundary_rows),
            "boundary_max_scan_idx": boundary_max_scan_idx,
            "boundary_max_scan_prime": boundary_max_scan_prime,
            "test_row_count": len(test_rows),
            "fresh_row_count": len(fresh_rows),
            "fresh_positive_count": sum(1 for row in fresh_rows if row["future_anchor"]),
            "fresh_base_rate": round(
                sum(1 for row in fresh_rows if row["future_anchor"]) / len(fresh_rows),
                6,
            ),
        },
        "frozen_gate": {
            "spec": asdict(spec),
            "fresh": frozen,
        },
        "baselines": baselines,
        "claim_boundary": "Frozen gate selected from 50M report, evaluated only on rows beyond the 50M scan boundary.",
    }
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="artifacts/prime_fog_branch_gate/latest_report.json")
    parser.add_argument("--selector", choices=["holdout", "train", "full"], default="holdout")
    parser.add_argument("--boundary-limit", type=int, default=50_000_000)
    parser.add_argument("--test-limit", type=int, default=100_000_000)
    parser.add_argument("--window", type=int, default=36)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--anchor-threshold", type=float, default=4.0)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_validation(args)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        fresh = report["frozen_gate"]["fresh"]
        print(
            "frozen_gate fresh={hits}/{top_n} rate={rate:.1%} ap={ap:.6f}".format(
                hits=fresh["top_hits"],
                top_n=fresh["top_n"],
                rate=fresh["top_anchor_rate"],
                ap=fresh["average_precision"],
            )
        )
        print(Path(args.out_dir) / "LATEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
