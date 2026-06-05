"""Run Ring I with frozen cascade v4, then add the inverse-prime lane.

Protocol:
  1. Build/load Ring I rows (500M -> 550M).
  2. Score cascade v4 with the precommitted compressed_frozen_late weights.
  3. Only after that, score the IP lane and compare incremental anchors.

The IP lane does not read anchor labels or future-anchor fields while scoring.
It uses current scan_prime neighborhoods:

  hub_gradient = max_d tau(scan_prime - d) * exp(-d / decay)
  path_energy  = sum_d tau(scan_prime - d) * exp(-d / decay)
"""

from __future__ import annotations

import json
import math
import sys
import time
from functools import lru_cache
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
    score_dict,
    score_frozen,
    split_ordered_rows,
)
from scripts.research.run_field_gate_threshold_sensitivity import fresh_rows  # noqa: E402

try:  # Sympy is available locally and is faster/cleaner than repeated ad hoc factoring.
    from sympy import divisor_count as _sympy_divisor_count  # type: ignore
except Exception:  # pragma: no cover - fallback for stripped environments
    _sympy_divisor_count = None


WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20
FIT_FRACTION = 0.60
CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "ring_i_cascade_v4_ip"

RING_I_LOWER = 500_000_000
RING_I_UPPER = 550_000_000
IP_WINDOW = 100
IP_DECAY = 20.0


def load_frozen_spec() -> GateSpec:
    report_path = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return GateSpec(**data["frozen_spec"])


def dyn_blend(frz_z: list[float], cen_z: list[float], wf: float, wa: float, wc: float) -> list[float]:
    scores: list[float] = []
    for frozen, centroid in zip(frz_z, cen_z):
        if frozen <= NEG_INF / 10 or centroid <= NEG_INF / 10:
            scores.append(NEG_INF)
        else:
            scores.append(wf * frozen + wa * abs(frozen) + wc * centroid)
    return scores


@lru_cache(maxsize=2_000_000)
def tau(n: int) -> int:
    if n <= 1:
        return 1 if n == 1 else 0
    if _sympy_divisor_count is not None:
        return int(_sympy_divisor_count(n))

    count = 1
    d = 2
    while d * d <= n:
        if n % d == 0:
            exp = 0
            while n % d == 0:
                exp += 1
                n //= d
            count *= exp + 1
        d += 1 if d == 2 else 2
    if n > 1:
        count *= 2
    return count


def ip_features_for_prime(scan_prime: int) -> dict[str, float]:
    weighted: list[tuple[int, int, float]] = []
    for dist in range(1, IP_WINDOW + 1):
        value = scan_prime - dist
        if value < 2:
            continue
        divisor_count = tau(value)
        weight = math.exp(-dist / IP_DECAY)
        weighted.append((dist, divisor_count, divisor_count * weight))
    if not weighted:
        return {
            "hub_gradient": 0.0,
            "path_energy": 0.0,
            "hub_tau": 0.0,
            "hub_dist": 0.0,
            "tau_pm1": 0.0,
            "tail_mean_tau": 0.0,
        }

    hub_dist, hub_tau, hub_gradient = max(weighted, key=lambda item: item[2])
    tail = [tau(scan_prime - dist) for dist in range(1, min(10, IP_WINDOW) + 1) if scan_prime - dist >= 2]
    return {
        "hub_gradient": hub_gradient,
        "path_energy": sum(item[2] for item in weighted),
        "hub_tau": float(hub_tau),
        "hub_dist": float(hub_dist),
        "tau_pm1": float(tau(scan_prime - 1)) if scan_prime > 2 else 0.0,
        "tail_mean_tau": sum(tail) / len(tail) if tail else 0.0,
    }


def score_inverse_prime_lane(rows: list[dict[str, Any]]) -> tuple[list[float], list[dict[str, float]]]:
    scores: list[float] = []
    features: list[dict[str, float]] = []
    for row in rows:
        scan_prime = int(row.get("scan_prime") or 0)
        if scan_prime < 2:
            scores.append(NEG_INF)
            features.append({})
            continue
        ip = ip_features_for_prime(scan_prime)
        lambda_residual = (
            safe_float(row.get("lambda_shadow_channel", 0.0))
            + 0.5 * safe_float(row.get("lambda_gradient_channel", 0.0))
        )
        phase_alignment = max(
            0.0,
            safe_float(row.get("mode_fit_score", 0.0)) + safe_float(row.get("geodesic_trend_channel", 0.0)),
        )
        score = (
            ip["hub_gradient"]
            + 0.035 * ip["path_energy"]
            + 0.20 * ip["tau_pm1"]
            + 0.30 * lambda_residual
            + 0.20 * phase_alignment
        )
        scores.append(score)
        features.append(ip)
    return scores, features


