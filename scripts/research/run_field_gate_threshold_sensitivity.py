"""Threshold sensitivity for a frozen prime fog branch gate.

This separates two claims:

1. Frozen gate performance is blind evidence.
2. Thresholds retuned on a fresh range are only an adaptive ceiling unless
   validated on a later disjoint range.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from itertools import product
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
from scripts.research.run_field_gate_oos_validate import spec_from_report  # noqa: E402


DEFAULT_OUT_DIR = Path("artifacts/prime_fog_gate_threshold_sensitivity")
BASELINES = ("igct_c3_g6", "igct_c4_g5", "igct_c4_g6")


def fresh_rows(boundary_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_idx = max(row["scan_idx"] for row in boundary_rows)
    max_prime = max(row["scan_prime"] for row in boundary_rows)
    return [row for row in test_rows if row["scan_idx"] > max_idx and row["scan_prime"] > max_prime]


def candidate_specs(base_profile: str) -> list[GateSpec]:
    specs = []
    for cold_min in (0.55, 0.60, 0.65, 0.70, 0.75):
        for grad_min in (0.00, 0.05, 0.10, 0.15):
            for grad_max in (0.45, 0.50, 0.60, 0.70):
                if grad_min >= grad_max:
                    continue
                for geo_min in (0.00, 0.25, 0.50):
                    specs.append(
                        GateSpec(
                            spec_id=(
                                f"{base_profile}_c{cold_min:g}_g{grad_min:g}-{grad_max:g}"
                                f"_geo{geo_min:g}_cas0_ch0_fb0_bb0"
                            ),
                            base_profile=base_profile,
                            cold_min=cold_min,
                            grad_min=grad_min,
                            grad_max=grad_max,
                            geo_min=geo_min,
                            cassette_min=0.0,
                            charge_min=0.0,
                            fallback_scale=0.0,
                            branch_bonus=0.0,
                        )
                    )
    return specs


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Fog Gate Threshold Sensitivity",
        "",
        "Adaptive thresholds are diagnostic only. The validation row is the next disjoint range.",
        "",
        "## Summary",
        "",
        "| Selection | 50M-100M | 100M-150M |",
        "| --- | ---: | ---: |",
        "| Frozen gate | {a}/{an} ({ar:.1%}) | {b}/{bn} ({br:.1%}) |".format(
            a=report["frozen"]["range_a"]["top_hits"],
            an=report["frozen"]["range_a"]["top_n"],
            ar=report["frozen"]["range_a"]["top_anchor_rate"],
            b=report["frozen"]["range_b"]["top_hits"],
            bn=report["frozen"]["range_b"]["top_n"],
            br=report["frozen"]["range_b"]["top_anchor_rate"],
        ),
        "| Best tuned on 50M-100M | {a}/{an} ({ar:.1%}) | {b}/{bn} ({br:.1%}) |".format(
            a=report["best_on_range_a"]["range_a"]["top_hits"],
            an=report["best_on_range_a"]["range_a"]["top_n"],
            ar=report["best_on_range_a"]["range_a"]["top_anchor_rate"],
            b=report["best_on_range_a"]["range_b"]["top_hits"],
            bn=report["best_on_range_a"]["range_b"]["top_n"],
            br=report["best_on_range_a"]["range_b"]["top_anchor_rate"],
        ),
        "| Oracle best on 100M-150M | {a}/{an} ({ar:.1%}) | {b}/{bn} ({br:.1%}) |".format(
            a=report["best_on_range_b"]["range_a"]["top_hits"],
            an=report["best_on_range_b"]["range_a"]["top_n"],
            ar=report["best_on_range_b"]["range_a"]["top_anchor_rate"],
            b=report["best_on_range_b"]["range_b"]["top_hits"],
            bn=report["best_on_range_b"]["range_b"]["top_n"],
            br=report["best_on_range_b"]["range_b"]["top_anchor_rate"],
        ),
        "",
        "## Selected Specs",
        "",
        f"Frozen: `{report['frozen']['spec']['spec_id']}`",
        f"Best tuned on 50M-100M: `{report['best_on_range_a']['spec']['spec_id']}`",
        f"Oracle best on 100M-150M: `{report['best_on_range_b']['spec']['spec_id']}`",
        "",
        "## Additive Baselines",
        "",
        "| Method | 50M-100M | 100M-150M |",
        "| --- | ---: | ---: |",
    ]
    for item in report["baselines"]:
        lines.append(
            "| {name} | {a}/{an} ({ar:.1%}) | {b}/{bn} ({br:.1%}) |".format(
                name=item["name"],
                a=item["range_a"]["top_hits"],
                an=item["range_a"]["top_n"],
                ar=item["range_a"]["top_anchor_rate"],
                b=item["range_b"]["top_hits"],
                bn=item["range_b"]["top_n"],
                br=item["range_b"]["top_anchor_rate"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def score_both(spec: GateSpec, rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    return {
        "spec": asdict(spec),
        "range_a": score_spec(rows_a, spec, top_n),
        "range_b": score_spec(rows_b, spec, top_n),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ensure_dynamic_profiles()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frozen_spec = spec_from_report(Path(args.report), "holdout")
    rows_50 = build_rows(args.limit_a_boundary, args.window, args.history, args.anchor_threshold)
    rows_100 = build_rows(args.limit_a_test, args.window, args.history, args.anchor_threshold)
    rows_150 = build_rows(args.limit_b_test, args.window, args.history, args.anchor_threshold)
    range_a = fresh_rows(rows_50, rows_100)
    range_b = fresh_rows(rows_100, rows_150)

    specs = candidate_specs(frozen_spec.base_profile)
    scored = [score_both(spec, range_a, range_b, args.top_n) for spec in specs]
    by_a = sorted(
        scored,
        key=lambda item: (-item["range_a"]["top_hits"], -item["range_a"]["average_precision"], item["spec"]["spec_id"]),
    )
    by_b = sorted(
        scored,
        key=lambda item: (-item["range_b"]["top_hits"], -item["range_b"]["average_precision"], item["spec"]["spec_id"]),
    )

    report = {
        "schema_version": "prime_fog_gate_threshold_sensitivity_v1",
        "config": {
            "limit_a_boundary": args.limit_a_boundary,
            "limit_a_test": args.limit_a_test,
            "limit_b_test": args.limit_b_test,
            "window": args.window,
            "history": args.history,
            "top_n": args.top_n,
            "candidate_specs": len(specs),
        },
        "ranges": {
            "range_a": {
                "label": "50M-100M",
                "row_count": len(range_a),
                "base_rate": round(sum(1 for row in range_a if row["future_anchor"]) / len(range_a), 6),
            },
            "range_b": {
                "label": "100M-150M",
                "row_count": len(range_b),
                "base_rate": round(sum(1 for row in range_b if row["future_anchor"]) / len(range_b), 6),
            },
        },
        "frozen": score_both(frozen_spec, range_a, range_b, args.top_n),
        "best_on_range_a": by_a[0],
        "best_on_range_b": by_b[0],
        "top_range_a_specs": by_a[: args.keep_top],
        "top_range_b_specs": by_b[: args.keep_top],
        "baselines": [
            {
                "name": profile,
                "range_a": score_profile(range_a, profile, args.top_n),
                "range_b": score_profile(range_b, profile, args.top_n),
            }
            for profile in BASELINES
        ],
        "claim_boundary": "Threshold retuning on range_a is adaptive; only range_b validates whether the retuned gate generalizes.",
    }
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="artifacts/prime_fog_branch_gate/latest_report.json")
    parser.add_argument("--limit-a-boundary", type=int, default=50_000_000)
    parser.add_argument("--limit-a-test", type=int, default=100_000_000)
    parser.add_argument("--limit-b-test", type=int, default=150_000_000)
    parser.add_argument("--window", type=int, default=36)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--anchor-threshold", type=float, default=4.0)
    parser.add_argument("--keep-top", type=int, default=10)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    report = run(args)
    print(
        "frozen={fa}/{fan}->{fb}/{fbn} tuned_a={ta}/{tan}->{tb}/{tbn}".format(
            fa=report["frozen"]["range_a"]["top_hits"],
            fan=report["frozen"]["range_a"]["top_n"],
            fb=report["frozen"]["range_b"]["top_hits"],
            fbn=report["frozen"]["range_b"]["top_n"],
            ta=report["best_on_range_a"]["range_a"]["top_hits"],
            tan=report["best_on_range_a"]["range_a"]["top_n"],
            tb=report["best_on_range_a"]["range_b"]["top_hits"],
            tbn=report["best_on_range_a"]["range_b"]["top_n"],
        )
    )
    print(Path(args.out_dir) / "LATEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
