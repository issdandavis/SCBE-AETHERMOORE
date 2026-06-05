"""Sweep the saddle-asymmetry threshold that controls the frozen gate fallback.

Rows are already cached with topo_asymmetry, gravity_score_normalized, and the
per-channel values needed to compute the gate.  This script re-scores the B range
(150M→200M) using a parametric fallback:

    fallback = topo_weight * topo_score(threshold) + grav_weight * gravity

where topo_score is re-derived from the stored topo_asymmetry:

    if asym >= threshold:
        saddle_score = 0.5 + 0.5 * asym       # 0.7 .. 1.0 range
    else:
        saddle_score = asym * (threshold - asym) / threshold   # decaying ramp

The sweep grid covers saddle_threshold x topo_weight.  For each combination it
reports the frozen gate hit count on top-20 B-range candidates.
"""

from __future__ import annotations

import json
import math
import sys
from itertools import product
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    row_cache_path,
)
from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    ensure_dynamic_profiles,
    profile_score,
)

# ── frozen gate spec ──────────────────────────────────────────────────────────
FROZEN_SPEC = GateSpec(
    spec_id="igct_c4_g5_c0.65_g0.05-0.6_geo0.25_cas0_ch0_fb0_bb0",
    base_profile="igct_c4_g5",
    cold_min=0.65,
    grad_min=0.05,
    grad_max=0.60,
    geo_min=0.25,
    cassette_min=0.0,
    charge_min=0.0,
    fallback_scale=0.0,
    branch_bonus=0.0,
)

TOP_N = 20
WINDOW = 36
HISTORY = 12
ANCHOR_THRESHOLD = 4.0

# ── sweep grid ────────────────────────────────────────────────────────────────
SADDLE_THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]
TOPO_WEIGHTS = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
# also sweep the "gate-miss full replace" blend: use ONLY saddle type (grav weight=0)


def indicator(cond: bool) -> float:
    return 1.0 if cond else 0.0


def gate_value(row: dict[str, Any], spec: GateSpec) -> float:
    cold = float(row.get("cold_spot_channel", 0.0))
    grad = float(row.get("gradient_abs_channel", 0.0))
    geo = float(row.get("geodesic_trend_channel", 0.0))
    cas = float(row.get("cassette_channel", 0.0))
    ch = float(row.get("charge_flip_channel", 0.0))
    return (
        indicator(cold >= spec.cold_min)
        * indicator(spec.grad_min <= grad <= spec.grad_max)
        * indicator(geo >= spec.geo_min)
        * indicator(cas >= spec.cassette_min)
        * indicator(ch >= spec.charge_min)
    )


def branch_term(row: dict[str, Any], spec: GateSpec) -> float:
    base = profile_score(row, spec.base_profile)
    cold = float(row.get("cold_spot_channel", 0.0))
    grad = float(row.get("gradient_abs_channel", 0.0))
    geo = float(row.get("geodesic_trend_channel", 0.0))
    cas = float(row.get("cassette_channel", 0.0))
    ch = float(row.get("charge_flip_channel", 0.0))
    return base + spec.branch_bonus * (1.5 * cold + 1.0 * grad + 0.75 * cas + 0.5 * ch + max(0.0, geo))


def parametric_topo_score(row: dict[str, Any], saddle_threshold: float) -> float:
    """Re-derive topo_score from raw topo_asymmetry at a given threshold."""
    asym = float(row.get("topo_asymmetry", 0.0))
    if asym >= saddle_threshold:
        # saddle: score in [0.5 + 0.5*threshold .. 1.0]
        return 0.5 + 0.5 * asym
    else:
        # sub-threshold: linear ramp down from saddle boundary to 0
        return asym / max(1e-9, saddle_threshold) * (0.5 + 0.5 * saddle_threshold) * (asym / max(1e-9, saddle_threshold))


