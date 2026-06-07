"""Replacement audit for density clusters and RR residue clusters.

The count-proxy audit showed density lanes can match anchor volume while
misplacing about half the anchor identities. The RR sqrt(1) lane finds many
disjoint true anchors but has weaker standalone count stability.

This audit freezes the density cluster count as the volume budget, then tests
whether RR candidates can replace low-confidence density clusters without
letting count error drift.

This is an exploratory capacity audit, not a blind committed router.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.audit_prime_anchor_count_proxy import (  # noqa: E402
    RINGS,
    PeakConfig,
    ScoreContext,
    actual_anchor_ids,
    anchor_id,
    choose_best,
    evaluate_clusters,
    local_peak_indices,
    non_max_suppress_by_scan_gap,
    parse_csv_floats,
    parse_csv_ints,
    percentile_cutoff,
)
from scripts.research.run_prime_search_engine_bench import (
    DEFAULT_ROW_CACHE_DIR,
)  # noqa: E402

DENSITY_FAMILIES = ("frozen", "dominant", "magnitude", "frozen_coherent", "v6")
RR_FAMILIES = ("rr_sqrt1_exact", "rr_sqrt1_near", "rr_sqrt1")


@dataclass(frozen=True)
class ClusterSet:
    config: PeakConfig
    indices: tuple[int, ...]
    metrics: dict[str, Any]


def percentile_ranks(scores: list[float]) -> list[float]:
    clean = sorted(score for score in scores if math.isfinite(score))
    if not clean:
        return [0.0 for _ in scores]
    denom = max(1, len(clean) - 1)
    out = []
    for score in scores:
        if not math.isfinite(score):
            out.append(0.0)
        else:
            out.append(bisect.bisect_left(clean, score) / denom)
    return out


def cluster_indices(
    rows: list[dict[str, Any]], scores: list[float], config: PeakConfig
) -> tuple[int, ...]:
    cutoff = percentile_cutoff(scores, config.percentile)
    peaks = local_peak_indices(rows, scores, cutoff)
    selected = non_max_suppress_by_scan_gap(rows, scores, peaks, config.radius)
    return tuple(selected)


def selected_metrics(
    rows: list[dict[str, Any]], selected: list[int] | tuple[int, ...]
) -> dict[str, Any]:
    actual_ids = actual_anchor_ids(rows)
    false_clusters = 0
    duplicate_clusters = 0
    hit_ids: set[object] = set()
    seen: set[object] = set()
    cluster_rows = []
    for rank, index in enumerate(selected, start=1):
        row = rows[index]
        aid = anchor_id(row) if row.get("future_anchor") else None
        if aid is None:
            false_clusters += 1
        elif aid in seen:
            duplicate_clusters += 1
        else:
            hit_ids.add(aid)
            seen.add(aid)
        cluster_rows.append(
            {
                "rank": rank,
                "scan_idx": row.get("scan_idx"),
                "scan_prime": row.get("scan_prime"),
                "future_anchor": bool(row.get("future_anchor")),
                "anchor_idx": row.get("first_anchor_idx"),
                "anchor_prime": row.get("first_anchor_prime"),
                "lead_steps": row.get("lead_steps"),
            }
        )
    predicted = len(selected)
    actual = len(actual_ids)
    unique_hits = len(hit_ids)
    missed = actual - unique_hits
    return {
        "predicted_clusters": predicted,
        "actual_unique_anchors": actual,
        "count_error": predicted - actual,
        "abs_count_error": abs(predicted - actual),
        "unique_anchor_hits": unique_hits,
        "false_clusters": false_clusters,
        "missed_anchors": missed,
        "duplicate_clusters": duplicate_clusters,
        "precision": round(unique_hits / predicted, 6) if predicted else 0.0,
        "recall": round(unique_hits / actual, 6) if actual else 0.0,
        "hit_anchor_ids": sorted(hit_ids),
        "cluster_rows": cluster_rows[:50],
    }


def score_configs(
    rows: list[dict[str, Any]],
    score_map: dict[str, list[float]],
    configs: list[PeakConfig],
) -> list[ClusterSet]:
    out = []
    for config in configs:
        scores = score_map[config.score_family]
        metrics = evaluate_clusters(rows, scores, config)
        indices = cluster_indices(rows, scores, config)
        out.append(ClusterSet(config, indices, metrics))
    return out


def best_cluster_set(cluster_sets: list[ClusterSet]) -> ClusterSet:
    metrics = [item.metrics for item in cluster_sets]
    best = choose_best(metrics)
    return next(
        item for item in cluster_sets if item.metrics["config_id"] == best["config_id"]
    )


def respects_scan_gap(
    rows: list[dict[str, Any]], selected: list[int], candidate: int, radius: int
) -> bool:
    scan_idx = int(rows[candidate]["scan_idx"])
    return all(
        abs(scan_idx - int(rows[index]["scan_idx"])) >= radius for index in selected
    )


def refill_to_budget(
    rows: list[dict[str, Any]],
    selected: list[int],
    fallback: list[int],
    budget: int,
    radius: int,
) -> list[int]:
    selected_set = set(selected)
    for candidate in fallback:
        if len(selected) >= budget:
            break
        if candidate in selected_set:
            continue
        if not respects_scan_gap(rows, selected, candidate, radius):
            continue
        selected.append(candidate)
        selected_set.add(candidate)
    return selected


def fixed_swap(
    rows: list[dict[str, Any]],
    density: ClusterSet,
    rr: ClusterSet,
    density_scores: list[float],
    rr_scores: list[float],
    swap_fraction: float,
) -> dict[str, Any]:
    budget = len(density.indices)
    swap_count = min(budget, max(0, round(budget * swap_fraction)))
    density_pct = percentile_ranks(density_scores)
    rr_pct = percentile_ranks(rr_scores)
    radius = max(density.config.radius, rr.config.radius)

    density_ranked_low_conf = sorted(
        density.indices,
        key=lambda index: (
            0.70 * density_pct[index] + 0.30 * rr_pct[index],
            density_pct[index],
            rr_pct[index],
            rows[index]["scan_idx"],
        ),
    )
    evicted = set(density_ranked_low_conf[:swap_count])
    kept = [index for index in density.indices if index not in evicted]
    density_set = set(density.indices)

    rr_ranked = sorted(
        rr.indices,
        key=lambda index: (
            -rr_pct[index],
            density_pct[index],
            -rr_scores[index],
            rows[index]["scan_idx"],
        ),
    )
    inserted: list[int] = []
    selected = list(kept)
    selected_set = set(selected)
    for candidate in rr_ranked:
        if len(selected) >= budget:
            break
        if candidate in density_set or candidate in selected_set:
            continue
        if not respects_scan_gap(rows, selected, candidate, radius):
            continue
        selected.append(candidate)
        selected_set.add(candidate)
        inserted.append(candidate)

    fallback = sorted(
        (index for index in density.indices if index not in selected_set),
        key=lambda index: (
            -density_pct[index],
            -rr_pct[index],
            rows[index]["scan_idx"],
        ),
    )
    selected = refill_to_budget(rows, selected, fallback, budget, radius)
    selected = sorted(selected, key=lambda index: int(rows[index]["scan_idx"]))
    metrics = selected_metrics(rows, selected)
    metrics.update(
        {
            "strategy": "fixed_swap",
            "swap_fraction": swap_fraction,
            "evicted_count": len(evicted),
            "inserted_count": len(inserted),
            "density_config": density.config.config_id,
            "rr_config": rr.config.config_id,
            "radius": radius,
        }
    )
    return metrics


def joint_score_select(
    rows: list[dict[str, Any]],
    density: ClusterSet,
    rr: ClusterSet,
    density_scores: list[float],
    rr_scores: list[float],
    alpha: float,
) -> dict[str, Any]:
    budget = len(density.indices)
    radius = max(density.config.radius, rr.config.radius)
    density_pct = percentile_ranks(density_scores)
    rr_pct = percentile_ranks(rr_scores)
    candidates = sorted(set(density.indices) | set(rr.indices))
    ranked = sorted(
        candidates,
        key=lambda index: (
            -(density_pct[index] + alpha * rr_pct[index]),
            -rr_pct[index],
            -density_pct[index],
            rows[index]["scan_idx"],
        ),
    )

    selected: list[int] = []
    for candidate in ranked:
        if len(selected) >= budget:
            break
        if not respects_scan_gap(rows, selected, candidate, radius):
            continue
        selected.append(candidate)
    selected = sorted(selected, key=lambda index: int(rows[index]["scan_idx"]))
    metrics = selected_metrics(rows, selected)
    metrics.update(
        {
            "strategy": "joint_score",
            "alpha": alpha,
            "density_config": density.config.config_id,
            "rr_config": rr.config.config_id,
            "radius": radius,
        }
    )
    return metrics


def oracle_swap_capacity(
    rows: list[dict[str, Any]],
    density: ClusterSet,
    rr: ClusterSet,
) -> dict[str, Any]:
    """Truth-guided upper bound for the same density/RR candidate pools.

    This intentionally uses anchor labels. It answers: if the router knew which
    density clusters were ghosts and which RR clusters were new true anchors,
    could the replacement pool break the ceiling while preserving count?
    """
    budget = len(density.indices)
    radius = max(density.config.radius, rr.config.radius)

    selected = list(density.indices)
    seen: set[object] = set()
    evictable: list[int] = []
    density_hit_ids: set[object] = set()
    for index in selected:
        row = rows[index]
        aid = anchor_id(row) if row.get("future_anchor") else None
        if aid is None or aid in seen:
            evictable.append(index)
        else:
            seen.add(aid)
            density_hit_ids.add(aid)

    rr_true_new = []
    rr_seen: set[object] = set()
    for index in rr.indices:
        row = rows[index]
        aid = anchor_id(row) if row.get("future_anchor") else None
        if aid is None or aid in density_hit_ids or aid in rr_seen:
            continue
        rr_true_new.append(index)
        rr_seen.add(aid)

    selected_set = set(selected)
    inserted: list[int] = []
    evicted: list[int] = []
    for candidate in rr_true_new:
        if not evictable:
            break
        evict = evictable.pop(0)
        trial = [index for index in selected if index != evict]
        if not respects_scan_gap(rows, trial, candidate, radius):
            continue
        selected = trial + [candidate]
        selected_set.discard(evict)
        selected_set.add(candidate)
        evicted.append(evict)
        inserted.append(candidate)
        if len(selected) >= budget:
            selected = selected[:budget]

    selected = sorted(selected, key=lambda index: int(rows[index]["scan_idx"]))
    metrics = selected_metrics(rows, selected)
    metrics.update(
        {
            "strategy": "oracle_swap_capacity",
            "evicted_count": len(evicted),
            "inserted_count": len(inserted),
            "density_config": density.config.config_id,
            "rr_config": rr.config.config_id,
            "radius": radius,
        }
    )
    return metrics


def choose_best_replacement(
    results: list[dict[str, Any]], max_count_error: int
) -> dict[str, Any]:
    feasible = [item for item in results if item["abs_count_error"] <= max_count_error]
    pool = feasible or results
    return max(
        pool,
        key=lambda item: (
            item["precision"],
            item["recall"],
            -item["abs_count_error"],
            -item["false_clusters"],
            -item["duplicate_clusters"],
        ),
    )


def build_configs(
    families: tuple[str, ...], percentiles: list[float], radii: list[int]
) -> list[PeakConfig]:
    return [
        PeakConfig(score_family=family, percentile=percentile, radius=radius)
        for family in families
        for percentile in percentiles
        for radius in radii
    ]


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Anchor Replacement Audit",
        "",
        "Density cluster count is held as the volume budget. RR clusters are tested as replacements.",
        "This is an exploratory capacity audit, not a blind committed router.",
        "",
        "## Best Replacement",
        "",
        (
            "| Ring | Strategy | Precision | Recall | Count error | Hits | Clusters | "
            "False | Missed | Duplicates | Details |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for ring, item in report["best_replacement"].items():
        details = (
            f"swap={item.get('swap_fraction')}"
            if item["strategy"] == "fixed_swap"
            else f"alpha={item.get('alpha')}"
        )
        lines.append(
            "| {ring} | {strategy} | {precision:.1%} | {recall:.1%} | {count_error:+d} | "
            "{unique_anchor_hits} | {predicted_clusters} | {false_clusters} | {missed_anchors} | "
            "{duplicate_clusters} | {details} |".format(
                ring=ring, details=details, **item
            )
        )

    lines.extend(
        [
            "",
            "## Oracle Swap Capacity",
            "",
            "| Ring | Precision | Recall | Count error | Hits | Clusters | Inserted |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for ring, item in report["oracle_capacity"].items():
        lines.append(
            "| {ring} | {precision:.1%} | {recall:.1%} | {count_error:+d} | "
            "{unique_anchor_hits} | {predicted_clusters} | {inserted_count} |".format(
                ring=ring, **item
            )
        )
    lines.extend(
        [
            "",
            "## Baselines",
            "",
            "| Ring | Density precision | RR precision | Density hits | RR hits | RR new | Union hits |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for ring, item in report["baselines"].items():
        lines.append(
            "| {ring} | {density_precision:.1%} | {rr_precision:.1%} | {density_hits} | {rr_hits} | "
            "{rr_new_hits} | {union_hits} |".format(ring=ring, **item)
        )
    lines.extend(
        [
            "",
            "## Caveat",
            "",
            (
                "Any ring-specific selected strategy is an oracle-style capacity result. "
                "Freeze a rule before the next ring before claiming generalization."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rings", default="K,L,M,N")
    parser.add_argument(
        "--percentiles", default="0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90"
    )
    parser.add_argument("--radii", default="6,12,18,24,36")
    parser.add_argument(
        "--swap-fractions", default="0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.50"
    )
    parser.add_argument("--alphas", default="0.0,0.25,0.5,0.75,1.0,1.5,2.0,3.0,4.0")
    parser.add_argument("--max-count-error", type=int, default=2)
    parser.add_argument("--out-dir", default="artifacts/prime_anchor_replacement")
    parser.add_argument("--cache-dir", default=str(DEFAULT_ROW_CACHE_DIR))
    args = parser.parse_args()

    rings = [ring.strip().upper() for ring in args.rings.split(",") if ring.strip()]
    unknown = sorted(set(rings) - set(RINGS))
    if unknown:
        raise SystemExit(f"unknown rings: {unknown}")

    percentiles = parse_csv_floats(args.percentiles)
    radii = parse_csv_ints(args.radii)
    swap_fractions = parse_csv_floats(args.swap_fractions)
    alphas = parse_csv_floats(args.alphas)

    density_configs = build_configs(DENSITY_FAMILIES, percentiles, radii)
    rr_configs = build_configs(RR_FAMILIES, percentiles, radii)
    ctx = ScoreContext(Path(args.cache_dir))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    baselines: dict[str, dict[str, Any]] = {}
    all_results: dict[str, list[dict[str, Any]]] = {}
    best_replacement: dict[str, dict[str, Any]] = {}
    oracle_capacity: dict[str, dict[str, Any]] = {}

    for ring in rings:
        rows = ctx.load_ring(ring)
        score_map = ctx.scores_for(rows)
        density_sets = score_configs(rows, score_map, density_configs)
        rr_sets = score_configs(rows, score_map, rr_configs)
        density = best_cluster_set(density_sets)
        rr = best_cluster_set(rr_sets)
        density_scores = score_map[density.config.score_family]
        rr_scores = score_map[rr.config.score_family]

        density_hits = set(density.metrics["hit_anchor_ids"])
        rr_hits = set(rr.metrics["hit_anchor_ids"])
        baselines[ring] = {
            "density_config": density.config.config_id,
            "rr_config": rr.config.config_id,
            "density_precision": density.metrics["precision"],
            "rr_precision": rr.metrics["precision"],
            "density_hits": len(density_hits),
            "rr_hits": len(rr_hits),
            "rr_new_hits": len(rr_hits - density_hits),
            "density_lost_hits": len(density_hits - rr_hits),
            "union_hits": len(density_hits | rr_hits),
        }

        ring_results: list[dict[str, Any]] = []
        for swap_fraction in swap_fractions:
            ring_results.append(
                fixed_swap(rows, density, rr, density_scores, rr_scores, swap_fraction)
            )
        for alpha in alphas:
            ring_results.append(
                joint_score_select(rows, density, rr, density_scores, rr_scores, alpha)
            )
        all_results[ring] = ring_results
        best_replacement[ring] = choose_best_replacement(
            ring_results, args.max_count_error
        )
        oracle_capacity[ring] = oracle_swap_capacity(rows, density, rr)

    report = {
        "schema": "prime_anchor_replacement_audit_v1",
        "rings": rings,
        "max_count_error": args.max_count_error,
        "baselines": baselines,
        "best_replacement": best_replacement,
        "oracle_capacity": oracle_capacity,
        "all_results": all_results,
    }
    (out_dir / "latest_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(report, out_dir / "RESULTS.md")

    print("Prime anchor replacement audit")
    print(f"  rings: {', '.join(rings)}")
    print(f"  wrote: {out_dir / 'RESULTS.md'}")
    for ring, item in best_replacement.items():
        detail = (
            f"swap={item.get('swap_fraction')}"
            if item["strategy"] == "fixed_swap"
            else f"alpha={item.get('alpha')}"
        )
        print(
            f"  {ring}: {item['strategy']} {detail} precision={item['precision']:.1%} "
            f"recall={item['recall']:.1%} count_error={item['count_error']:+d} "
            f"hits={item['unique_anchor_hits']}/{item['actual_unique_anchors']}"
        )


if __name__ == "__main__":
    main()
