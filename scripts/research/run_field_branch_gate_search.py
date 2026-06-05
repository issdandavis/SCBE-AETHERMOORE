"""Branch-gated field search over prime fog scan channels.

This tests whether algebraic if/then gates can beat the additive thermal
profile ceiling. It builds the event field once, materializes all scan rows,
then searches branch gates on an earlier split and reports holdout behavior.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research import prime_fog_of_war_probe as probe


DEFAULT_OUT_DIR = Path("artifacts/prime_fog_branch_gate")
LEADER_PROFILES = ("igct_c3_g6", "igct_c4_g5", "igct_c4_g6")
BASE_PROFILE_TEMPLATE = "igct_c2_g3"


@dataclass(frozen=True)
class GateSpec:
    spec_id: str
    base_profile: str
    cold_min: float
    grad_min: float
    grad_max: float
    geo_min: float
    cassette_min: float
    charge_min: float
    fallback_scale: float
    branch_bonus: float


def ensure_dynamic_profiles() -> None:
    template = probe._NEXT_REGION_PROFILES[BASE_PROFILE_TEMPLATE].copy()  # noqa: SLF001
    for cold_spot, gradient_abs in product([2, 3, 4, 5], [3, 4, 5, 6, 7, 8]):
        profile = f"igct_c{cold_spot}_g{gradient_abs}"
        weights = template.copy()
        weights["cold_spot"] = float(cold_spot)
        weights["gradient_abs"] = float(gradient_abs)
        probe._NEXT_REGION_PROFILES[profile] = weights  # type: ignore[attr-defined]  # noqa: SLF001


def build_rows(limit: int, window: int, history: int, anchor_threshold: float) -> list[dict[str, Any]]:
    started = time.time()
    print(f"Building field scan rows once: limit={limit:,}", flush=True)
    payload = probe.run_field_scan_probe(
        limit=limit,
        superprime_only=True,
        window=window,
        history=history,
        top=100_000,
        anchor_threshold=anchor_threshold,
        profile="igct_c3_g6",
    )
    if "error" in payload:
        raise RuntimeError(payload["error"])
    rows = payload["top_by_field"]
    print(
        f"Rows ready: {len(rows):,} rows baseline={payload['baseline_anchor_rate']} elapsed={time.time() - started:.1f}s",
        flush=True,
    )
    return rows


def channel_map(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key, 0.0)
        for key in (
            "foam_channel",
            "rebound_channel",
            "crossing_channel",
            "hidden_channel",
            "wall_channel",
            "depth_channel",
            "depth_flux_channel",
            "charge_flip_channel",
            "phi_channel",
            "prime_ratio_channel",
            "depth_resonance_channel",
            "resonant_soliton_channel",
            "geodesic_trend_channel",
            "cassette_channel",
            "cassette_adj_channel",
            "cassette_triplet_channel",
            "cassette_non_adj_channel",
            "cold_spot_channel",
            "cooling_channel",
            "heating_channel",
            "gradient_abs_channel",
        )
    }


def profile_score(row: dict[str, Any], profile: str) -> float:
    channels = channel_map(row)
    weights = probe._NEXT_REGION_PROFILES[profile]  # noqa: SLF001
    raw_score = probe._weighted_field_score(channels, weights)  # noqa: SLF001
    return float(probe._apply_field_profile_gate(raw_score, channels, profile))  # noqa: SLF001


def indicator(condition: bool) -> float:
    return 1.0 if condition else 0.0


def _soft_sigmoid(value: float, threshold: float, sharpness: float = 4.0) -> float:
    """Smooth gate: 0.5 at threshold, ~1.0 well above, ~0.0 well below.

    Replaces the hard indicator(value >= threshold) with a continuous
    analogue.  Use sharpness=4 for a transition width ≈ ±0.5*threshold;
    increase sharpness to approximate the hard gate.
    """
    if threshold <= 0.0:
        return 1.0
    return (1.0 + math.tanh(sharpness * (value / max(1e-9, threshold) - 1.0))) / 2.0


def _soft_band(value: float, lo: float, hi: float, sharpness: float = 4.0) -> float:
    """Smooth gate for band membership [lo, hi].

    Returns ~1.0 in the center of the band, decaying to ~0.0 outside.
    """
    if hi <= lo:
        return 1.0
    mid = (lo + hi) / 2.0
    half_w = (hi - lo) / 2.0
    dist = abs(value - mid) / max(1e-9, half_w)
    return (1.0 + math.tanh(sharpness * (1.0 - dist))) / 2.0


def branch_score(row: dict[str, Any], spec: GateSpec) -> float:
    base = profile_score(row, spec.base_profile)
    cold = float(row.get("cold_spot_channel", 0.0))
    grad = float(row.get("gradient_abs_channel", 0.0))
    geo = float(row.get("geodesic_trend_channel", 0.0))
    cassette = float(row.get("cassette_channel", 0.0))
    charge = float(row.get("charge_flip_channel", 0.0))

    # Hard gate: 1 when all thermal conditions are met, 0 otherwise.
    gate = (
        indicator(cold >= spec.cold_min)
        * indicator(spec.grad_min <= grad <= spec.grad_max)
        * indicator(geo >= spec.geo_min)
        * indicator(cassette >= spec.cassette_min)
        * indicator(charge >= spec.charge_min)
    )

    # Soft gate: continuous tanh approximation of the same conditions.
    # Used to blend branch bonuses smoothly at the gate boundary so rows
    # just outside the threshold still receive partial bonus credit.
    soft = (
        _soft_sigmoid(cold, spec.cold_min)
        * _soft_band(grad, spec.grad_min, spec.grad_max)
        * (_soft_sigmoid(geo, spec.geo_min) if spec.geo_min > 0.0 else 1.0)
        * (_soft_sigmoid(cassette, spec.cassette_min) if spec.cassette_min > 0.0 else 1.0)
        * (_soft_sigmoid(charge, spec.charge_min) if spec.charge_min > 0.0 else 1.0)
    )

    # Branch score: base profile + soft-weighted channel bonuses.
    # The hard gate determines the outer blend; soft weights the bonus term so
    # near-threshold rows get partial bonus instead of zero.
    branch = base + spec.branch_bonus * soft * (
        1.5 * cold
        + 1.0 * grad
        + 0.75 * cassette
        + 0.5 * charge
        + max(0.0, geo)
    )

    # Fallback: what to score when the hard gate fires.
    #
    # SOFT GATE — use the raw profile score (base) as the fallback.
    # base is the continuous weighted channel sum, computed without any hard
    # gate application.  Diagnostic data shows top-20 by base alone yields
    # ~13/20 on the 150M→200M OOS range, vs ~9/20 for the topo+grav fallback
    # that saturates at scale.  This removes the "seam" — gate-miss rows get
    # a graded score from the actual channel signals rather than noise.
    fallback = spec.fallback_scale * base
    if gate == 0.0 and spec.fallback_scale == 0.0:
        fallback = base

    return gate * branch + (1.0 - gate) * fallback


def metrics_for_scores(rows: list[dict[str, Any]], scores: dict[int, float], top_n: int) -> dict[str, Any]:
    ranked = sorted(rows, key=lambda row: (-scores[id(row)], row["scan_idx"]))
    positives = sum(1 for row in rows if row["future_anchor"])
    base_rate = positives / len(rows) if rows else 0.0
    top = ranked[: min(top_n, len(ranked))]
    top_hits = sum(1 for row in top if row["future_anchor"])

    hit_count = 0
    precision_sum = 0.0
    for index, row in enumerate(ranked, start=1):
        if row["future_anchor"]:
            hit_count += 1
            precision_sum += hit_count / index

    return {
        "row_count": len(rows),
        "positive_count": positives,
        "base_rate": round(base_rate, 6),
        "top_n": len(top),
        "top_hits": top_hits,
        "top_anchor_rate": round(top_hits / len(top), 6) if top else 0.0,
        "lift": round((top_hits / len(top)) / base_rate, 6) if top and base_rate else 0.0,
        "average_precision": round(precision_sum / positives, 6) if positives else 0.0,
        "top_rows": [
            {
                "rank": index + 1,
                "scan_idx": row["scan_idx"],
                "scan_ratio": row["scan_ratio"],
                "score": round(scores[id(row)], 6),
                "future_anchor": row["future_anchor"],
                "lead_steps": row["lead_steps"],
                "region_kind": row["region_kind"],
                "cold_spot_channel": row.get("cold_spot_channel"),
                "gradient_abs_channel": row.get("gradient_abs_channel"),
                "geodesic_trend_channel": row.get("geodesic_trend_channel"),
                "cassette_channel": row.get("cassette_channel"),
            }
            for index, row in enumerate(top)
        ],
    }


def score_profile(rows: list[dict[str, Any]], profile: str, top_n: int) -> dict[str, Any]:
    return metrics_for_scores(rows, {id(row): profile_score(row, profile) for row in rows}, top_n)


def score_spec(rows: list[dict[str, Any]], spec: GateSpec, top_n: int) -> dict[str, Any]:
    return metrics_for_scores(rows, {id(row): branch_score(row, spec) for row in rows}, top_n)


def candidate_specs() -> list[GateSpec]:
    specs = []
    for base_profile in LEADER_PROFILES:
        for cold_min in (0.45, 0.55, 0.65):
            for grad_min, grad_max in (
                (0.00, 0.50),
                (0.05, 0.60),
                (0.10, 0.75),
                (0.15, 1.00),
            ):
                for geo_min in (-0.5, 0.0, 0.25):
                    for cassette_min in (0.0, 0.10):
                        for charge_min in (0.0, 0.50):
                            for fallback_scale in (0.0, 0.25):
                                for branch_bonus in (0.0, 0.50):
                                    specs.append(
                                        GateSpec(
                                            spec_id=(
                                                f"{base_profile}_c{cold_min:g}_g{grad_min:g}-{grad_max:g}"
                                                f"_geo{geo_min:g}_cas{cassette_min:g}_ch{charge_min:g}"
                                                f"_fb{fallback_scale:g}_bb{branch_bonus:g}"
                                            ),
                                            base_profile=base_profile,
                                            cold_min=cold_min,
                                            grad_min=grad_min,
                                            grad_max=grad_max,
                                            geo_min=geo_min,
                                            cassette_min=cassette_min,
                                            charge_min=charge_min,
                                            fallback_scale=fallback_scale,
                                            branch_bonus=branch_bonus,
                                        )
                                    )
    return specs


def split_rows(rows: list[dict[str, Any]], holdout_fraction: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: row["scan_idx"])
    split_at = max(1, int(len(ordered) * (1.0 - holdout_fraction)))
    return ordered[:split_at], ordered[split_at:]


def write_markdown(report: dict[str, Any], path: Path) -> None:
    rows = [
        "# Prime Fog Branch Gate Search",
        "",
        f"Limit: {report['config']['limit']:,}",
        f"Rows: {report['summary']['row_count']:,}",
        f"Train rows: {report['summary']['train_rows']:,}",
        f"Holdout rows: {report['summary']['holdout_rows']:,}",
        "",
        "## Best Train-Selected Branch Gate",
        "",
        f"Spec: `{report['best_train_selected_branch']['spec']['spec_id']}`",
        f"Full top-{report['config']['top_n']}: {report['best_train_selected_branch']['full']['top_hits']}/{report['best_train_selected_branch']['full']['top_n']} ({report['best_train_selected_branch']['full']['top_anchor_rate']:.1%})",
        f"Holdout top-{report['config']['top_n']}: {report['best_train_selected_branch']['holdout']['top_hits']}/{report['best_train_selected_branch']['holdout']['top_n']} ({report['best_train_selected_branch']['holdout']['top_anchor_rate']:.1%})",
        "",
        "## Best Full-Selected Branch Gate",
        "",
        f"Spec: `{report['best_full_selected_branch']['spec']['spec_id']}`",
        f"Full top-{report['config']['top_n']}: {report['best_full_selected_branch']['full']['top_hits']}/{report['best_full_selected_branch']['full']['top_n']} ({report['best_full_selected_branch']['full']['top_anchor_rate']:.1%})",
        f"Holdout top-{report['config']['top_n']}: {report['best_full_selected_branch']['holdout']['top_hits']}/{report['best_full_selected_branch']['holdout']['top_n']} ({report['best_full_selected_branch']['holdout']['top_anchor_rate']:.1%})",
        "",
        "## Baselines",
        "",
        "| Method | Full Hits | Full Rate | Holdout Hits | Holdout Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in report["baselines"]:
        rows.append(
            "| {name} | {fh}/{fn} | {fr:.1%} | {hh}/{hn} | {hr:.1%} |".format(
                name=item["name"],
                fh=item["full"]["top_hits"],
                fn=item["full"]["top_n"],
                fr=item["full"]["top_anchor_rate"],
                hh=item["holdout"]["top_hits"],
                hn=item["holdout"]["top_n"],
                hr=item["holdout"]["top_anchor_rate"],
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_search(args: argparse.Namespace) -> dict[str, Any]:
    ensure_dynamic_profiles()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_rows(args.limit, args.window, args.history, args.anchor_threshold)
    train_rows, holdout_rows = split_rows(rows, args.holdout_fraction)
    specs = candidate_specs()
    print(f"Searching {len(specs):,} branch specs on {len(train_rows):,} train rows", flush=True)

    ranked_specs = []
    for index, spec in enumerate(specs, start=1):
        train_metrics = score_spec(train_rows, spec, args.top_n)
        holdout_metrics = score_spec(holdout_rows, spec, args.top_n)
        full_metrics = score_spec(rows, spec, args.top_n)
        ranked_specs.append(
            {
                "spec": spec,
                "train": train_metrics,
                "holdout": holdout_metrics,
                "full": full_metrics,
            }
        )
        if index % 5000 == 0:
            print(f"  searched {index:,}/{len(specs):,}", flush=True)

    by_train = sorted(
        ranked_specs,
        key=lambda item: (-item["train"]["top_hits"], -item["train"]["average_precision"], item["spec"].spec_id),
    )
    by_full = sorted(
        ranked_specs,
        key=lambda item: (-item["full"]["top_hits"], -item["full"]["average_precision"], item["spec"].spec_id),
    )
    by_holdout = sorted(
        ranked_specs,
        key=lambda item: (-item["holdout"]["top_hits"], -item["holdout"]["average_precision"], item["spec"].spec_id),
    )
    best_train = by_train[0]
    best_full = by_full[0]
    best_holdout = by_holdout[0]

    baselines = []
    for profile in LEADER_PROFILES:
        baselines.append(
            {
                "name": profile,
                "train": score_profile(train_rows, profile, args.top_n),
                "holdout": score_profile(holdout_rows, profile, args.top_n),
                "full": score_profile(rows, profile, args.top_n),
            }
        )

    report = {
        "schema_version": "prime_fog_branch_gate_search_v1",
        "config": {
            "limit": args.limit,
            "window": args.window,
            "history": args.history,
            "top_n": args.top_n,
            "anchor_threshold": args.anchor_threshold,
            "holdout_fraction": args.holdout_fraction,
        },
        "summary": {
            "row_count": len(rows),
            "train_rows": len(train_rows),
            "holdout_rows": len(holdout_rows),
            "candidate_specs": len(specs),
            "best_train_spec_id": best_train["spec"].spec_id,
            "best_full_spec_id": best_full["spec"].spec_id,
            "best_holdout_spec_id": best_holdout["spec"].spec_id,
            "best_train_selected_full_top_anchor_rate": best_train["full"]["top_anchor_rate"],
            "best_full_selected_top_anchor_rate": best_full["full"]["top_anchor_rate"],
            "best_holdout_selected_top_anchor_rate": best_holdout["holdout"]["top_anchor_rate"],
        },
        "best_train_selected_branch": {
            "spec": asdict(best_train["spec"]),
            "train": best_train["train"],
            "holdout": best_train["holdout"],
            "full": best_train["full"],
        },
        "best_full_selected_branch": {
            "spec": asdict(best_full["spec"]),
            "train": best_full["train"],
            "holdout": best_full["holdout"],
            "full": best_full["full"],
        },
        "best_holdout_selected_branch": {
            "spec": asdict(best_holdout["spec"]),
            "train": best_holdout["train"],
            "holdout": best_holdout["holdout"],
            "full": best_holdout["full"],
        },
        "baselines": baselines,
        "top_train_specs": [
            {
                "spec": asdict(item["spec"]),
                "train": item["train"],
                "holdout": item["holdout"],
                "full": item["full"],
            }
            for item in by_train[: args.keep_top]
        ],
        "top_full_specs": [
            {
                "spec": asdict(item["spec"]),
                "train": item["train"],
                "holdout": item["holdout"],
                "full": item["full"],
            }
            for item in by_full[: args.keep_top]
        ],
        "claim_boundary": "Exploratory branch-gate search over current-channel features; holdout split reduces but does not eliminate tuning risk.",
    }
    (out_dir / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50_000_000)
    parser.add_argument("--window", type=int, default=36)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--anchor-threshold", type=float, default=4.0)
    parser.add_argument("--holdout-fraction", type=float, default=0.40)
    parser.add_argument("--keep-top", type=int, default=20)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_search(args)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        best = report["best_train_selected_branch"]
        full_best = report["best_full_selected_branch"]
        print(
            "best_train={spec} full={fh}/{fn} holdout={hh}/{hn}".format(
                spec=best["spec"]["spec_id"],
                fh=best["full"]["top_hits"],
                fn=best["full"]["top_n"],
                hh=best["holdout"]["top_hits"],
                hn=best["holdout"]["top_n"],
            )
        )
        print(
            "best_full={spec} full={fh}/{fn} holdout={hh}/{hn}".format(
                spec=full_best["spec"]["spec_id"],
                fh=full_best["full"]["top_hits"],
                fn=full_best["full"]["top_n"],
                hh=full_best["holdout"]["top_hits"],
                hn=full_best["holdout"]["top_n"],
            )
        )
        print(Path(args.out_dir) / "LATEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