def score_row(row: dict[str, Any], spec: GateSpec, saddle_threshold: float, topo_weight: float) -> float:
    gate = gate_value(row, spec)
    branch = branch_term(row, spec)
    if gate > 0.0:
        return gate * branch + (1.0 - gate) * spec.fallback_scale * branch
    # gate == 0: use parametric fallback
    ts = parametric_topo_score(row, saddle_threshold)
    grav = float(row.get("gravity_score_normalized", 0.0))
    grav_w = 1.0 - topo_weight
    return topo_weight * ts + grav_w * grav


def score_rows(
    rows: list[dict[str, Any]],
    spec: GateSpec,
    saddle_threshold: float,
    topo_weight: float,
) -> int:
    scored = [(score_row(r, spec, saddle_threshold, topo_weight), r) for r in rows]
    scored.sort(key=lambda t: (-t[0], id(t[1])))
    top = scored[:TOP_N]
    return sum(1 for _, r in top if r.get("future_anchor"))


def load_rows(cache_dir: Path, limit: int) -> list[dict[str, Any]]:
    path = row_cache_path(cache_dir, limit, WINDOW, HISTORY, ANCHOR_THRESHOLD)
    if not path.exists():
        raise FileNotFoundError(f"Row cache missing: {path}\nRun the benchmark first to build it.")
    with path.open() as f:
        return json.load(f)


def main() -> None:
    ensure_dynamic_profiles()
    cache_dir = DEFAULT_ROW_CACHE_DIR

    # Load all rows and split into ranges
    rows_150m = load_rows(cache_dir, 150_000_000)
    rows_200m = load_rows(cache_dir, 200_000_000)

    # B range: rows from 150M boundary scan that are beyond 150M
    # The bench uses fresh_rows(rows_200m, boundary=150M) for range B.
    # In the cache, rows_200m contains rows up to 200M; rows_150m up to 150M.
    # Range B = rows in rows_200m with scan_prime > max(rows_150m scan primes)
    max_150m_prime = max(r["scan_prime"] for r in rows_150m)
    b_rows = [r for r in rows_200m if r["scan_prime"] > max_150m_prime]
    positives = sum(1 for r in b_rows if r.get("future_anchor"))
    print(f"B rows: {len(b_rows):,}  positives: {positives}  baseline: {positives / len(b_rows):.4f}")
    print(f"{'threshold':>10}  {'topo_w':>7}  {'hits':>5}  {'rate':>7}  {'vs_base':>8}")
    print("-" * 50)

    results: list[tuple[float, float, int]] = []
    for saddle_threshold, topo_weight in product(SADDLE_THRESHOLDS, TOPO_WEIGHTS):
        hits = score_rows(b_rows, FROZEN_SPEC, saddle_threshold, topo_weight)
        results.append((saddle_threshold, topo_weight, hits))

    # Sort by hits descending, then threshold ascending
    results.sort(key=lambda t: (-t[2], t[0]))

    best_hits = results[0][2]
    for saddle_threshold, topo_weight, hits in results:
        rate = hits / TOP_N
        base_rate = min(positives, TOP_N) / TOP_N
        marker = " ◄ best" if hits == best_hits else ""
        print(f"{saddle_threshold:>10.2f}  {topo_weight:>7.2f}  {hits:>5d}  {rate:>7.1%}  {hits - round(base_rate * TOP_N):>+8d}{marker}")

    print()
    # Print compact grid: threshold rows, topo_weight columns
    tw_list = TOPO_WEIGHTS
    print("Grid (rows=threshold, cols=topo_weight):")
    header = f"{'thresh':>8}" + "".join(f"  tw={w:.2f}" for w in tw_list)
    print(header)
    grid: dict[float, dict[float, int]] = {}
    for st, tw, h in results:
        grid.setdefault(st, {})[tw] = h
    for st in SADDLE_THRESHOLDS:
        row_str = f"{st:>8.2f}"
        for tw in tw_list:
            h = grid.get(st, {}).get(tw, -1)
            row_str += f"  {'*' if h == best_hits else ' '}{h:>6}"
        print(row_str)


if __name__ == "__main__":
    main()
