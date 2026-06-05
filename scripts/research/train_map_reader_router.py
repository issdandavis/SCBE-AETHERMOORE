"""
Map Reader Router v2 — Frozen-preserving three-phase residual routing.

Core design
-----------
Each lane runs its own unique-anchor selection independently.  Frozen gets
first refusal; lambda/graph fill from the residual (rows not already covered
by frozen's anchor set).

Phase 1 — Frozen selection
  Rows with frz_pct >= frozen_keep_pct form the "frozen candidate pool."
  From that pool, take the top k_f rows by frz_pct with unique_anchors_only.
  Record the set of covered anchor primes.

Phase 2 — Lambda fill
  Rows NOT in the frozen candidate pool are the residual.
  From residual, take the top k_l rows by lam_pct that cover NEW anchor
  primes (not already in frozen's covered set).

Phase 3 — Graph fill
  From residual (excluding lambda picks), take the top k_g rows by grph_pct
  that cover NEW anchor primes not yet covered.

Search objective (asymmetric)
  obj = unique_total_hits - 2.0 * lost_frozen_hits
  Hard invariant: obj is only better than frozen when new anchors exceed 2×
  lost anchors — so the search naturally avoids eroding the frozen baseline.

Key parameters
  frozen_keep_pct   0.80 | 0.85 | 0.90 | 0.95
  k_lambda_fill     0 … 6
  k_graph_fill      0 … 6   (k_f = TOP_N - k_l - k_g, must be >= 14)

Why three-phase beats tier-priority
  With ~53% anchor-row density and ~24 rows per unique prime in the cache,
  pre-selecting exactly k_f rows and giving the rest NEG_INF causes
  unique_anchors_only dedup to collapse those k_f rows to 3-4 unique primes.
  The frozen gate gets 10/111 only because it searches the full pool.
  Three-phase keeps full-pool access per lane; the covered-anchor tracking
  prevents double-counting across lanes.
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
    split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import GateSpec, ensure_dynamic_profiles  # noqa: E402

OUT_DIR = REPO_ROOT / "artifacts" / "map_reader_router"
CACHE_DIR = DEFAULT_ROW_CACHE_DIR

WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0
TOP_N = 20
FIT_FRACTION = 0.60

LANE_FROZEN = 0
LANE_LAMBDA = 1
LANE_GRAPH  = 2
LANE_NAMES  = ["frozen", "lambda", "graph"]


# ── Lane scoring ───────────────────────────────────────────────────────────────

def _get(row: dict, key: str) -> float:
    return safe_float(row.get(key, 0.0))


def lambda_composite(row: dict) -> float:
    return (_get(row, "lambda_shadow_channel")
            + 0.5 * _get(row, "lambda_gradient_channel")
            + 0.3 * _get(row, "lambda_peak_lag"))


def graph_composite(row: dict) -> float:
    ret = _get(row, "graph_return_rate")
    return (_get(row, "graph_monotone_ramp")
            + (1.0 - ret) * 0.5
            + _get(row, "graph_edge_variance") * 0.3
            + _get(row, "graph_attractor_score") * 0.4)


def compute_lane_scores(rows: list[dict], spec: GateSpec) -> tuple[list[float], list[float], list[float]]:
    return score_frozen(rows, spec), [lambda_composite(r) for r in rows], [graph_composite(r) for r in rows]


def z_norm(raw: list[float]) -> list[float]:
    vals = [v for v in raw if v > NEG_INF / 10]
    if not vals:
        return raw
    mean = sum(vals) / len(vals)
    sd   = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) or 1.0
    return [(v - mean) / sd if v > NEG_INF / 10 else v for v in raw]


def rank_pct(scores: list[float]) -> list[float]:
    """Return rank percentile in [0, 1] for each element (higher score → higher pct)."""
    n = len(scores)
    order = sorted(range(n), key=lambda i: scores[i])
    pct = [0.0] * n
    for rank, i in enumerate(order):
        pct[i] = rank / max(n - 1, 1)
    return pct


# ── Three-phase residual selection ────────────────────────────────────────────

def _pick_unique_anchor(
    rows: list[dict],
    candidate_idx: list[int],
    score_pct: list[float],
    k: int,
    already_covered: set,
) -> tuple[list[int], set]:
    """
    From candidate_idx sorted by score_pct descending, pick up to k rows.
    Each row must either be a non-anchor row OR have an anchor_prime not in
    already_covered.  Returns (selected_idx, updated_covered).
    """
    covered = set(already_covered)
    selected = []
    for i in sorted(candidate_idx, key=lambda j: -score_pct[j]):
        if len(selected) >= k:
            break
        r = rows[i]
        anchor = r.get("first_anchor_prime") if r.get("future_anchor") else None
        if anchor is None or anchor not in covered:
            selected.append(i)
            if anchor is not None:
                covered.add(anchor)
    return selected, covered


def three_phase_select(
    rows: list[dict],
    frz_pct: list[float],
    lam_pct: list[float],
    grph_pct: list[float],
    k_l: int,
    k_g: int,
) -> dict:
    """
    Three-phase anchor selection.

    Phase 1 — Frozen selects k_f unique-anchor rows from ALL rows by frz_pct.
    Phase 2 — Lambda fills k_l slots from rows NOT selected by frozen,
               only accepting rows with NEW anchor primes (not already covered).
    Phase 3 — Graph fills k_g slots from remaining rows, same NEW-prime constraint.

    The 'not selected by frozen' pool includes rows that frozen bypassed because
    their anchor prime was already claimed — these are the rows lambda/graph can
    upgrade with their own signal.

    Returns dict with:
      unique_hits     — total unique anchor primes hit
      covered_anchors — set of anchor primes covered
      lane_counts     — {frozen_sel, lambda_sel, graph_sel}
    """
    k_f = TOP_N - k_l - k_g
    n   = len(rows)
    all_idx = list(range(n))

    # Phase 1: frozen selects k_f rows from ALL rows
    frz_selected, covered = _pick_unique_anchor(rows, all_idx, frz_pct, k_f, set())
    frz_set = set(frz_selected)

    # Phase 2: lambda fills from all UNSELECTED rows
    lambda_candidates = [i for i in all_idx if i not in frz_set]
    lam_selected, covered = _pick_unique_anchor(rows, lambda_candidates, lam_pct, k_l, covered)

    # Phase 3: graph fills from remaining unselected rows
    lam_set = set(lam_selected)
    graph_candidates = [i for i in lambda_candidates if i not in lam_set]
    grph_selected, covered = _pick_unique_anchor(rows, graph_candidates, grph_pct, k_g, covered)

    unique_hits = len({rows[i].get("first_anchor_prime")
                       for i in frz_selected + lam_selected + grph_selected
                       if rows[i].get("future_anchor")})

    return {
        "unique_hits":     unique_hits,
        "covered_anchors": covered,
        "lane_counts":     {
            "frozen_sel":  len(frz_selected),
            "lambda_sel":  len(lam_selected),
            "graph_sel":   len(grph_selected),
        },
    }


def router_objective(hits: int, lost_frozen: int) -> float:
    return hits - 2.0 * lost_frozen


# ── Frozen baseline ────────────────────────────────────────────────────────────

def frozen_anchor_set(rows: list[dict], spec: GateSpec) -> tuple[set, int]:
    sc = {id(r): s for r, s in zip(rows, score_frozen(rows, spec))}
    m  = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return {h["anchor_prime"] for h in m["hidden_numbers"]}, m["unique_anchors_total"]


# ── Oracle lane coverage (diagnostic) ─────────────────────────────────────────

def oracle_lane_coverage(rows: list[dict], spec: GateSpec) -> dict:
    frz_r, lam_r, grph_r = compute_lane_scores(rows, spec)
    def anchors(r):
        return {h["anchor_prime"] for h in metrics_for_scores(
            rows, {id(x): s for x, s in zip(rows, r)},
            TOP_N, unique_anchors_only=True)["hidden_numbers"]}
    fa, la, ga = anchors(frz_r), anchors(lam_r), anchors(grph_r)
    return {
        "frozen_hits": sorted(fa), "lambda_hits": sorted(la), "graph_hits": sorted(ga),
        "frozen_only": sorted(fa - la - ga),
        "lambda_unique": sorted(la - fa),
        "graph_unique":  sorted(ga - fa - la),
        "union_size": len(fa | la | ga),
        "triple_intersect": len(fa & la & ga),
    }


# ── Electoral scoring ─────────────────────────────────────────────────────────

def electoral_score_dict(
    rows: list[dict],
    frz_z: list[float],
    lam_z: list[float],
    grph_z: list[float],
    frz_weight: float,
    lam_weight: float,
    grph_weight: float,
    nominate_k: int,
) -> dict:
    """
    Build an electoral score dict.
    Each sensor nominates its top-nominate_k rows by z-score.
    A row's score = sum(weight_i for sensors that nominated it)
                  + tiebreaker from average z-score across nominating sensors.

    frz_weight: frozen sensor weight (default 3.0)
    lam_weight: lambda sensor weight (default 2.0)
    grph_weight: graph sensor weight (default 1.0)
    nominate_k: how many candidates each sensor nominates (≥ TOP_N)
    """
    n = len(rows)
    frz_top  = set(sorted(range(n), key=lambda i: -frz_z[i])[:nominate_k])
    lam_top  = set(sorted(range(n), key=lambda i: -lam_z[i])[:nominate_k])
    grph_top = set(sorted(range(n), key=lambda i: -grph_z[i])[:nominate_k])

    sc = {}
    for i, r in enumerate(rows):
        votes   = 0.0
        z_sum   = 0.0
        z_count = 0
        if i in frz_top:
            votes += frz_weight
            z_sum  += frz_z[i]
            z_count += 1
        if i in lam_top:
            votes += lam_weight
            z_sum  += lam_z[i]
            z_count += 1
        if i in grph_top:
            votes += grph_weight
            z_sum  += grph_z[i]
            z_count += 1
        if votes > 0:
            sc[id(r)] = votes + (z_sum / z_count) * 1e-4
        else:
            sc[id(r)] = NEG_INF
    return sc


def eval_electoral(
    rows: list[dict],
    frz_z: list[float],
    lam_z: list[float],
    grph_z: list[float],
    frz_weight: float,
    lam_weight: float,
    grph_weight: float,
    nominate_k: int,
    frozen_anchors: set,
) -> dict:
    sc = electoral_score_dict(rows, frz_z, lam_z, grph_z,
                              frz_weight, lam_weight, grph_weight, nominate_k)
    m  = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    hit_set = {h["anchor_prime"] for h in m["hidden_numbers"]}
    hits = m["unique_anchor_hits"]
    lost = len(frozen_anchors - hit_set)
    return {
        "unique_hits":       hits,
        "unique_total":      m["unique_anchors_total"],
        "covered_anchors":   hit_set,
        "delta_frozen":      hits - len(frozen_anchors),
        "lost_frozen_hits":  lost,
        "objective":         router_objective(hits, lost),
        "new_anchors":       sorted(hit_set - frozen_anchors),
        "lost_anchors":      sorted(frozen_anchors - hit_set),
    }


def search_electoral(
    rows: list[dict],
    frz_z: list[float],
    lam_z: list[float],
    grph_z: list[float],
    frozen_anchors: set,
) -> tuple:
    """
    Grid search: frz_weight in {3,2,1}, lam_weight in {2,1}, grph_weight in {1},
    nominate_k in {20, 30, 40, 60}.
    Returns (frz_w, lam_w, grph_w, k, best_obj, best_hits, best_lost).
    """
    best_obj   = -1e9
    best_hits  = 0
    best_lost  = 0
    best_params = (3, 2, 1, 40)

    for frz_w in (3.0, 2.0, 1.0):
        for lam_w in (2.0, 1.0):
            for grph_w in (1.0,):
                for k in (20, 30, 40, 60):
                    r = eval_electoral(rows, frz_z, lam_z, grph_z,
                                       frz_w, lam_w, grph_w, k, frozen_anchors)
                    obj = r["objective"]
                    if obj > best_obj:
                        best_obj    = obj
                        best_hits   = r["unique_hits"]
                        best_lost   = r["lost_frozen_hits"]
                        best_params = (frz_w, lam_w, grph_w, k)

    return best_params[0], best_params[1], best_params[2], best_params[3], \
           best_obj, best_hits, best_lost


# ── Grid search (residual) ─────────────────────────────────────────────────────

def search_residual_router(
    rows: list[dict],
    frz_z: list[float],
    lam_z: list[float],
    grph_z: list[float],
    frozen_anchors: set,
) -> tuple:
    """
    Grid search over (k_l, k_g) where k_f = TOP_N - k_l - k_g.
    Returns (k_l, k_g, best_obj, best_hits, best_lost).
    """
    frz_pct  = rank_pct(frz_z)
    lam_pct  = rank_pct(lam_z)
    grph_pct = rank_pct(grph_z)

    best_obj   = -1e9
    best_hits  = 0
    best_lost  = 0
    best_kl    = 0
    best_kg    = 0

    for k_l in range(0, 7):
        for k_g in range(0, 7):
            if k_l + k_g > 6:
                continue
            k_f = TOP_N - k_l - k_g
            if k_f < 14:
                continue
            result = three_phase_select(rows, frz_pct, lam_pct, grph_pct, k_l, k_g)
            hits = result["unique_hits"]
            hit_set = result["covered_anchors"]
            lost = len(frozen_anchors - hit_set)
            obj  = router_objective(hits, lost)
            if obj > best_obj:
                best_obj  = obj
                best_hits = hits
                best_lost = lost
                best_kl   = k_l
                best_kg   = k_g

    return best_kl, best_kg, best_obj, best_hits, best_lost


# ── Evaluation helper ──────────────────────────────────────────────────────────

def eval_residual_router(
    label: str,
    rows: list[dict],
    spec: GateSpec,
    k_l: int,
    k_g: int,
    frozen_anchors: set,
) -> dict:
    frz_r, lam_r, grph_r = compute_lane_scores(rows, spec)
    frz_z  = z_norm(frz_r)
    lam_z  = z_norm(lam_r)
    grph_z = z_norm(grph_r)
    frz_pct  = rank_pct(frz_z)
    lam_pct  = rank_pct(lam_z)
    grph_pct = rank_pct(grph_z)

    result = three_phase_select(rows, frz_pct, lam_pct, grph_pct, k_l, k_g)
    hits    = result["unique_hits"]
    hit_set = result["covered_anchors"]
    lost    = len(frozen_anchors - hit_set)
    new     = sorted(hit_set - frozen_anchors)
    lost_a  = sorted(frozen_anchors - hit_set)

    # Unique anchors total (denominator)
    _, unique_total = frozen_anchor_set(rows, spec)

    return {
        "label": label,
        "unique_hits": hits,
        "unique_total": unique_total,
        "delta_frozen": hits - len(frozen_anchors),
        "lost_frozen_hits": lost,
        "objective": router_objective(hits, lost),
        "new_anchors": new,
        "lost_anchors": lost_a,
        "lane_counts": result["lane_counts"],
    }


# ── Frozen-spec loader ─────────────────────────────────────────────────────────

def _load_frozen_spec() -> GateSpec:
    p = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    if not p.exists():
        raise FileNotFoundError(f"Run bench first: {p}")
    return GateSpec(**json.loads(p.read_text())["frozen_spec"])


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ensure_dynamic_profiles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    spec = _load_frozen_spec()
    print(f"Frozen spec: {spec.spec_id}")

    print("Loading row caches...", flush=True)
    rows_100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_200 = build_or_load_rows(200_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_250 = build_or_load_rows(250_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    rows_300 = build_or_load_rows(300_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    range_a = fresh_rows(rows_100, rows_150)
    range_b = fresh_rows(rows_150, rows_200)
    range_c = fresh_rows(rows_200, rows_250)
    range_d = fresh_rows(rows_250, rows_300)
    print(f"range_a={len(range_a)}  range_b={len(range_b)}  range_c={len(range_c)}  range_d={len(range_d)}")

    fit_a, holdout_a = split_ordered_rows(range_a, FIT_FRACTION)

    # Frozen baselines
    b_frz_set, b_total = frozen_anchor_set(range_b, spec)
    c_frz_set, c_total = frozen_anchor_set(range_c, spec)
    d_frz_set, d_total = frozen_anchor_set(range_d, spec)
    ho_frz_set, ho_total = frozen_anchor_set(holdout_a, spec)
    print(f"Frozen: B={len(b_frz_set)}/{b_total}  C={len(c_frz_set)}/{c_total}  "
          f"D={len(d_frz_set)}/{d_total}  holdout={len(ho_frz_set)}/{ho_total}")

    # Oracle lane coverage diagnostic on range_a
    print("\nOracle lane coverage (range_a)...", flush=True)
    cov_a = oracle_lane_coverage(range_a, spec)
    print(f"  frozen={len(cov_a['frozen_hits'])}  lambda={len(cov_a['lambda_hits'])}  "
          f"graph={len(cov_a['graph_hits'])}  union={cov_a['union_size']}  "
          f"3way={cov_a['triple_intersect']}")
    print(f"  lambda_unique={cov_a['lambda_unique']}")
    print(f"  graph_unique={cov_a['graph_unique']}")

    # Lane z-scores computed independently per evaluation set.
    # score_frozen is context-dependent (batch context changes per-row scores), so
    # we MUST call compute_lane_scores directly on each evaluation subset.
    print("\nComputing lane z-scores for holdout_a...", flush=True)
    frz_ho_raw, lam_ho_raw, grph_ho_raw = compute_lane_scores(holdout_a, spec)
    frz_ho_z  = z_norm(frz_ho_raw)
    lam_ho_z  = z_norm(lam_ho_raw)
    grph_ho_z = z_norm(grph_ho_raw)

    frz_ho_pct  = rank_pct(frz_ho_z)
    lam_ho_pct  = rank_pct(lam_ho_z)
    grph_ho_pct = rank_pct(grph_ho_z)
    anchor_rows = [r for r in holdout_a if r.get("future_anchor")]
    print(f"\nholdout_a: {len(holdout_a)} rows, {len(anchor_rows)} anchor rows, "
          f"{len(ho_frz_set)} unique primes (frozen baseline)")

    # Verify k_l=0, k_g=0 matches frozen baseline
    chk = three_phase_select(holdout_a, frz_ho_pct, lam_ho_pct, grph_ho_pct, 0, 0)
    print(f"  verify (k_l=0, k_g=0): {chk['unique_hits']}/{ho_total} "
          f"  (should match frozen={len(ho_frz_set)})")

    # Grid search on holdout_a
    print("\nGrid-searching residual router on holdout_a...", flush=True)
    k_l, k_g, best_obj, ho_hits, ho_lost = search_residual_router(
        holdout_a, frz_ho_z, lam_ho_z, grph_ho_z, ho_frz_set,
    )
    k_f = TOP_N - k_l - k_g
    print(f"  k_frozen={k_f}  k_lambda={k_l}  k_graph={k_g}")
    print(f"  holdout: hits={ho_hits}/{ho_total}  lost_frozen={ho_lost}  obj={best_obj:.1f}")

    # ── Electoral scoring experiment ──────────────────────────────────────────
    print("\nGrid-searching electoral router on holdout_a...", flush=True)
    el_frz_w, el_lam_w, el_grph_w, el_k, el_obj, el_ho_hits, el_ho_lost = search_electoral(
        holdout_a, frz_ho_z, lam_ho_z, grph_ho_z, ho_frz_set,
    )
    print(f"  frz_weight={el_frz_w}  lam_weight={el_lam_w}  grph_weight={el_grph_w}  "
          f"nominate_k={el_k}")
    print(f"  holdout: hits={el_ho_hits}/{ho_total}  lost_frozen={el_ho_lost}  obj={el_obj:.1f}")

    # Blind evaluation of electoral on B, C, D
    def _el_eval(label, rows_x, frz_set):
        frz_r, lam_r, grph_r = compute_lane_scores(rows_x, spec)
        fz = z_norm(frz_r); lz = z_norm(lam_r); gz = z_norm(grph_r)
        return eval_electoral(rows_x, fz, lz, gz, el_frz_w, el_lam_w, el_grph_w, el_k, frz_set)

    el_b = _el_eval("B", range_b, b_frz_set)
    el_c = _el_eval("C", range_c, c_frz_set)
    el_d = _el_eval("D", range_d, d_frz_set)

    # Blind evaluation on B, C, D
    print("\nEvaluating residual router on range_b, range_c, range_d...", flush=True)
    r_b = eval_residual_router("B", range_b, spec, k_l, k_g, b_frz_set)
    r_c = eval_residual_router("C", range_c, spec, k_l, k_g, c_frz_set)
    r_d = eval_residual_router("D", range_d, spec, k_l, k_g, d_frz_set)

    # Save artifact
    def _r(d):
        return {k: d[k] for k in ("unique_hits", "unique_total", "delta_frozen",
                                   "lost_frozen_hits", "objective", "new_anchors", "lost_anchors")}
    artifact = {
        "schema": "map_reader_router_v2_residual",
        "routing": {"k_frozen": k_f, "k_lambda": k_l, "k_graph": k_g},
        "electoral": {"frz_weight": el_frz_w, "lam_weight": el_lam_w,
                      "grph_weight": el_grph_w, "nominate_k": el_k},
        "objective": "unique_hits - 2.0 * lost_frozen_hits",
        "calibrated_on": "holdout_a (100M-150M, last 40%)",
        "oracle_coverage_a": cov_a,
        "results": {
            "holdout_a": {
                "unique_hits": ho_hits, "unique_total": ho_total,
                "delta_frozen": ho_hits - len(ho_frz_set),
                "lost_frozen_hits": ho_lost, "objective": best_obj,
            },
            "range_b": _r(r_b), "range_c": _r(r_c), "range_d": _r(r_d),
        },
        "electoral_results": {
            "holdout_a": {
                "unique_hits": el_ho_hits, "unique_total": ho_total,
                "delta_frozen": el_ho_hits - len(ho_frz_set),
                "lost_frozen_hits": el_ho_lost, "objective": el_obj,
            },
            "range_b": _r(el_b), "range_c": _r(el_c), "range_d": _r(el_d),
        },
    }
    out_path = OUT_DIR / "router_v2.json"
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {out_path}")

    # Summary table
    print("\n" + "=" * 90)
    print(f"MAP READER ROUTER v2 — Three-Phase Residual  (k_f={k_f}  k_l={k_l}  k_g={k_g})")
    print("=" * 90)
    print(f"{'Gate':<46}  {'holdout':>9}  {'B':>8}  {'C':>8}  {'D':>8}")
    print("-" * 90)
    print(f"  {'frozen_gate (baseline)':<44}  {len(ho_frz_set)}/{ho_total}  "
          f"{len(b_frz_set)}/{b_total}  {len(c_frz_set)}/{c_total}  {len(d_frz_set)}/{d_total}")
    print(f"  {'router_v2_residual':<44}  {ho_hits}/{ho_total}  "
          f"{r_b['unique_hits']}/{r_b['unique_total']}  "
          f"{r_c['unique_hits']}/{r_c['unique_total']}  "
          f"{r_d['unique_hits']}/{r_d['unique_total']}")
    el_label = f"electoral (f={el_frz_w:.0f}/l={el_lam_w:.0f}/g={el_grph_w:.0f} k={el_k})"
    print(f"  {el_label:<44}  {el_ho_hits}/{ho_total}  "
          f"{el_b['unique_hits']}/{el_b['unique_total']}  "
          f"{el_c['unique_hits']}/{el_c['unique_total']}  "
          f"{el_d['unique_hits']}/{el_d['unique_total']}")
    print()
    print(f"  delta_frozen [residual]:  holdout={ho_hits-len(ho_frz_set):+d}  "
          f"B={r_b['delta_frozen']:+d}  C={r_c['delta_frozen']:+d}  D={r_d['delta_frozen']:+d}")
    print(f"  delta_frozen [electoral]: holdout={el_ho_hits-len(ho_frz_set):+d}  "
          f"B={el_b['delta_frozen']:+d}  C={el_c['delta_frozen']:+d}  D={el_d['delta_frozen']:+d}")
    print(f"  lost_frozen  [electoral]: holdout={el_ho_lost}  B={el_b['lost_frozen_hits']}  "
          f"C={el_c['lost_frozen_hits']}  D={el_d['lost_frozen_hits']}")
    print()
    print(f"  Electoral B new: {el_b['new_anchors']}  lost: {el_b['lost_anchors']}")
    print(f"  Electoral C new: {el_c['new_anchors']}  lost: {el_c['lost_anchors']}")
    print(f"  Electoral D new: {el_d['new_anchors']}  lost: {el_d['lost_anchors']}")
    print()
    print("Reference: tree_d2_a w=0.5  B=12/227 (+1)  C=10/256 (+4)  D=6/220 (-1)")
    print("Reference: fog_router_v1    B=9/227  (-2)  C=8/256  (+2)  D=6/220 (-1)")
    print("Reference: gate_v1          B=12/227 (+1)  C=6/256  (+0)  D=—")


if __name__ == "__main__":
    main()
