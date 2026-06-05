"""Answer-backprop distiller for prime hidden-anchor search.

Training-time idea:
  1. Use known anchors on the fit split.
  2. For each anchor, ask which sensor lane ranks any row leading to it best.
  3. Distill those winning lanes into thresholds/reliability weights.
  4. Calibrate a frozen quota selector on the holdout split.
  5. Carry the selector blind to B/C/D.

Runtime/eval never reads verifier fields for scoring. Verifier fields are only
used by metrics_for_scores after ranking and by the fit/holdout calibration.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_field_branch_gate_search import ensure_dynamic_profiles  # noqa: E402
from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    NEG_INF,
    build_or_load_rows,
    evaluate_candidate,
    fresh_rows,
    metrics_for_scores,
    score_cmpssz,
    score_frozen,
    score_graph_map,
    score_lambda_shadow,
    spec_from_report,
    split_ordered_rows,
)

OUT_DIR = REPO_ROOT / "artifacts" / "answer_backprop_distiller"
CACHE_DIR = DEFAULT_ROW_CACHE_DIR
REPORT_PATH = REPO_ROOT / "artifacts" / "prime_fog_branch_gate" / "latest_report.json"

WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20
FIT_FRACTION = 0.60
LANES = ("frozen", "lambda", "graph", "cmpssz")


def z_norm(scores: list[float]) -> list[float]:
    clean = [score for score in scores if score > NEG_INF / 10]
    if not clean:
        return [NEG_INF for _ in scores]
    mean = sum(clean) / len(clean)
    variance = sum((score - mean) ** 2 for score in clean) / len(clean)
    scale = math.sqrt(variance) or 1.0
    return [((score - mean) / scale) if score > NEG_INF / 10 else NEG_INF for score in scores]


def rank_pct(scores: list[float]) -> list[float]:
    valid = [index for index, score in enumerate(scores) if score > NEG_INF / 10]
    pct = [0.0 for _ in scores]
    if not valid:
        return pct
    ordered = sorted(valid, key=lambda index: scores[index])
    denom = max(1, len(ordered) - 1)
    for rank, index in enumerate(ordered):
        pct[index] = rank / denom
    return pct


def lane_scores(rows: list[dict[str, Any]], spec: Any) -> dict[str, list[float]]:
    return {
        "frozen": score_frozen(rows, spec),
        "lambda": score_lambda_shadow(rows),
        "graph": score_graph_map(rows),
        "cmpssz": score_cmpssz(rows),
    }


def lane_pcts(rows: list[dict[str, Any]], spec: Any) -> dict[str, list[float]]:
    return {lane: rank_pct(z_norm(scores)) for lane, scores in lane_scores(rows, spec).items()}


def anchor_set_from_scores(rows: list[dict[str, Any]], scores: list[float]) -> set[int]:
    metrics = metrics_for_scores(
        rows,
        {id(row): score for row, score in zip(rows, scores)},
        TOP_N,
        unique_anchors_only=True,
    )
    return {int(item["anchor_prime"]) for item in metrics["hidden_numbers"] if item.get("anchor_prime") is not None}


def frozen_metrics(rows: list[dict[str, Any]], spec: Any) -> dict[str, Any]:
    scores = score_frozen(rows, spec)
    metrics = metrics_for_scores(
        rows,
        {id(row): score for row, score in zip(rows, scores)},
        TOP_N,
        unique_anchors_only=True,
    )
    metrics["anchor_set"] = {
        int(item["anchor_prime"]) for item in metrics["hidden_numbers"] if item.get("anchor_prime") is not None
    }
    return metrics


def backprop_explanations(rows: list[dict[str, Any]], pcts: dict[str, list[float]]) -> dict[str, Any]:
    by_anchor: dict[int, list[int]] = {}
    for index, row in enumerate(rows):
        if not row.get("future_anchor"):
            continue
        anchor = row.get("first_anchor_prime")
        if anchor is None:
            continue
        by_anchor.setdefault(int(anchor), []).append(index)

    explanations: list[dict[str, Any]] = []
    winner_counts = {lane: 0 for lane in LANES}
    winner_strengths: dict[str, list[float]] = {lane: [] for lane in LANES}
    for anchor, indexes in by_anchor.items():
        lane_best: dict[str, float] = {}
        lane_best_index: dict[str, int] = {}
        for lane in LANES:
            best_index = max(indexes, key=lambda idx: pcts[lane][idx])
            lane_best[lane] = pcts[lane][best_index]
            lane_best_index[lane] = best_index
        winner = max(LANES, key=lambda lane: (lane_best[lane], -LANES.index(lane)))
        winner_counts[winner] += 1
        winner_strengths[winner].append(lane_best[winner])
        explanations.append(
            {
                "anchor_prime": anchor,
                "winner": winner,
                "winner_pct": round(lane_best[winner], 6),
                "lane_best": {lane: round(lane_best[lane], 6) for lane in LANES},
                "best_scan_idx": rows[lane_best_index[winner]].get("scan_idx"),
            }
        )

    total = max(1, len(explanations))
    reliability = {
        lane: (winner_counts[lane] / total) * (sum(winner_strengths[lane]) / len(winner_strengths[lane]))
        if winner_strengths[lane]
        else 0.0
        for lane in LANES
    }
    threshold = {}
    for lane in LANES:
        vals = sorted(winner_strengths[lane])
        threshold[lane] = vals[max(0, int(len(vals) * 0.20) - 1)] if vals else 1.1

    return {
        "anchor_count": len(explanations),
        "winner_counts": winner_counts,
        "reliability": {lane: round(value, 6) for lane, value in reliability.items()},
        "threshold": {lane: round(value, 6) for lane, value in threshold.items()},
        "examples": sorted(explanations, key=lambda item: (-item["winner_pct"], item["anchor_prime"]))[:25],
    }


def pick_unique(
    rows: list[dict[str, Any]],
    candidate_indexes: list[int],
    score_values: list[float],
    count: int,
    covered: set[int],
) -> tuple[list[int], set[int]]:
    selected: list[int] = []
    updated = set(covered)
    for index in sorted(candidate_indexes, key=lambda idx: (-score_values[idx], rows[idx]["scan_idx"])):
        if len(selected) >= count:
            break
        row = rows[index]
        anchor = row.get("first_anchor_prime") if row.get("future_anchor") else None
        if anchor is not None and int(anchor) in updated:
            continue
        selected.append(index)
        if anchor is not None:
            updated.add(int(anchor))
    return selected, updated


def select_distilled(
    rows: list[dict[str, Any]],
    pcts: dict[str, list[float]],
    thresholds: dict[str, float],
    quotas: dict[str, int],
    lane_order: tuple[str, ...],
) -> dict[str, Any]:
    selected: list[int] = []
    covered: set[int] = set()
    selected_set: set[int] = set()
    lane_counts: dict[str, int] = {}
    lane_scores_for_sort = {
        lane: [
            (pcts[lane][index] if pcts[lane][index] >= thresholds.get(lane, 0.0) else NEG_INF)
            for index in range(len(rows))
        ]
        for lane in LANES
    }

    for lane in lane_order:
        quota = quotas.get(lane, 0)
        if quota <= 0:
            lane_counts[lane] = 0
            continue
        candidates = [idx for idx in range(len(rows)) if idx not in selected_set and lane_scores_for_sort[lane][idx] > NEG_INF / 10]
        picked, covered = pick_unique(rows, candidates, lane_scores_for_sort[lane], quota, covered)
        selected.extend(picked)
        selected_set.update(picked)
        lane_counts[lane] = len(picked)

    if len(selected) < TOP_N:
        fallback = [idx for idx in range(len(rows)) if idx not in selected_set]
        picked, covered = pick_unique(rows, fallback, pcts["frozen"], TOP_N - len(selected), covered)
        selected.extend(picked)
        selected_set.update(picked)
        lane_counts["fallback_frozen"] = len(picked)

    score_map = {id(row): NEG_INF for row in rows}
    for rank, index in enumerate(selected[:TOP_N]):
        score_map[id(rows[index])] = TOP_N - rank
    metrics = metrics_for_scores(rows, score_map, TOP_N, unique_anchors_only=True)
    hit_set = {int(item["anchor_prime"]) for item in metrics["hidden_numbers"] if item.get("anchor_prime") is not None}
    return {"metrics": metrics, "hit_set": hit_set, "lane_counts": lane_counts, "selected_indexes": selected[:TOP_N]}


def objective(hit_set: set[int], frozen_set: set[int]) -> float:
    lost = len(frozen_set - hit_set)
    return len(hit_set) - 2.0 * lost


def search_quotas(
    rows: list[dict[str, Any]],
    pcts: dict[str, list[float]],
    thresholds: dict[str, float],
    frozen_set: set[int],
    reliability: dict[str, float],
) -> dict[str, Any]:
    lane_order = tuple(sorted(LANES, key=lambda lane: (-reliability.get(lane, 0.0), LANES.index(lane))))
    best: dict[str, Any] | None = None
    for k_lambda in range(0, 7):
        for k_graph in range(0, 7):
            for k_cmpssz in range(0, 7):
                if k_lambda + k_graph + k_cmpssz > 8:
                    continue
                k_frozen = TOP_N - k_lambda - k_graph - k_cmpssz
                if k_frozen < 12:
                    continue
                quotas = {
                    "frozen": k_frozen,
                    "lambda": k_lambda,
                    "graph": k_graph,
                    "cmpssz": k_cmpssz,
                }
                result = select_distilled(rows, pcts, thresholds, quotas, lane_order)
                obj = objective(result["hit_set"], frozen_set)
                lost = len(frozen_set - result["hit_set"])
                candidate = {
                    "objective": obj,
                    "unique_hits": len(result["hit_set"]),
                    "lost_frozen_hits": lost,
                    "quotas": quotas,
                    "lane_order": lane_order,
                    "result": result,
                }
                if best is None or (
                    candidate["objective"],
                    candidate["unique_hits"],
                    -candidate["lost_frozen_hits"],
                    -candidate["quotas"]["frozen"],
                ) > (
                    best["objective"],
                    best["unique_hits"],
                    -best["lost_frozen_hits"],
                    -best["quotas"]["frozen"],
                ):
                    best = candidate
    if best is None:
        raise RuntimeError("quota search produced no candidates")
    return best


def proportional_quotas(winner_counts: dict[str, int], total_slots: int = TOP_N) -> dict[str, int]:
    total = sum(winner_counts.values()) or 1
    raw = {lane: winner_counts[lane] * total_slots / total for lane in LANES}
    quotas = {lane: int(math.floor(raw[lane])) for lane in LANES}
    remaining = total_slots - sum(quotas.values())
    for lane in sorted(LANES, key=lambda item: (-(raw[item] - quotas[item]), -winner_counts[item], LANES.index(item))):
        if remaining <= 0:
            break
        quotas[lane] += 1
        remaining -= 1
    return quotas


def evaluate_range(
    rows: list[dict[str, Any]],
    spec: Any,
    thresholds: dict[str, float],
    quotas: dict[str, int],
    lane_order: tuple[str, ...],
    frozen_set: set[int],
) -> dict[str, Any]:
    pcts = lane_pcts(rows, spec)
    result = select_distilled(rows, pcts, thresholds, quotas, lane_order)
    metrics = result["metrics"]
    hit_set = result["hit_set"]
    return {
        "unique_hits": len(hit_set),
        "unique_total": metrics["unique_anchors_total"],
        "delta_frozen": len(hit_set) - len(frozen_set),
        "lost_frozen_hits": len(frozen_set - hit_set),
        "new_anchors": sorted(hit_set - frozen_set),
        "lost_anchors": sorted(frozen_set - hit_set),
        "lane_counts": result["lane_counts"],
        "hidden_numbers": metrics["hidden_numbers"],
    }


def main() -> int:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spec = spec_from_report(REPORT_PATH, "holdout")

    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_200 = build_or_load_rows(200_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_250 = build_or_load_rows(250_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_300 = build_or_load_rows(300_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    range_a_all = fresh_rows(rows_100, rows_150)
    fit_a, holdout_a = split_ordered_rows(range_a_all, FIT_FRACTION)
    ranges = {
        "holdout_a": holdout_a,
        "range_b": fresh_rows(rows_150, rows_200),
        "range_c": fresh_rows(rows_200, rows_250),
        "range_d": fresh_rows(rows_250, rows_300),
    }

    fit_pcts = lane_pcts(fit_a, spec)
    distilled = backprop_explanations(fit_a, fit_pcts)
    thresholds = {lane: float(value) for lane, value in distilled["threshold"].items()}
    reliability = {lane: float(value) for lane, value in distilled["reliability"].items()}

    holdout_frozen = frozen_metrics(holdout_a, spec)
    best = search_quotas(holdout_a, lane_pcts(holdout_a, spec), thresholds, holdout_frozen["anchor_set"], reliability)
    quotas = best["quotas"]
    lane_order = tuple(best["lane_order"])
    answer_quotas = proportional_quotas({lane: int(count) for lane, count in distilled["winner_counts"].items()})

    results: dict[str, Any] = {}
    answer_quota_results: dict[str, Any] = {}
    frozen_baselines: dict[str, Any] = {}
    for name, rows in ranges.items():
        frozen = frozen_metrics(rows, spec)
        frozen_baselines[name] = {
            "unique_hits": frozen["unique_anchor_hits"],
            "unique_total": frozen["unique_anchors_total"],
            "hidden_numbers": frozen["hidden_numbers"],
        }
        results[name] = evaluate_range(rows, spec, thresholds, quotas, lane_order, frozen["anchor_set"])
        answer_quota_results[name] = evaluate_range(
            rows,
            spec,
            thresholds,
            answer_quotas,
            lane_order,
            frozen["anchor_set"],
        )

    artifact = {
        "schema": "answer_backprop_distiller_v1",
        "training": {
            "fit_range": "100M-150M first 60%",
            "selector_range": "100M-150M last 40%",
            "method": "known-anchor lane attribution -> frozen quota selector",
        },
        "frozen_spec": spec.__dict__,
        "distilled": distilled,
        "selector": {
            "quotas": quotas,
            "lane_order": list(lane_order),
            "objective": "unique_hits - 2.0 * lost_frozen_hits on holdout_a",
            "holdout_objective": best["objective"],
            "holdout_lost_frozen_hits": best["lost_frozen_hits"],
        },
        "answer_quota_selector": {
            "quotas": answer_quotas,
            "lane_order": list(lane_order),
            "source": "proportional allocation from fit_a reverse-answer lane winners",
        },
        "frozen_baselines": frozen_baselines,
        "results": results,
        "answer_quota_results": answer_quota_results,
    }

    lines = [
        "# Answer-Backprop Distiller v1",
        "",
        "Known answers are used only on fit/holdout to attribute which visible lane explains each anchor.",
        "",
        f"Lane order: `{', '.join(lane_order)}`",
        "",
        "| Lane | Fit winner count | Reliability | Threshold |",
        "| --- | ---: | ---: | ---: |",
    ]
    for lane in LANES:
        lines.append(
            "| {lane} | {count} | {rel:.6f} | {thr:.6f} |".format(
                lane=lane,
                count=distilled["winner_counts"][lane],
                rel=reliability[lane],
                thr=thresholds[lane],
            )
        )
    lines.extend(
        [
            "",
            "## Selector",
            "",
            "| Lane | Quota |",
            "| --- | ---: |",
        ]
    )
    for lane in LANES:
        lines.append(f"| {lane} | {quotas[lane]} |")
    lines.extend(
        [
            "",
            "## Answer-Quota Selector",
            "",
            "| Lane | Quota |",
            "| --- | ---: |",
        ]
    )
    for lane in LANES:
        lines.append(f"| {lane} | {answer_quotas[lane]} |")
    lines.extend(
        [
            "",
            "## Holdout-Preserve Results",
            "",
            "| Range | Frozen | Distilled | Delta | Lost frozen | New anchors |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in ("holdout_a", "range_b", "range_c", "range_d"):
        frozen = frozen_baselines[name]
        result = results[name]
        lines.append(
            f"| {name} | {frozen['unique_hits']}/{frozen['unique_total']} | "
            f"{result['unique_hits']}/{result['unique_total']} | {result['delta_frozen']:+d} | "
            f"{result['lost_frozen_hits']} | {len(result['new_anchors'])} |"
        )
    lines.extend(
        [
            "",
            "## Answer-Quota Results",
            "",
            "| Range | Frozen | Answer quota | Delta | Lost frozen | New anchors |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in ("holdout_a", "range_b", "range_c", "range_d"):
        frozen = frozen_baselines[name]
        result = answer_quota_results[name]
        lines.append(
            f"| {name} | {frozen['unique_hits']}/{frozen['unique_total']} | "
            f"{result['unique_hits']}/{result['unique_total']} | {result['delta_frozen']:+d} | "
            f"{result['lost_frozen_hits']} | {len(result['new_anchors'])} |"
        )
    lines.extend(["", "## New Anchors", ""])
    for name in ("holdout_a", "range_b", "range_c", "range_d"):
        lines.append(f"### {name}")
        lines.append("holdout-preserve: " + (", ".join(map(str, results[name]["new_anchors"])) or "-"))
        lines.append("answer-quota: " + (", ".join(map(str, answer_quota_results[name]["new_anchors"])) or "-"))
        lines.append("")

    (OUT_DIR / "distiller_v1.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:24]))
    print(OUT_DIR / "RESULTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
