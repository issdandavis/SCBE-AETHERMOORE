"""Prime alignment ledger — truth-aligned substrate for the prime-fog program.

This is NOT a solver and NOT a search router. It is the null-safe substrate the
router work should have rested on:

  known answer -> exact truth ledger -> relationship graph -> AXIS GATE -> (only
  then) candidate search lane.

Two halves, with very different epistemic status:

1. LEDGER (null-safe facts). For each known anchor across rings we record exact,
   looked-up truth via ``prime_truth_oracle`` -- prime value, gaps to the
   neighbouring primes, gap ratios/derivatives, log scale, small-prime residue
   vector, and (optionally) the exact prime index pi(p) and its primality. You
   cannot overfit a lookup table of true values, so this half is always safe to
   trust and to build on.

2. AXIS GATE (the discipline, baked in at the API). A candidate transformation
   does not get to be a "search lane" just because it aligns to the known values
   in-sample -- that is the exact overfit that killed the IP lane, the RR lane,
   the joint router, and the K/L/M/N "regime flip" (see
   ``notes/prime-fog/solutions/null floor metric audit.md``). Before any axis is
   believed, it must answer the three questions, all measured through the
   surviving NMS count-proxy with a proper ``random.shuffle`` null:

     (a) better than random?      precision_real > precision_null_p95
     (b) aligns across rings?     (a) holds on EVERY ring, one frozen config
     (c) identity, not count?     |count_error| <= COUNT_TOL * actual_anchors

   ``precision`` (unique anchor hits / predicted clusters) is the scatter-RESISTANT
   metric: NMS de-dups by scan-gap radius, and precision punishes false clusters,
   so you cannot win it by spraying. ``recall`` is NOT used as a gate -- it is
   scatter-INFLATED: a random shuffle that over-predicts (huge positive count
   error) hits many unique anchors by spray and posts recall ~0.86, far above a
   calibrated scorer's ~0.45. Gating on recall-vs-null is therefore backwards (it
   rewards the density trap); recall is reported for transparency only. The
   honest "identity AND count" pair is precision (right identities) + a count-
   error bound (right number, not won by over/under-predicting). Verified by the
   ``--gate-demo`` null-check: frozen clears precision+count on every ring; the
   already-falsified rr lane fails precision on 3/4 rings and blows the count
   bound on all 4.

   Freeze discipline: the gate evaluates a FROZEN score function. If your axis has
   tunable parameters, fit them on rings OUTSIDE the gate set -- the across-rings
   requirement (b) is what catches a per-ring-tuned axis (one frozen config will
   not clear every ring if it was secretly tuned per ring).

Demo (``--gate-demo``) runs the gate on ``frozen`` (expected PASS) and ``rr_sqrt1``
(expected FAIL). That is a null-check of the GATE itself: a gate that passed the
already-falsified rr lane would be broken.

Usage:
    python scripts/research/prime_alignment_ledger.py --rings K,L,M,N
    python scripts/research/prime_alignment_ledger.py --rings K,L,M,N --with-index
    python scripts/research/prime_alignment_ledger.py --gate-demo --rings K,L,M,N
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

try:
    from audit_prime_anchor_count_proxy import (
        PeakConfig,
        ScoreContext,
        actual_anchor_ids,
        anchor_id,
        evaluate_clusters,
    )
    from prime_truth_oracle import (
        is_prime_u64,
        next_prime_at_or_after,
        previous_prime_at_or_before,
        prime_indices_for_values,
    )
except ModuleNotFoundError:  # pragma: no cover - package import path for tests
    from scripts.research.audit_prime_anchor_count_proxy import (
        PeakConfig,
        ScoreContext,
        actual_anchor_ids,
        anchor_id,
        evaluate_clusters,
    )
    from scripts.research.prime_truth_oracle import (
        is_prime_u64,
        next_prime_at_or_after,
        previous_prime_at_or_before,
        prime_indices_for_values,
    )

# Small-prime residue vector recorded per anchor. These are FACTS about the
# integer; recording them never overfits. Whether any of them ALIGNS to anchor
# structure is a separate question the gate answers.
RESIDUE_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_GATE_AXES = (
    "frozen,rr_sqrt1,log_power_bridge,golden_spiral_phase,gap_acceleration,"
    "ratio_curvature,ratio_graph_resonance,residue_wheel_frequency,"
    "numerical_emulsion,prime_circuit_geometry"
)
DEFAULT_PERCENTILE_GRID = tuple(
    round(0.50 + (index * 0.005), 3) for index in range(100)
)

# A single frozen gate config. Mid-percentile + the established radius; the point
# is to FREEZE one config and require it to clear the null on every ring, not to
# sweep configs and crown a per-ring winner (that sweep is the overfit).
GATE_CONFIG = PeakConfig("gate", 0.85, 12)
DEFAULT_GATE_SEEDS = 120
# Count-honesty bound: predicted cluster count must be within COUNT_TOL of the true
# anchor count. Stops an axis from "winning" precision by over/under-predicting.
COUNT_TOL = 0.30


@dataclass(frozen=True)
class AnchorRecord:
    """Exact, looked-up truth for one known anchor. Null-safe by construction."""

    ring: str
    anchor_id: str
    anchor_prime: int | None
    anchor_idx: int | None
    is_prime: bool | None
    prev_prime: int | None
    next_prime: int | None
    gap_before: int | None
    gap_after: int | None
    gap_ratio: float | None
    log_value: float | None
    residues: dict[str, int]
    # Optional (requires a full segmented count to max anchor): exact prime index.
    prime_index: int | None = None
    index_is_prime: bool | None = None
    is_superprime: bool | None = None


def _anchor_value(row: dict[str, Any]) -> int | None:
    """Best exact integer for an anchor row: the anchor prime if present, else its scan prime."""
    value = row.get("first_anchor_prime")
    if isinstance(value, int):
        return value
    scan = row.get("scan_prime")
    return int(scan) if scan is not None else None


def _representative_rows(rows: list[dict[str, Any]]) -> dict[object, dict[str, Any]]:
    """One representative row per unique anchor id (first anchor-bearing row seen)."""
    reps: dict[object, dict[str, Any]] = {}
    for row in rows:
        if not row.get("future_anchor"):
            continue
        aid = anchor_id(row)
        if aid is None or aid in reps:
            continue
        reps[aid] = row
    return reps


def build_anchor_records(
    ring: str,
    rows: list[dict[str, Any]],
    prime_index_lookup: dict[int, int] | None = None,
) -> list[AnchorRecord]:
    """Exact truth ledger for every known anchor in one ring. Pure lookup -- never overfits."""
    records: list[AnchorRecord] = []
    for aid, row in sorted(
        _representative_rows(rows).items(), key=lambda kv: str(kv[0])
    ):
        value = _anchor_value(row)
        if value is None:
            continue
        is_prime = is_prime_u64(value)
        prev_p = previous_prime_at_or_before(value - 1) if value > 2 else None
        next_p = next_prime_at_or_after(value + 1)
        gap_before = value - prev_p if prev_p is not None else None
        gap_after = next_p - value if next_p is not None else None
        gap_ratio = (gap_after / gap_before) if (gap_before and gap_after) else None
        residues = {f"mod{p}": value % p for p in RESIDUE_PRIMES}

        prime_index = None
        index_is_prime = None
        is_superprime = None
        if prime_index_lookup is not None and is_prime:
            prime_index = prime_index_lookup.get(value)
            if prime_index is not None:
                index_is_prime = is_prime_u64(prime_index)
                is_superprime = bool(is_prime and index_is_prime)

        records.append(
            AnchorRecord(
                ring=ring,
                anchor_id=str(aid),
                anchor_prime=value if is_prime else None,
                anchor_idx=row.get("first_anchor_idx"),
                is_prime=is_prime,
                prev_prime=prev_p,
                next_prime=next_p,
                gap_before=gap_before,
                gap_after=gap_after,
                gap_ratio=round(gap_ratio, 6) if gap_ratio is not None else None,
                log_value=round(math.log(value), 6) if value > 0 else None,
                residues=residues,
                prime_index=prime_index,
                index_is_prime=index_is_prime,
                is_superprime=is_superprime,
            )
        )
    return records


def relationship_edges(records: list[AnchorRecord]) -> list[dict[str, Any]]:
    """Edges between consecutive known anchors: gap-of-gaps and ratio transitions. Facts, not fits."""
    ordered = sorted(
        (r for r in records if r.anchor_prime is not None),
        key=lambda r: r.anchor_prime,  # type: ignore[arg-type,return-value]
    )
    edges: list[dict[str, Any]] = []
    for prev, cur in zip(ordered, ordered[1:]):
        assert prev.anchor_prime is not None and cur.anchor_prime is not None
        span = cur.anchor_prime - prev.anchor_prime
        gap_delta = None
        if prev.gap_after is not None and cur.gap_after is not None:
            gap_delta = cur.gap_after - prev.gap_after
        edges.append(
            {
                "from": prev.anchor_id,
                "to": cur.anchor_id,
                "value_span": span,
                "log_span": round(math.log(span), 6) if span > 0 else None,
                "gap_delta": gap_delta,
            }
        )
    return edges


# --------------------------------------------------------------------------- #
# Axis gate -- the discipline, baked in.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RingGateResult:
    ring: str
    precision_real: float
    recall_real: float  # reported only; scatter-inflated, NOT a gate
    precision_null_p95: float
    recall_null_p95: float  # reported only
    count_error: int
    actual_anchors: int
    passes_precision: bool
    passes_count: bool

    @property
    def passes(self) -> bool:
        return self.passes_precision and self.passes_count


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(q * len(sorted_vals)))
    return sorted_vals[idx]


def gate_axis_on_ring(
    rows: list[dict[str, Any]],
    scores: list[float],
    config: PeakConfig = GATE_CONFIG,
    seeds: int = DEFAULT_GATE_SEEDS,
) -> RingGateResult:
    """Run the three-question gate on one ring with a proper random.shuffle null."""
    ring_label = str(rows[0].get("ring", "?")) if rows else "?"
    real = evaluate_clusters(rows, scores, config)
    actual = real["actual_unique_anchors"]

    prec_null: list[float] = []
    rec_null: list[float] = []
    for seed in range(seeds):
        shuffled = list(scores)
        random.Random(seed).shuffle(shuffled)  # proper permutation -- never (i*M)%n
        ev = evaluate_clusters(rows, shuffled, config)
        prec_null.append(ev["precision"])
        rec_null.append(ev["recall"])
    prec_null.sort()
    rec_null.sort()
    prec_p95 = _percentile(prec_null, 0.95)
    rec_p95 = _percentile(rec_null, 0.95)

    count_ok = abs(real["count_error"]) <= COUNT_TOL * actual if actual else False
    return RingGateResult(
        ring=ring_label,
        precision_real=real["precision"],
        recall_real=real["recall"],
        precision_null_p95=prec_p95,
        recall_null_p95=rec_p95,
        count_error=real["count_error"],
        actual_anchors=actual,
        passes_precision=real["precision"] > prec_p95,
        passes_count=count_ok,
    )


def gate_axis(
    ctx: ScoreContext,
    score_fn: Callable[[list[dict[str, Any]]], list[float]],
    rings: list[str],
    ring_rows: dict[str, list[dict[str, Any]]],
    config: PeakConfig = GATE_CONFIG,
    seeds: int = DEFAULT_GATE_SEEDS,
) -> dict[str, Any]:
    """Gate a FROZEN candidate axis across rings. PASS only if it clears the null on EVERY ring.

    score_fn maps a ring's rows -> per-row scores. It must be frozen (no tuning on
    the gate rings); the across-rings requirement is what catches per-ring overfit.
    """
    per_ring: list[RingGateResult] = []
    for ring in rings:
        rows = ring_rows[ring]
        scores = score_fn(rows)
        result = gate_axis_on_ring(rows, scores, config, seeds)
        # gate_axis_on_ring can't see the ring name from rows reliably; stamp it.
        per_ring.append(
            RingGateResult(
                ring=ring,
                precision_real=result.precision_real,
                recall_real=result.recall_real,
                precision_null_p95=result.precision_null_p95,
                recall_null_p95=result.recall_null_p95,
                count_error=result.count_error,
                actual_anchors=result.actual_anchors,
                passes_precision=result.passes_precision,
                passes_count=result.passes_count,
            )
        )
    overall = all(r.passes for r in per_ring)
    return {
        "config_id": config.config_id,
        "seeds": seeds,
        "rings": rings,
        "passes": overall,
        "verdict": (
            "SEARCH-LANE ELIGIBLE"
            if overall
            else "REJECTED (does not clear null on every ring)"
        ),
        "per_ring": [asdict(r) for r in per_ring],
    }


def fit_count_honest_config(
    rows: list[dict[str, Any]],
    scores: list[float],
    axis_name: str,
    radius: int = GATE_CONFIG.radius,
    percentile_grid: tuple[float, ...] = DEFAULT_PERCENTILE_GRID,
) -> dict[str, Any]:
    """Pick one frozen percentile on the freeze ring by count honesty only.

    The fitting target is the number of NMS clusters, not anchor identities.
    Precision is only a tie-breaker, so this does not tune to hit locations.
    """
    candidates: list[dict[str, Any]] = []
    for percentile in percentile_grid:
        config = PeakConfig(axis_name, percentile, radius)
        ev = evaluate_clusters(rows, scores, config)
        candidates.append(ev)
    best = min(
        candidates,
        key=lambda item: (
            item["abs_count_error"],
            -item["precision"],
            item["false_clusters"] + item["duplicate_clusters"],
            item["percentile"],
        ),
    )
    return best


def count_honest_axis_probe(
    ctx: ScoreContext,
    axis_name: str,
    freeze_ring: str,
    test_rings: list[str],
    ring_rows: dict[str, list[dict[str, Any]]],
    seeds: int = DEFAULT_GATE_SEEDS,
    radius: int = GATE_CONFIG.radius,
) -> dict[str, Any]:
    """Freeze a count-honest cutoff on one ring, then null-test on the rest."""
    score_fn = axis_score_fn(ctx, axis_name)
    freeze_rows = ring_rows[freeze_ring]
    freeze_scores = score_fn(freeze_rows)
    fit = fit_count_honest_config(freeze_rows, freeze_scores, axis_name, radius=radius)
    frozen_config = PeakConfig(axis_name, float(fit["percentile"]), radius)

    per_ring: list[dict[str, Any]] = []
    for ring in test_rings:
        rows = ring_rows[ring]
        scores = score_fn(rows)
        gate = gate_axis_on_ring(rows, scores, frozen_config, seeds)
        real = evaluate_clusters(rows, scores, frozen_config)
        per_ring.append(
            {
                "ring": ring,
                "predicted_clusters": real["predicted_clusters"],
                "unique_anchor_hits": real["unique_anchor_hits"],
                "precision_real": gate.precision_real,
                "precision_null_p95": gate.precision_null_p95,
                "count_error": gate.count_error,
                "actual_anchors": gate.actual_anchors,
                "passes_precision": gate.passes_precision,
                "passes_count": gate.passes_count,
            }
        )

    passes = all(item["passes_precision"] and item["passes_count"] for item in per_ring)
    return {
        "axis": axis_name,
        "freeze_ring": freeze_ring,
        "test_rings": test_rings,
        "seeds": seeds,
        "frozen_config": frozen_config.config_id,
        "fit_on_freeze_ring": fit,
        "passes": passes,
        "verdict": (
            "SEARCH-LANE ELIGIBLE"
            if passes
            else "REJECTED (count-honest frozen cutoff did not transfer)"
        ),
        "per_ring": per_ring,
    }


def _frozen_scores(ctx: ScoreContext) -> Callable[[list[dict[str, Any]]], list[float]]:
    return lambda rows: ctx.scores_for(rows)["frozen"]


def _rr_scores(ctx: ScoreContext) -> Callable[[list[dict[str, Any]]], list[float]]:
    return lambda rows: ctx.scores_for(rows)["rr_sqrt1"]


def _scan_prime(row: dict[str, Any]) -> int:
    return int(row.get("scan_prime") or 0)


def _unit_phase(value: float) -> float:
    return value - math.floor(value)


def _unit_circle_distance(phase: float, targets: tuple[float, ...]) -> float:
    phase = _unit_phase(phase)
    return min(
        min(abs(phase - target), 1.0 - abs(phase - target)) for target in targets
    )


def log_power_bridge_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Scale bridge: closeness to integer bands of log_3(n) or log_4(n).

    This is the user's "count * log(3) / log(4)" lookup-chart idea made into a
    frozen axis. It deliberately does not fit anchor locations.
    """
    scores: list[float] = []
    for row in rows:
        n = _scan_prime(row)
        if n <= 1:
            scores.append(0.0)
            continue
        log_n = math.log(n)
        dist = min(
            _unit_circle_distance(log_n / math.log(3.0), (0.0,)),
            _unit_circle_distance(log_n / math.log(4.0), (0.0,)),
        )
        scores.append(max(0.0, 1.0 - (2.0 * dist)))
    return scores


