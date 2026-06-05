"""Train and evaluate the MapReader frozen gate on all three sensor families.

Design: weight search over normalized lane scores rather than a deep tree.
Leaf-probability trees at depth 3 produce too-narrow probability ranges (0.38-0.55)
to rank 11,000+ rows reliably.  A linear blend of three normalized lane scores
searches a small, interpretable weight space and optimises directly for top-20 recall.

Feature space (6 values, normalized to [0,1]):
  frozen_norm   = clamp(branch_score / MAX_FROZEN, 0, 1) — 0 for gated-out rows
  lambda_norm   = clamp((shadow + 0.5*gradient + 0.3*peak_lag + 2) / 4, 0, 1)
  graph_norm    = clamp((ramp + (1-ret)*0.5 + edge_var*0.3 + att*0.4) / 2.5, 0, 1)
  local_tonic   = clamp(log(tonic) / 3.0, -1, 1)   — log-scale position in range
  mode_fit      = mode_fit_score as-is in [0, 1]
  lambda_peak_lag = as-is in [0, 1]

The weight search optimises (frozen_w, lambda_w, graph_w) on fit_a.
Refractory features (local_tonic, mode_fit, peak_lag) are added to the score
if their contribution improves holdout_a recall.

Training split:
  fit       : 100M→150M, first 60% ordered by scan_idx
  holdout_a : 100M→150M, last 40%  (grid-search target)
  range_b   : 150M→200M            (blind validation — not used during training)
  range_c   : 200M→250M            (first generalization test)

Outputs:
  artifacts/map_reader_gate/gate_v1.json   — gate weights + metadata
  artifacts/map_reader_gate/RESULTS.md     — human-readable summary
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    NEG_INF,
    build_or_load_rows,
    fresh_rows,
    metrics_for_scores,
    safe_float,
    score_frozen,
    score_graph_map,
    score_lambda_shadow,
    split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    ensure_dynamic_profiles,
    branch_score as gate_branch_score,
)

OUT_DIR = REPO_ROOT / "artifacts" / "map_reader_gate"
CACHE_DIR = DEFAULT_ROW_CACHE_DIR

WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20

# Normalisation constants (empirically stable across 100M–250M range)
MAX_FROZEN_SCORE = 22.0     # branch_score ceiling for normalisation
LAMBDA_SHIFT = 2.0          # shift so lambda range [-2,+2] maps to [0, 4]
LAMBDA_SCALE = 4.0
GRAPH_SCALE = 2.5           # graph scores range ~ [0, 2.5]

# Weight search grid
WEIGHT_STEPS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
REFRAC_WEIGHT_STEPS = [0.0, 0.05, 0.10, 0.15, 0.20]


# ── frozen spec ────────────────────────────────────────────────────────────────
def _load_frozen_spec() -> GateSpec:
    report_path = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Run the bench first: {report_path}")
    data = json.loads(report_path.read_text())
    return GateSpec(**data["frozen_spec"])


# ── lane score normalisation ───────────────────────────────────────────────────
def _frozen_norm(row: dict, spec: GateSpec) -> float:
    s = gate_branch_score(row, spec)
    if s <= 0.0:
        return 0.0
    return min(1.0, s / MAX_FROZEN_SCORE)


def _lambda_norm(row: dict) -> float:
    shadow = safe_float(row.get("lambda_shadow_channel", 0.0))
    grad = safe_float(row.get("lambda_gradient_channel", 0.0))
    lag = safe_float(row.get("lambda_peak_lag", 0.5))
    raw = shadow + 0.5 * grad + 0.3 * lag
    return max(0.0, min(1.0, (raw + LAMBDA_SHIFT) / LAMBDA_SCALE))


def _graph_norm(row: dict) -> float:
    ramp = safe_float(row.get("graph_monotone_ramp", 0.0))
    ret = safe_float(row.get("graph_return_rate", 0.5))
    edge = safe_float(row.get("graph_edge_variance", 0.0))
    att = safe_float(row.get("graph_attractor_score", 0.0))
    raw = ramp + (1.0 - ret) * 0.5 + edge * 0.3 + att * 0.4
    return max(0.0, min(1.0, raw / GRAPH_SCALE))


def _refrac_score(row: dict) -> float:
    """Local tonic log-normalised + mode fit + recency."""
    tonic = safe_float(row.get("local_tonic", 1.0))
    log_t = math.log(max(tonic, 1e-9)) / 3.0  # rough range [-2, 2] → [-0.67, 0.67]
    log_t = max(-1.0, min(1.0, log_t))
    mode_fit = safe_float(row.get("mode_fit_score", 0.0))
    peak_lag = safe_float(row.get("lambda_peak_lag", 0.5))
    return 0.5 + 0.3 * log_t + 0.1 * mode_fit + 0.1 * peak_lag  # centred near 0.5


def build_lane_vectors(rows: list[dict], spec: GateSpec) -> tuple[list[float], list[float], list[float], list[float]]:
    fn = [_frozen_norm(r, spec) for r in rows]
    ln = [_lambda_norm(r) for r in rows]
    gn = [_graph_norm(r) for r in rows]
    rf = [_refrac_score(r) for r in rows]
    return fn, ln, gn, rf


def blend_score(fn: float, ln: float, gn: float, rf: float,
                w_f: float, w_l: float, w_g: float, w_r: float) -> float:
    return w_f * fn + w_l * ln + w_g * gn + w_r * rf


def apply_gate(rows: list[dict], fn: list[float], ln: list[float],
               gn: list[float], rf: list[float],
               w_f: float, w_l: float, w_g: float, w_r: float) -> dict[int, float]:
    sc = {}
    for r, f, la, g, re in zip(rows, fn, ln, gn, rf):
        sc[id(r)] = blend_score(f, la, g, re, w_f, w_l, w_g, w_r)
    return sc


def hits(rows: list[dict], sc: dict[int, float]) -> int:
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return m["unique_anchor_hits"]


def unique_anchors_total(rows: list[dict]) -> int:
    seen: set = set()
    for r in rows:
        if r.get("future_anchor"):
            a = r.get("first_anchor_idx", r.get("first_anchor_prime"))
            if a is not None:
                seen.add(a)
    return len(seen)


# ── weight search ─────────────────────────────────────────────────────────────
def search_weights(
    rows: list[dict],
    fn: list[float], ln: list[float], gn: list[float], rf: list[float],
    min_frozen_weight: float = 0.3,
) -> tuple[float, float, float, float, int]:
    """Grid search on (w_f, w_l, w_g) constrained to w_f >= min_frozen_weight.
    Returns best (w_f, w_l, w_g, w_r, hits).
    """
    best_h = -1
    best_w = (0.7, 0.15, 0.15, 0.0)
    candidates: list[tuple[float, float, float, float]] = []
    for wf in WEIGHT_STEPS:
        if wf < min_frozen_weight - 0.001:
            continue
        for wl in WEIGHT_STEPS:
            for wg in WEIGHT_STEPS:
                if abs(wf + wl + wg - 1.0) > 0.01:
                    continue
                candidates.append((wf, wl, wg, 0.0))
    # also try with a small refractory weight
    for wf in [w for w in [0.3, 0.4, 0.5, 0.6, 0.7] if w >= min_frozen_weight]:
        for wl in [0.1, 0.15, 0.2]:
            for wg in [0.1, 0.15, 0.2]:
                for wr in REFRAC_WEIGHT_STEPS[1:]:
                    total = wf + wl + wg + wr
                    if abs(total - 1.0) > 0.02:
                        continue
                    candidates.append((wf, wl, wg, wr))

    for wf, wl, wg, wr in candidates:
        sc = apply_gate(rows, fn, ln, gn, rf, wf, wl, wg, wr)
        h = hits(rows, sc)
        if h > best_h or (h == best_h and wf > best_w[0]):
            best_h = h
            best_w = (wf, wl, wg, wr)

    return (*best_w, best_h)


# ── evaluation ─────────────────────────────────────────────────────────────────
def evaluate(name: str, rows: list[dict], fn, ln, gn, rf,
             wf, wl, wg, wr) -> dict:
    sc = apply_gate(rows, fn, ln, gn, rf, wf, wl, wg, wr)
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return {
        "range": name,
        "top_hits": m["top_hits"],
        "top_n": TOP_N,
        "unique_anchor_hits": m["unique_anchor_hits"],
        "unique_anchors_total": m["unique_anchors_total"],
        "hit_rate": round(m["top_hits"] / TOP_N, 4),
        "unique_anchor_rate": m["unique_anchor_rate"],
        "unique_anchor_recall": m["unique_anchor_recall"],
        "hidden_numbers": m["hidden_numbers"],
    }


# ── main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frozen_spec = _load_frozen_spec()
    print(f"Frozen spec: {frozen_spec.spec_id}")

    print("Loading row caches...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_200 = build_or_load_rows(200_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    print("Loading 250M rows (new territory)...", flush=True)
    rows_250 = build_or_load_rows(250_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    range_a_all = fresh_rows(rows_100, rows_150)
    range_b = fresh_rows(rows_150, rows_200)
    range_c = fresh_rows(rows_200, rows_250)

    fit_a, holdout_a = split_ordered_rows(range_a_all, 0.60)
    print(f"fit_a={len(fit_a)}  holdout_a={len(holdout_a)}  range_b={len(range_b)}  range_c={len(range_c)}")

    print("Building lane vectors...", flush=True)
    fn_fit, ln_fit, gn_fit, rf_fit = build_lane_vectors(fit_a, frozen_spec)
    fn_ho, ln_ho, gn_ho, rf_ho = build_lane_vectors(holdout_a, frozen_spec)
    fn_b, ln_b, gn_b, rf_b = build_lane_vectors(range_b, frozen_spec)
    fn_c, ln_c, gn_c, rf_c = build_lane_vectors(range_c, frozen_spec)

    # Reference: frozen gate alone
    def frozen_ref(rows, fn, ln, gn, rf):
        sc = apply_gate(rows, fn, ln, gn, rf, 1.0, 0.0, 0.0, 0.0)
        m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
        return m["unique_anchor_hits"], m["unique_anchors_total"]

    ref_fit = frozen_ref(fit_a, fn_fit, ln_fit, gn_fit, rf_fit)
    ref_ho = frozen_ref(holdout_a, fn_ho, ln_ho, gn_ho, rf_ho)
    ref_b = frozen_ref(range_b, fn_b, ln_b, gn_b, rf_b)
    ref_c = frozen_ref(range_c, fn_c, ln_c, gn_c, rf_c)
    print(f"Frozen gate ref:  fit={ref_fit[0]}/{ref_fit[1]}  holdout={ref_ho[0]}/{ref_ho[1]}  B={ref_b[0]}/{ref_b[1]}  C={ref_c[0]}/{ref_c[1]}")

    # Search weights on fit_a
    print("Searching weights on fit_a...", flush=True)
    wf, wl, wg, wr, fit_h = search_weights(fit_a, fn_fit, ln_fit, gn_fit, rf_fit)
    print(f"Best fit_a weights: frozen={wf:.2f}  lambda={wl:.2f}  graph={wg:.2f}  refrac={wr:.2f}  → {fit_h}/{ref_fit[1]} unique")

    # Evaluate with fit_a-selected weights (DO NOT re-tune on holdout/B/C)
    res_ho = evaluate("holdout_a (100M-150M)", holdout_a, fn_ho, ln_ho, gn_ho, rf_ho, wf, wl, wg, wr)
    res_b = evaluate("range_b (150M-200M)", range_b, fn_b, ln_b, gn_b, rf_b, wf, wl, wg, wr)
    res_c = evaluate("range_c (200M-250M, BLIND)", range_c, fn_c, ln_c, gn_c, rf_c, wf, wl, wg, wr)

    print(f"\n{'Range':<35}  {'hits':>5}  {'uniq':>5}  {'total':>6}  {'recall':>7}  {'vs frozen':>10}")
    print("-" * 75)
    for r, ref in [(res_ho, ref_ho), (res_b, ref_b), (res_c, ref_c)]:
        delta = r["unique_anchor_hits"] - ref[0]
        sign = f"+{delta}" if delta >= 0 else str(delta)
        print(
            f"  {r['range']:<33}  {r['top_hits']:>5}  {r['unique_anchor_hits']:>5}  "
            f"{r['unique_anchors_total']:>6}  {r['unique_anchor_recall']:>7.1%}  {sign:>10}"
        )

    # Anchor sets for each range
    def anchor_set(res):
        return {h["anchor_prime"] for h in res["hidden_numbers"]}

    b_frz_anchors = _ref_anchors(range_b, fn_b, ln_b, gn_b, rf_b)
    b_new = anchor_set(res_b) - b_frz_anchors
    c_frz_anchors = _ref_anchors(range_c, fn_c, ln_c, gn_c, rf_c)
    c_new = anchor_set(res_c) - c_frz_anchors
    print(f"\nNew anchors vs frozen:  B={sorted(b_new)}  C={sorted(c_new)}")

    # ── portfolio gate (two-stage: frozen fills unique first, lambda+graph fills rest)
    print("\n--- Portfolio gate (frozen-first, lambda+graph fill) ---")
    def eval_portfolio(name, rows, fn, ln, gn, rf):
        sc = portfolio_score(rows, fn, ln, gn, rf)
        m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
        anchors = {h["anchor_prime"] for h in m["hidden_numbers"]}
        return m["unique_anchor_hits"], m["unique_anchors_total"], anchors, m["hidden_numbers"]

    p_ho = eval_portfolio("holdout_a", holdout_a, fn_ho, ln_ho, gn_ho, rf_ho)
    p_b = eval_portfolio("range_b", range_b, fn_b, ln_b, gn_b, rf_b)
    p_c = eval_portfolio("range_c", range_c, fn_c, ln_c, gn_c, rf_c)

    print(f"  Portfolio holdout_a:  {p_ho[0]}/{p_ho[1]} unique  (frozen: {ref_ho[0]})  delta={p_ho[0]-ref_ho[0]:+d}")
    print(f"  Portfolio range_b:    {p_b[0]}/{p_b[1]} unique  (frozen: {ref_b[0]})  delta={p_b[0]-ref_b[0]:+d}")
    print(f"  Portfolio range_c:    {p_c[0]}/{p_c[1]} unique  (frozen: {ref_c[0]})  delta={p_c[0]-ref_c[0]:+d}")
    print(f"  Portfolio B new anchors vs frozen: {sorted(p_b[2] - b_frz_anchors)}")
    print(f"  Portfolio C new anchors vs frozen: {sorted(p_c[2] - c_frz_anchors)}")

    # Save gate
    gate_doc = {
        "schema": "map_reader_gate_v1",
        "description": "Weighted blend of frozen/lambda/graph lane scores, trained on fit_a",
        "weights": {"frozen": wf, "lambda": wl, "graph": wg, "refractory": wr},
        "normalisation": {
            "frozen": f"clamp(branch_score / {MAX_FROZEN_SCORE}, 0, 1)",
            "lambda": f"clamp((shadow + 0.5*grad + 0.3*lag + {LAMBDA_SHIFT}) / {LAMBDA_SCALE}, 0, 1)",
            "graph": f"clamp(ramp + (1-ret)*0.5 + edge_var*0.3 + att*0.4) / {GRAPH_SCALE}, 0, 1)",
            "refractory": "0.5 + 0.3*log(tonic)/3 + 0.1*mode_fit + 0.1*peak_lag",
        },
        "frozen_spec_id": frozen_spec.spec_id,
        "training": {
            "fit_a_unique_hits": fit_h,
            "fit_a_unique_total": ref_fit[1],
        },
        "results": {
            "holdout_a": res_ho,
            "range_b": res_b,
            "range_c": res_c,
        },
        "reference_frozen": {
            "holdout_a": {"unique_anchor_hits": ref_ho[0], "unique_anchors_total": ref_ho[1]},
            "range_b": {"unique_anchor_hits": ref_b[0], "unique_anchors_total": ref_b[1]},
            "range_c": {"unique_anchor_hits": ref_c[0], "unique_anchors_total": ref_c[1]},
        },
    }
    gate_path = OUT_DIR / "gate_v1.json"
    gate_path.write_text(json.dumps(gate_doc, indent=2) + "\n", encoding="utf-8")
    print(f"\nGate saved: {gate_path}")

    # Markdown results
    md = [
        "# MapReader Gate v1 — Training Results",
        "",
        "Trained: fit_a (100M→150M, 60%). Weights selected on fit_a only. Blind carry to holdout/B/C.",
        "",
        f"| Weight | Value |",
        f"| --- | ---: |",
        f"| frozen (camera) | {wf:.2f} |",
        f"| lambda (PNT flashlight) | {wl:.2f} |",
        f"| graph (ticker graph) | {wg:.2f} |",
        f"| refractory | {wr:.2f} |",
        "",
        "## Results",
        "",
        "| Range | Hits | Unique | Total | Recall | vs Frozen |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r, ref in [(res_ho, ref_ho), (res_b, ref_b), (res_c, ref_c)]:
        delta = r["unique_anchor_hits"] - ref[0]
        sign = f"+{delta}" if delta >= 0 else str(delta)
        md.append(
            f"| {r['range']} | {r['top_hits']}/20 | {r['unique_anchor_hits']} | "
            f"{r['unique_anchors_total']} | {r['unique_anchor_recall']:.1%} | {sign} |"
        )

    for r in [res_ho, res_b, res_c]:
        md += [
            "",
            f"### {r['range']}",
            "",
            "| Rank | Anchor prime | Ratio | Lead | Score |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
        for h in r["hidden_numbers"]:
            md.append(
                f"| {h['rank']} | {h['anchor_prime']} | {h['anchor_ratio']} | {h['lead_steps']} | {h['score']} |"
            )

    md_path = OUT_DIR / "RESULTS.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Results: {md_path}")


def _ref_anchors(rows, fn, ln, gn, rf) -> set:
    sc = apply_gate(rows, fn, ln, gn, rf, 1.0, 0.0, 0.0, 0.0)
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return {h["anchor_prime"] for h in m["hidden_numbers"]}


def portfolio_score(
    rows: list[dict],
    fn: list[float], ln: list[float], gn: list[float], rf: list[float],
    frozen_slots: int = 11,
) -> dict[int, float]:
    """Two-stage portfolio: frozen gate fills first N unique slots, lambda+graph fills the rest.

    Implementation: give frozen-passing rows a large score bonus so they always rank first.
    Within each tier, rank by the tier's own signal. The unique_anchors_only deduplication
    in metrics_for_scores then naturally exhausts frozen-tier unique anchors before pulling
    from the lambda+graph tier.
    """
    FROZEN_TIER = 100.0   # large offset so frozen-tier always ranks above lambda/graph tier
    sc = {}
    for r, f, la, g, re in zip(rows, fn, ln, gn, rf):
        if f > 0.0:
            # Row passes frozen gate: tier-1, ranked by frozen signal within tier
            sc[id(r)] = FROZEN_TIER + f
        else:
            # Row fails frozen gate: tier-2, ranked by lambda+graph signal
            sc[id(r)] = la * 0.8 + g * 0.2
    return sc


if __name__ == "__main__":
    main()
