"""Build an anchor-level target-lock map for prime-fog controllers.

This script is intentionally diagnostic. It uses known anchors to answer:

    which controller gets closest to each known hidden number?

That is not a blind benchmark score. It is the calibration surface for building
the next frozen trajectory rule.
"""

from __future__ import annotations

import csv
import gc
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_field_branch_gate_search import GateSpec, ensure_dynamic_profiles  # noqa: E402
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    NEG_INF,
    apply_score_normalizer,
    build_or_load_rows,
    fit_centroid_ranker,
    fit_score_normalizer,
    labels,
    linear_scores,
    matrix,
    metrics_for_scores,
    safe_float,
    score_cmpssz,
    score_dict,
    score_frozen,
    score_graph_map,
    score_lambda_shadow,
    split_ordered_rows,
)
from scripts.research.run_field_gate_threshold_sensitivity import fresh_rows  # noqa: E402


WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20
NEAR_RANKS = (50, 100)
FIT_FRACTION = 0.60
CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "prime_target_lock"

RANGES = [
    ("A", 100_000_000, 150_000_000),
    ("B", 150_000_000, 200_000_000),
    ("C", 200_000_000, 250_000_000),
    ("D", 250_000_000, 300_000_000),
    ("E", 300_000_000, 350_000_000),
    ("F", 350_000_000, 400_000_000),
    ("G", 400_000_000, 450_000_000),
]


def load_frozen_spec() -> GateSpec:
    report_path = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return GateSpec(**data["frozen_spec"])


def dyn_blend(frz_z: list[float], cen_z: list[float], wf: float, wa: float, wc: float) -> list[float]:
    out: list[float] = []
    for frozen, centroid in zip(frz_z, cen_z):
        if frozen <= NEG_INF / 10 or centroid <= NEG_INF / 10:
            out.append(NEG_INF)
        else:
            out.append(wf * frozen + wa * abs(frozen) + wc * centroid)
    return out


def score_modified_log_bridge(rows: list[dict[str, Any]]) -> list[float]:
    """Scale-stable bridge lane using only visible past/current row fields.

    The exact future bridge `log(p_next / p)` is verifier-side information, so
    this diagnostic uses the observed previous->current scan-prime bridge and a
    log-compressed current ratio pressure:

        bridge = (log(p_i) - log(p_{i-1})) / log(p_{i-1})
        ratio  = log1p(abs(scan_ratio_i)) / log(p_i)

    This keeps huge prime values on a dimensionless scale without peeking at
    hidden anchors.
    """
    scores = [NEG_INF for _row in rows]
    previous_prime: float | None = None
    previous_ratio = 0.0

    ordered = sorted(enumerate(rows), key=lambda item: item[1].get("scan_idx", 0))
    for index, row in ordered:
        prime = max(2.0, safe_float(row.get("scan_prime"), 2.0))
        log_prime = math.log(prime)
        scan_ratio = safe_float(row.get("scan_ratio", 0.0))

        if previous_prime is None:
            bridge_pressure = 0.0
            jump_pressure = 0.0
        else:
            log_previous = math.log(max(2.0, previous_prime))
            bridge = max(0.0, (log_prime - log_previous) / max(log_previous, 1.0))
            bridge_pressure = math.log1p(bridge * 1_000_000.0)
            jump_pressure = math.log1p(abs(scan_ratio - previous_ratio)) / max(log_prime, 1.0)

        ratio_pressure = math.log1p(abs(scan_ratio)) / max(log_prime, 1.0)
        scores[index] = bridge_pressure + (0.75 * ratio_pressure) + (0.50 * jump_pressure)

        previous_prime = prime
        previous_ratio = scan_ratio

    return scores


def finite_ranked(rows: list[dict[str, Any]], scores: list[float]) -> list[tuple[int, dict[str, Any], float]]:
    ranked: list[tuple[int, dict[str, Any], float]] = []
    for row, score in zip(rows, scores):
        if score > NEG_INF / 10:
            ranked.append((0, row, float(score)))
    ranked.sort(key=lambda item: (-item[2], item[1]["scan_idx"]))
    return [(rank, row, score) for rank, (_zero, row, score) in enumerate(ranked, start=1)]