def golden_spiral_phase_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Golden-log spiral phase: prime-log notches on a Fibonacci-style shell."""
    notches = tuple(
        _unit_phase(math.log(prime) / math.log(PHI)) for prime in RESIDUE_PRIMES[1:]
    )
    scores: list[float] = []
    for row in rows:
        n = _scan_prime(row)
        if n <= 1:
            scores.append(0.0)
            continue
        phase = math.log(n) / math.log(PHI)
        dist = _unit_circle_distance(phase, notches)
        scores.append(max(0.0, 1.0 - (2.0 * dist)))
    return scores


def gap_acceleration_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Local second difference of scan_ratio, returned in original row order."""
    scores = [0.0 for _row in rows]
    if len(rows) < 3:
        return scores
    ordered = sorted(
        enumerate(rows), key=lambda item: int(item[1].get("scan_idx") or 0)
    )
    ratios = [float(row.get("scan_ratio") or 0.0) for _index, row in ordered]
    for position in range(1, len(ordered) - 1):
        original_index = ordered[position][0]
        scores[original_index] = abs(
            ratios[position + 1] - (2.0 * ratios[position]) + ratios[position - 1]
        )
    return scores


def _ordered_scan_primes(rows: list[dict[str, Any]]) -> list[tuple[int, int]]:
    ordered: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        value = _scan_prime(row)
        if value > 0:
            ordered.append((index, value))
    return sorted(ordered, key=lambda item: int(rows[item[0]].get("scan_idx") or 0))