def metric(rows: list[dict[str, Any]], scores: list[float]) -> dict[str, Any]:
    return metrics_for_scores(rows, score_dict(rows, scores), TOP_N, unique_anchors_only=True)


def anchors(item: dict[str, Any]) -> set[int]:
    return {
        int(number["anchor_prime"])
        for number in item.get("hidden_numbers", [])
        if number.get("anchor_prime") is not None
    }


def summarize_method(name: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "unique_anchor_hits": item["unique_anchor_hits"],
        "unique_anchors_total": item["unique_anchors_total"],
        "top_hits": item["top_hits"],
        "duplicate_anchor_hits": item["duplicate_anchor_hits"],
        "anchors": sorted(anchors(item)),
        "hidden_numbers": item.get("hidden_numbers", []),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Ring I Cascade v4 + Inverse Prime Lane",
        "",
        "Protocol order:",
        "",
        "1. Score frozen cascade v4 on Ring I.",
        "2. Score inverse-prime lane as a ninth controller.",
        "3. Compare only incremental anchors after the v4 baseline is recorded.",
        "",
        "## Summary",
        "",
        f"- Range: `{report['range']}`",
        f"- Row count: `{report['row_count']}`",
        f"- Known anchors after verification: `{report['unique_anchors_total']}`",
        f"- Cascade v4 regime: `{report['cascade_v4']['regime']}`",
        f"- Cascade v4 weights: `{report['cascade_v4']['weights']}`",
        "",
        "| Method | Row hits | Unique anchors | Duplicate hits | New vs v4 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key in ("frozen", "cascade_v4", "inverse_prime", "v4_or_ip_union"):
        item = report["methods"][key]
        row_hits = f"{item['top_hits']}/20" if isinstance(item["top_hits"], int) else str(item["top_hits"])
        lines.append(
            "| {name} | {row_hits} | {unique_anchor_hits}/{unique_anchors_total} | {duplicate_anchor_hits} | {new_vs_v4} |".format(
                row_hits=row_hits,
                **item
            )
        )

    lines.extend(
        [
            "",
            "## Incremental IP Anchors",
            "",
            "Anchors found by IP top-20 that cascade v4 did not find:",
            "",
        ]
    )
    if report["ip_new_anchors"]:
        lines.append(", ".join(str(anchor) for anchor in report["ip_new_anchors"]))
    else:
        lines.append("None.")

    lines.extend(
        [
            "",
            "## Cascade v4 Hidden Numbers",
            "",
            "| Rank | Anchor prime | Ratio | Lead | Scan prime | Score |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for number in report["methods"]["cascade_v4"]["hidden_numbers"]:
        lines.append(
            "| {rank} | {anchor_prime} | {anchor_ratio} | {lead_steps} | {scan_prime} | {score} |".format(**number)
        )

    lines.extend(
        [
            "",
            "## IP Hidden Numbers",
            "",
            "| Rank | Anchor prime | Ratio | Lead | Scan prime | Score |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for number in report["methods"]["inverse_prime"]["hidden_numbers"]:
        lines.append(
            "| {rank} | {anchor_prime} | {anchor_ratio} | {lead_steps} | {scan_prime} | {score} |".format(**number)
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    start = time.time()
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = load_frozen_spec()
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    fit_a, _holdout_a = split_ordered_rows(fresh_rows(rows_100, rows_150), FIT_FRACTION)

    frozen_fit = score_frozen(fit_a, frozen_spec)
    frozen_mean, frozen_scale = fit_score_normalizer(frozen_fit)
    centroid_model = fit_centroid_ranker(matrix(fit_a), labels(fit_a))
    centroid_fit = linear_scores(centroid_model, matrix(fit_a))
    centroid_mean, centroid_scale = fit_score_normalizer(centroid_fit)

    rows_500 = build_or_load_rows(RING_I_LOWER, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_550 = build_or_load_rows(RING_I_UPPER, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    ring_i = fresh_rows(rows_500, rows_550)

    frozen_raw = score_frozen(ring_i, frozen_spec)
    frozen_z = apply_score_normalizer(frozen_raw, frozen_mean, frozen_scale)
    centroid_z = apply_score_normalizer(linear_scores(centroid_model, matrix(ring_i)), centroid_mean, centroid_scale)

    v4_spec = json.loads((REPO_ROOT / "artifacts" / "range_regime_classifier" / "cascade_v4_spec.json").read_text())
    v4_regime = v4_spec["ring_i_prediction"]["v4_regime"]
    v4_weights = v4_spec["ring_i_prediction"]["v4_weights"]
    v4_scores = dyn_blend(
        frozen_z,
        centroid_z,
        float(v4_weights["w_f"]),
        float(v4_weights["w_a"]),
        float(v4_weights["w_c"]),
    )

    print("Ring I cascade v4 scored before IP comparison.", flush=True)
    frozen_m = metric(ring_i, frozen_z)
    v4_m = metric(ring_i, v4_scores)

    ip_scores, ip_features = score_inverse_prime_lane(ring_i)
    ip_m = metric(ring_i, ip_scores)

    v4_anchor_set = anchors(v4_m)
    ip_anchor_set = anchors(ip_m)
    frozen_anchor_set = anchors(frozen_m)
    union_anchor_set = v4_anchor_set | ip_anchor_set

    method_summaries = {
        "frozen": summarize_method("frozen", frozen_m),
        "cascade_v4": summarize_method("cascade_v4", v4_m),
        "inverse_prime": summarize_method("inverse_prime", ip_m),
        "v4_or_ip_union": {
            "name": "v4_or_ip_union",
            "unique_anchor_hits": len(union_anchor_set),
            "unique_anchors_total": v4_m["unique_anchors_total"],
            "top_hits": "n/a",
            "duplicate_anchor_hits": "n/a",
            "anchors": sorted(union_anchor_set),
            "hidden_numbers": [],
        },
    }
    for key, item in method_summaries.items():
        item["new_vs_v4"] = len(set(item["anchors"]) - v4_anchor_set)
    method_summaries["frozen"]["new_vs_v4"] = len(frozen_anchor_set - v4_anchor_set)

    report = {
        "schema": "ring_i_cascade_v4_ip_v1",
        "range": "500M-550M",
        "row_count": len(ring_i),
        "unique_anchors_total": v4_m["unique_anchors_total"],
        "cascade_v4": {"regime": v4_regime, "weights": v4_weights},
        "ip_lane": {
            "window": IP_WINDOW,
            "decay": IP_DECAY,
            "score": "hub_gradient + 0.035*path_energy + 0.20*tau_pm1 + 0.30*lambda_residual + 0.20*phase_alignment",
            "scoring_fields": [
                "scan_prime",
                "lambda_shadow_channel",
                "lambda_gradient_channel",
                "mode_fit_score",
                "geodesic_trend_channel",
            ],
        },
        "methods": method_summaries,
        "ip_new_anchors": sorted(ip_anchor_set - v4_anchor_set),
        "v4_missed_frozen_anchors": sorted(frozen_anchor_set - v4_anchor_set),
        "sample_ip_features": ip_features[:5],
        "elapsed_seconds": round(time.time() - start, 3),
    }

    (OUT_DIR / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, OUT_DIR / "RESULTS.md")

    print(
        "Ring I results: "
        f"frozen={frozen_m['unique_anchor_hits']}/{frozen_m['unique_anchors_total']} "
        f"v4={v4_m['unique_anchor_hits']}/{v4_m['unique_anchors_total']} "
        f"ip={ip_m['unique_anchor_hits']}/{ip_m['unique_anchors_total']} "
        f"union={len(union_anchor_set)}/{v4_m['unique_anchors_total']} "
        f"ip_new_vs_v4={len(ip_anchor_set - v4_anchor_set)}",
        flush=True,
    )
    print(f"Wrote {OUT_DIR / 'RESULTS.md'}", flush=True)


if __name__ == "__main__":
    main()