def anchor_catalog(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    catalog: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not row.get("future_anchor") or row.get("first_anchor_prime") is None:
            continue
        anchor_prime = int(row["first_anchor_prime"])
        item = catalog.setdefault(
            anchor_prime,
            {
                "anchor_prime": anchor_prime,
                "anchor_idx": row.get("first_anchor_idx"),
                "anchor_ratio": row.get("first_anchor_ratio"),
                "candidate_rows": 0,
                "min_lead_steps": None,
                "max_lead_steps": None,
            },
        )
        item["candidate_rows"] += 1
        lead = row.get("lead_steps")
        if lead is not None:
            item["min_lead_steps"] = lead if item["min_lead_steps"] is None else min(item["min_lead_steps"], lead)
            item["max_lead_steps"] = lead if item["max_lead_steps"] is None else max(item["max_lead_steps"], lead)
    return catalog


def controller_metrics(rows: list[dict[str, Any]], scores: list[float]) -> dict[str, Any]:
    return metrics_for_scores(rows, score_dict(rows, scores), TOP_N, unique_anchors_only=True)


def anchor_best_ranks(
    rows: list[dict[str, Any]],
    scores_by_controller: dict[str, list[float]],
) -> dict[int, dict[str, dict[str, Any]]]:
    out: dict[int, dict[str, dict[str, Any]]] = {}
    for controller, scores in scores_by_controller.items():
        for rank, row, score in finite_ranked(rows, scores):
            if not row.get("future_anchor") or row.get("first_anchor_prime") is None:
                continue
            anchor_prime = int(row["first_anchor_prime"])
            controller_map = out.setdefault(anchor_prime, {})
            if controller not in controller_map:
                controller_map[controller] = {
                    "rank": rank,
                    "scan_idx": row.get("scan_idx"),
                    "scan_prime": row.get("scan_prime"),
                    "lead_steps": row.get("lead_steps"),
                    "score": round(score, 8),
                }
    return out


def summarize_range(
    label: str,
    rows: list[dict[str, Any]],
    scores_by_controller: dict[str, list[float]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    catalog = anchor_catalog(rows)
    best_ranks = anchor_best_ranks(rows, scores_by_controller)
    metrics = {
        name: controller_metrics(rows, scores)
        for name, scores in scores_by_controller.items()
    }

    controller_summary: dict[str, Any] = {}
    for name, item in metrics.items():
        hit_set = {int(hit["anchor_prime"]) for hit in item["hidden_numbers"] if hit.get("anchor_prime") is not None}
        controller_summary[name] = {
            "unique_hits": item["unique_anchor_hits"],
            "unique_total": item["unique_anchors_total"],
            "hit_anchors": sorted(hit_set),
        }

    target_rows: list[dict[str, Any]] = []
    union_by_rank = {rank_cutoff: set() for rank_cutoff in (TOP_N, *NEAR_RANKS)}
    for anchor_prime, item in catalog.items():
        per_controller = best_ranks.get(anchor_prime, {})
        best_controller = None
        best_info = None
        for controller, info in per_controller.items():
            if best_info is None or info["rank"] < best_info["rank"]:
                best_controller = controller
                best_info = info
        hit_by = [
            controller
            for controller, info in per_controller.items()
            if info["rank"] <= TOP_N
        ]
        near_by = {
            str(rank_cutoff): [
                controller
                for controller, info in per_controller.items()
                if info["rank"] <= rank_cutoff
            ]
            for rank_cutoff in NEAR_RANKS
        }
        for rank_cutoff in union_by_rank:
            if any(info["rank"] <= rank_cutoff for info in per_controller.values()):
                union_by_rank[rank_cutoff].add(anchor_prime)

        target_rows.append(
            {
                **item,
                "range": label,
                "hit_by_top20": sorted(hit_by),
                "near_by": near_by,
                "best_controller": best_controller,
                "best_rank": best_info["rank"] if best_info else None,
                "best_scan_idx": best_info["scan_idx"] if best_info else None,
                "best_scan_prime": best_info["scan_prime"] if best_info else None,
                "best_lead_steps": best_info["lead_steps"] if best_info else None,
                "best_score": best_info["score"] if best_info else None,
                "controller_ranks": {
                    controller: info["rank"]
                    for controller, info in sorted(per_controller.items())
                },
            }
        )

    target_rows.sort(
        key=lambda row: (
            10**9 if row["best_rank"] is None else row["best_rank"],
            row["anchor_prime"],
        )
    )

    summary = {
        "range": label,
        "known_anchor_count": len(catalog),
        "controllers": controller_summary,
        "union_top20": len(union_by_rank[TOP_N]),
        "union_top50": len(union_by_rank[50]),
        "union_top100": len(union_by_rank[100]),
        "top20_union_anchors": sorted(union_by_rank[TOP_N]),
        "top50_union_anchors": sorted(union_by_rank[50]),
        "top100_union_anchors": sorted(union_by_rank[100]),
    }
    return summary, target_rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "range",
        "anchor_prime",
        "anchor_idx",
        "anchor_ratio",
        "candidate_rows",
        "min_lead_steps",
        "max_lead_steps",
        "best_controller",
        "best_rank",
        "best_scan_idx",
        "best_scan_prime",
        "best_lead_steps",
        "best_score",
        "hit_by_top20",
        "near_by",
        "controller_ranks",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "hit_by_top20": json.dumps(row["hit_by_top20"]),
                    "near_by": json.dumps(row["near_by"], sort_keys=True),
                    "controller_ranks": json.dumps(row["controller_ranks"], sort_keys=True),
                }
            )


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Target Lock Map",
        "",
        "Diagnostic use only: known anchors are used to measure which controller gets closest to each target.",
        "This is calibration for the trajectory controller, not a blind benchmark claim.",
        "",
        "## Controller Scores",
        "",
        "| Range | Known anchors | frozen | dominant | magnitude | frozen_coherent | centroid | lambda | graph | CMPSSZ | modified_log | Union top20 | Union top50 | Union top100 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    order = [
        "frozen",
        "dominant",
        "magnitude",
        "frozen_coherent",
        "centroid",
        "lambda",
        "graph",
        "cmpssz",
        "modified_log",
    ]
    for item in report["ranges"]:
        cells = []
        for controller in order:
            c = item["controllers"][controller]
            cells.append(f"{c['unique_hits']}/{c['unique_total']}")
        lines.append(
            "| {range} | {known_anchor_count} | {scores} | {union_top20} | {union_top50} | {union_top100} |".format(
                range=item["range"],
                known_anchor_count=item["known_anchor_count"],
                scores=" | ".join(cells),
                union_top20=item["union_top20"],
                union_top50=item["union_top50"],
                union_top100=item["union_top100"],
            )
        )

    lines.extend(
        [
            "",
            "## What This Means",
            "",
            "- `Union top20` is the number of known anchors hit if an oracle could choose the best controller per target.",
            "- `Union top50` and `Union top100` show near-lock capacity: targets the current projections can almost hit but do not yet place in the top 20.",
            "- The next controller should learn how to move near-lock targets into top-20 without displacing high-confidence frozen hits.",
            "",
            "## Best Controller By Target",
            "",
        ]
    )
    for label, rows in report["targets_by_range"].items():
        lines.extend(
            [
                f"### Range {label}",
                "",
                "| Anchor prime | Ratio | Best controller | Best rank | Lead | Hit by top20 |",
                "| ---: | ---: | --- | ---: | ---: | --- |",
            ]
        )
        for row in rows[:40]:
            lines.append(
                "| {anchor_prime} | {anchor_ratio} | {best_controller} | {best_rank} | {best_lead_steps} | `{hit_by_top20}` |".format(
                    **row
                )
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_spec = load_frozen_spec()

    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    range_a = fresh_rows(rows_100, rows_150)
    fit_a, _holdout_a = split_ordered_rows(range_a, FIT_FRACTION)

    frozen_fit = score_frozen(fit_a, frozen_spec)
    frozen_mean, frozen_scale = fit_score_normalizer(frozen_fit)
    centroid_model = fit_centroid_ranker(matrix(fit_a), labels(fit_a))
    centroid_fit = linear_scores(centroid_model, matrix(fit_a))
    centroid_mean, centroid_scale = fit_score_normalizer(centroid_fit)

    report: dict[str, Any] = {
        "schema": "prime_target_lock_map_v2_modified_log",
        "top_n": TOP_N,
        "near_ranks": list(NEAR_RANKS),
        "ranges": [],
        "targets_by_range": {},
    }
    all_target_rows: list[dict[str, Any]] = []

    lower_rows = rows_100
    upper_rows = rows_150
    for index, (label, lower_limit, upper_limit) in enumerate(RANGES):
        if index == 0:
            rows = range_a
        else:
            del lower_rows
            gc.collect()
            lower_rows = upper_rows
            upper_rows = build_or_load_rows(upper_limit, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
            rows = fresh_rows(lower_rows, upper_rows)

        frozen_raw = score_frozen(rows, frozen_spec)
        frozen_z = apply_score_normalizer(frozen_raw, frozen_mean, frozen_scale)
        x_rows = matrix(rows)
        centroid_z = apply_score_normalizer(linear_scores(centroid_model, x_rows), centroid_mean, centroid_scale)

        scores_by_controller = {
            "frozen": frozen_raw,
            "dominant": dyn_blend(frozen_z, centroid_z, -1.5, 0.0, 1.0),
            "magnitude": dyn_blend(frozen_z, centroid_z, 0.5, 2.0, 2.0),
            "frozen_coherent": dyn_blend(frozen_z, centroid_z, 1.0, 0.0, 1.5),
            "centroid": centroid_z,
            "lambda": score_lambda_shadow(rows),
            "graph": score_graph_map(rows),
            "cmpssz": score_cmpssz(rows),
            "modified_log": score_modified_log_bridge(rows),
        }
        summary, target_rows = summarize_range(label, rows, scores_by_controller)
        report["ranges"].append(summary)
        report["targets_by_range"][label] = target_rows
        all_target_rows.extend(target_rows)
        print(
            f"{label} {lower_limit//1_000_000}-{upper_limit//1_000_000}M: "
            f"union20={summary['union_top20']} union50={summary['union_top50']} union100={summary['union_top100']}",
            flush=True,
        )

        del rows, x_rows, frozen_raw, frozen_z, centroid_z, scores_by_controller
        gc.collect()

    (OUT_DIR / "target_lock_latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_csv(all_target_rows, OUT_DIR / "target_lock_latest.csv")
    write_markdown(report, OUT_DIR / "RESULTS.md")
    print(f"Wrote {OUT_DIR / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