def ratio_curvature_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Ratio-of-ratios bend: abs(log(p[i+1]/p[i]) - log(p[i]/p[i-1]))."""
    scores = [0.0 for _row in rows]
    ordered = _ordered_scan_primes(rows)
    if len(ordered) < 3:
        return scores
    values = [value for _index, value in ordered]
    for position in range(1, len(ordered) - 1):
        original_index = ordered[position][0]
        left = math.log(values[position] / values[position - 1])
        right = math.log(values[position + 1] / values[position])
        scores[original_index] = abs(right - left)
    return scores


def ratio_graph_resonance_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Transition-space recurrence: higher when a prime-pair log-ratio repeats."""
    scores = [-math.inf for _row in rows]
    ordered = _ordered_scan_primes(rows)
    if len(ordered) < 2:
        return scores

    edges: list[tuple[float, int, int]] = []
    for position in range(len(ordered) - 1):
        left_index, left_value = ordered[position]
        right_index, right_value = ordered[position + 1]
        edges.append((math.log(right_value / left_value), left_index, right_index))

    if len(edges) == 1:
        _weight, left_index, right_index = edges[0]
        scores[left_index] = 0.0
        scores[right_index] = 0.0
        return scores

    sorted_edges = sorted(enumerate(edges), key=lambda item: item[1][0])
    edge_scores = [0.0 for _edge in edges]
    for sorted_index, (edge_index, (weight, _left, _right)) in enumerate(sorted_edges):
        distances: list[float] = []
        if sorted_index > 0:
            distances.append(abs(weight - sorted_edges[sorted_index - 1][1][0]))
        if sorted_index + 1 < len(sorted_edges):
            distances.append(abs(weight - sorted_edges[sorted_index + 1][1][0]))
        edge_scores[edge_index] = -min(distances)

    for edge_index, (_weight, left_index, right_index) in enumerate(edges):
        score = edge_scores[edge_index]
        scores[left_index] = max(scores[left_index], score)
        scores[right_index] = max(scores[right_index], score)
    return scores


def _wheel_point(value: int, modulus: int = 210) -> tuple[float, float]:
    """Fold an integer onto a residue wheel and use log(value) as radius."""
    radius = math.log(max(2, value))
    angle = (2.0 * math.pi * (value % modulus)) / modulus
    return radius * math.cos(angle), radius * math.sin(angle)


def prime_circuit_geometry_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Local bend on the prime residue circuit.

    This is the circle-of-fifths analogue: fold each visible scan prime by its
    residue on the 210 wheel, use log(p) as the ring radius, then score the
    local turn through previous/current/next scan primes. High values mean the
    path bends sharply or changes radial step size in this folded circuit.
    """
    scores = [0.0 for _row in rows]
    ordered = _ordered_scan_primes(rows)
    if len(ordered) < 3:
        return scores

    points = [_wheel_point(value) for _index, value in ordered]
    for position in range(1, len(ordered) - 1):
        original_index = ordered[position][0]
        prev_x, prev_y = points[position - 1]
        cur_x, cur_y = points[position]
        next_x, next_y = points[position + 1]

        left_x = cur_x - prev_x
        left_y = cur_y - prev_y
        right_x = next_x - cur_x
        right_y = next_y - cur_y
        left_norm = math.hypot(left_x, left_y)
        right_norm = math.hypot(right_x, right_y)
        if left_norm <= 0.0 or right_norm <= 0.0:
            continue

        cross = abs((left_x * right_y) - (left_y * right_x))
        dot = (left_x * right_x) + (left_y * right_y)
        turn = math.atan2(cross, dot) / math.pi
        radial_step_change = abs(math.log(right_norm / left_norm))
        scores[original_index] = turn + (0.25 * radial_step_change)
    return scores


def residue_wheel_frequency_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Exact wheel class frequency on scan_prime mod 210.

    This is intentionally label-free: the score is only how common the row's
    residue class is among the candidate rows in the same board.
    """
    modulus = 2 * 3 * 5 * 7
    residues = [_scan_prime(row) % modulus for row in rows]
    counts: dict[int, int] = {}
    for residue in residues:
        counts[residue] = counts.get(residue, 0) + 1
    max_count = max(counts.values(), default=1)
    return [counts[residue] / max_count for residue in residues]


@lru_cache(maxsize=64)
def _factor_primes(limit: int) -> tuple[int, ...]:
    if limit < 2:
        return ()
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = 0
    sieve[1] = 0
    root = math.isqrt(limit)
    for value in range(2, root + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = bytearray(((limit - start) // value) + 1)
    return tuple(index for index in range(2, limit + 1) if sieve[index])


def _divisor_count_with_primes(value: int, primes: tuple[int, ...]) -> int:
    if value <= 0:
        return 0
    if value == 1:
        return 1

    remaining = value
    count = 1
    for prime in primes:
        if prime * prime > remaining:
            break
        if remaining % prime != 0:
            continue
        exponent = 0
        while remaining % prime == 0:
            exponent += 1
            remaining //= prime
        count *= exponent + 1
    if remaining > 1:
        count *= 2
    return count


def numerical_emulsion_scores(rows: list[dict[str, Any]]) -> list[float]:
    """Local factor-pressure collar around each visible scan prime.

    The row's scan_prime is already prime, so primality itself is not useful as
    a discriminator. This score treats the prime as an interface and measures
    the composite pressure in a small integer collar on both sides:

      - immediate boundary pressure: tau(n-1) + tau(n+1)
      - peak composite connectivity in the collar
      - left/right transition asymmetry

    It is intentionally frozen and label-free: no future_anchor fields, no
    anchor residues, and no fitted target statistics.
    """
    if not rows:
        return []

    radius = 6
    scan_primes = [_scan_prime(row) for row in rows]
    max_value = max(scan_primes) + radius
    primes = _factor_primes(math.isqrt(max_value) + 1)

    scores: list[float] = []
    for scan_prime in scan_primes:
        left = [
            _divisor_count_with_primes(scan_prime - dist, primes)
            for dist in range(1, radius + 1)
            if scan_prime - dist >= 1
        ]
        right = [
            _divisor_count_with_primes(scan_prime + dist, primes)
            for dist in range(1, radius + 1)
        ]
        collar = left + right
        if not collar:
            scores.append(0.0)
            continue

        left_sum = float(sum(left))
        right_sum = float(sum(right))
        immediate = float((left[0] if left else 0) + (right[0] if right else 0))
        peak = float(max(collar))
        transition = abs(left_sum - right_sum) / max(1.0, left_sum + right_sum)
        scores.append(math.log1p(immediate) + math.log1p(peak) + transition)
    return scores


def axis_score_fn(
    ctx: ScoreContext, axis_name: str
) -> Callable[[list[dict[str, Any]]], list[float]]:
    name = axis_name.strip().lower()
    if name == "frozen":
        return _frozen_scores(ctx)
    if name == "rr_sqrt1":
        return _rr_scores(ctx)
    if name == "log_power_bridge":
        return log_power_bridge_scores
    if name == "golden_spiral_phase":
        return golden_spiral_phase_scores
    if name == "gap_acceleration":
        return gap_acceleration_scores
    if name == "ratio_curvature":
        return ratio_curvature_scores
    if name == "ratio_graph_resonance":
        return ratio_graph_resonance_scores
    if name == "prime_circuit_geometry":
        return prime_circuit_geometry_scores
    if name == "residue_wheel_frequency":
        return residue_wheel_frequency_scores
    if name == "numerical_emulsion":
        return numerical_emulsion_scores
    raise ValueError(f"unknown alignment axis: {axis_name}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_ledger(
    ctx: ScoreContext, rings: list[str], with_index: bool
) -> dict[str, Any]:
    ring_rows = {ring: ctx.load_ring(ring) for ring in rings}

    prime_index_lookup: dict[int, int] | None = None
    if with_index:
        values: set[int] = set()
        for rows in ring_rows.values():
            for row in rows:
                if row.get("future_anchor"):
                    val = _anchor_value(row)
                    if val is not None and is_prime_u64(val):
                        values.add(val)
        # Single segmented count to the max anchor (memory bounded by segment size).
        prime_index_lookup = prime_indices_for_values(values)

    ledger: dict[str, Any] = {
        "rings": {},
        "config": GATE_CONFIG.config_id,
        "with_index": with_index,
    }
    for ring in rings:
        records = build_anchor_records(ring, ring_rows[ring], prime_index_lookup)
        edges = relationship_edges(records)
        anchors = actual_anchor_ids(ring_rows[ring])
        ledger["rings"][ring] = {
            "known_anchors": len(anchors),
            "records": [asdict(r) for r in records],
            "edges": edges,
        }
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--rings", default="K,L,M,N")
    parser.add_argument(
        "--with-index",
        action="store_true",
        help="compute exact pi(p) + superprime check (slower)",
    )
    parser.add_argument(
        "--gate-demo",
        action="store_true",
        help="run the gate on frozen (PASS) and rr (FAIL)",
    )
    parser.add_argument("--gate-seeds", type=int, default=DEFAULT_GATE_SEEDS)
    parser.add_argument(
        "--axes", default=DEFAULT_GATE_AXES, help="comma-separated axes for --gate-demo"
    )
    parser.add_argument(
        "--count-honest-axis",
        default=None,
        help="fit a count-honest cutoff on --freeze-ring",
    )
    parser.add_argument("--freeze-ring", default="K")
    parser.add_argument("--test-rings", default="L,M,N")
    parser.add_argument("--out-dir", default="artifacts/prime_alignment_ledger")
    parser.add_argument("--cache-dir", default=None)
    args = parser.parse_args()

    rings = [r.strip() for r in args.rings.split(",") if r.strip()]
    if args.cache_dir:
        ctx = ScoreContext(Path(args.cache_dir))
    else:
        from run_prime_search_engine_bench import DEFAULT_ROW_CACHE_DIR

        ctx = ScoreContext(Path(str(DEFAULT_ROW_CACHE_DIR)))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ledger = build_ledger(ctx, rings, args.with_index)
    ledger_path = out_dir / "ledger.json"
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(f"ledger -> {ledger_path}")
    for ring in rings:
        info = ledger["rings"][ring]
        sample = info["records"][0] if info["records"] else {}
        sp = sample.get("is_superprime")
        sp_str = "" if sp is None else f"  superprime[0]={sp}"
        print(
            f"  ring {ring}: {info['known_anchors']} known anchors, {len(info['edges'])} edges{sp_str}"
        )

    if args.gate_demo:
        print("\n=== AXIS GATE DEMO (null-check of the gate itself) ===")
        ring_rows = {ring: ctx.load_ring(ring) for ring in rings}
        axis_names = [name.strip() for name in args.axes.split(",") if name.strip()]
        gate_payload = {}
        for name in axis_names:
            fn = axis_score_fn(ctx, name)
            res = gate_axis(ctx, fn, rings, ring_rows, seeds=args.gate_seeds)
            gate_payload[name] = res
            print(
                f"\naxis '{name}': {res['verdict']}  (config {res['config_id']}, {res['seeds']} seeds)"
            )
            print(
                "  ring  prec_real  prec_p95  cnt_err  /actual  prec?  cnt?  (recall_real reported)"
            )
            for r in res["per_ring"]:
                pf = "ok " if r["passes_precision"] else "FAIL"
                cf = "ok " if r["passes_count"] else "FAIL"
                print(
                    f"  {r['ring']:>4}   {r['precision_real']:.3f}    {r['precision_null_p95']:.3f}   "
                    f"{r['count_error']:+5d}   /{r['actual_anchors']:<4}  {pf}   {cf}   (rec {r['recall_real']:.3f})"
                )
        gate_path = out_dir / "gate_demo.json"
        gate_path.write_text(json.dumps(gate_payload, indent=2), encoding="utf-8")
        print(f"\ngate demo -> {gate_path}")

    if args.count_honest_axis:
        freeze_ring = args.freeze_ring.strip().upper()
        test_rings = [
            ring.strip().upper() for ring in args.test_rings.split(",") if ring.strip()
        ]
        needed_rings = sorted(set([freeze_ring, *test_rings]))
        ring_rows = {ring: ctx.load_ring(ring) for ring in needed_rings}
        probe = count_honest_axis_probe(
            ctx=ctx,
            axis_name=args.count_honest_axis,
            freeze_ring=freeze_ring,
            test_rings=test_rings,
            ring_rows=ring_rows,
            seeds=args.gate_seeds,
        )
        print("\n=== COUNT-HONEST AXIS PROBE ===")
        print(
            "axis '{axis}' frozen on {freeze}: {verdict} ({config})".format(
                axis=probe["axis"],
                freeze=probe["freeze_ring"],
                verdict=probe["verdict"],
                config=probe["frozen_config"],
            )
        )
        fit = probe["fit_on_freeze_ring"]
        print(
            "  fit: percentile={:.3f} predicted={} actual={} count_error={:+d} precision={:.3f}".format(
                fit["percentile"],
                fit["predicted_clusters"],
                fit["actual_unique_anchors"],
                fit["count_error"],
                fit["precision"],
            )
        )
        print("  ring  prec_real  prec_p95  predicted  cnt_err  /actual  prec?  cnt?")
        for ring in probe["per_ring"]:
            pf = "ok " if ring["passes_precision"] else "FAIL"
            cf = "ok " if ring["passes_count"] else "FAIL"
            print(
                "  {ring:>4}   {pr:.3f}    {p95:.3f}      {pred:>4}   {err:+5d}   /{actual:<4}  {pf}   {cf}".format(
                    ring=ring["ring"],
                    pr=ring["precision_real"],
                    p95=ring["precision_null_p95"],
                    pred=ring["predicted_clusters"],
                    err=ring["count_error"],
                    actual=ring["actual_anchors"],
                    pf=pf,
                    cf=cf,
                )
            )
        count_path = out_dir / f"{args.count_honest_axis}_count_honest_probe.json"
        count_path.write_text(json.dumps(probe, indent=2), encoding="utf-8")
        print(f"\ncount-honest probe -> {count_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
