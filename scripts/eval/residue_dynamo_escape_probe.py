#!/usr/bin/env python3
"""Residue dynamo escape-corridor probe.

The first residue-dynamo prototype showed the important inversion:

    composites -> dense modular intersections / coherence wells
    primes     -> sparse residue escape points

This probe keeps that split explicit. It does not claim a new prime finder.
It asks two falsifiable questions:

1. Does the raw dynamo coherence rank composites above primes?
2. Does an escape score rank primes above composites better than a shuffled null?

It also reports a narrow bridge check for next-prime gap buckets. That lane is
expected to be weak unless the field carries transition information, not just
instantaneous divisibility structure.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

DEFAULT_LIMIT = 5000
DEFAULT_BAND_COUNT = 12
DEFAULT_NULL_RUNS = 400
DEFAULT_SEED = 173
CLASS_NAMES = {0: "small", 1: "normal", 2: "large"}


@dataclass(frozen=True)
class DynamoScore:
    n: int
    is_prime: bool
    hit_count: int
    divisibility_density: float
    nonzero_fraction: float
    raw_dynamo_score: float
    composite_coherence: float
    residue_spread: float
    escape_score: float


@dataclass(frozen=True)
class BinaryMetric:
    auc: float
    null_mean: float
    null_p95: float
    p_value: float
    beats_null95: bool


@dataclass(frozen=True)
class BridgeStats:
    count: int
    delta_escape_mean: float
    delta_escape_std: float
    delta_escape_min: float
    delta_escape_max: float
    current_escape_large_gap_auc: BinaryMetric
    current_coherence_large_gap_auc: BinaryMetric


@dataclass(frozen=True)
class ResidueDynamoProbeResult:
    schema_version: str
    verdict: str
    limit: int
    bands: list[int]
    counts: dict[str, int]
    mean_scores: dict[str, dict[str, float]]
    composite_coherence_auc: BinaryMetric
    prime_escape_auc: BinaryMetric
    prime_raw_dynamo_auc: BinaryMetric
    bridge: BridgeStats
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _small_primes(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for value in range(2, int(limit**0.5) + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = b"\x00" * len(
                sieve[start : limit + 1 : value]
            )
    return [value for value in range(2, limit + 1) if sieve[value]]


def _is_prime_table(limit: int) -> list[bool]:
    table = [False] * (limit + 1)
    for prime in _small_primes(limit):
        table[prime] = True
    return table


def _first_primes(count: int) -> list[int]:
    if count <= 0:
        return []
    limit = max(
        16,
        int(
            count
            * (math.log(max(count, 2)) + math.log(max(math.log(max(count, 3)), 2)))
        )
        + 10,
    )
    while True:
        primes = _small_primes(limit)
        if len(primes) >= count:
            return primes[:count]
        limit *= 2


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def score_number(
    n: int, bands: Sequence[int], is_prime: bool | None = None
) -> DynamoScore:
    """Score one integer as a modular dynamo field."""
    if n < 2:
        raise ValueError("n must be >= 2")
    if not bands:
        raise ValueError("bands must not be empty")

    phases: list[float] = []
    signed_vectors: list[complex] = []
    hits: list[int] = []

    for prime in bands:
        residue = n % prime
        # A prime equal to one of the band primes is not a composite collision.
        hit = int(residue == 0 and n != prime)
        phase = 2.0 * math.pi * residue / prime
        polarity = -1.0 if hit else 1.0
        phases.append(phase)
        signed_vectors.append(polarity * complex(math.cos(phase), math.sin(phase)))
        hits.append(hit)

    pair_couplings: list[float] = []
    for i in range(len(phases)):
        for j in range(i + 1, len(phases)):
            phase_alignment = 0.5 * (1.0 + math.cos(phases[i] - phases[j]))
            hit_boost = 1.0 + hits[i] + hits[j]
            pair_couplings.append(phase_alignment * hit_boost / 3.0)

    hit_count = sum(hits)
    divisibility_density = hit_count / len(bands)
    nonzero_fraction = 1.0 - divisibility_density
    raw_dynamo_score = _mean(pair_couplings)
    resultant = abs(sum(signed_vectors) / len(signed_vectors))
    residue_spread = 1.0 - resultant
    composite_coherence = (0.55 * divisibility_density) + (0.45 * raw_dynamo_score)
    escape_score = (
        (0.50 * nonzero_fraction)
        + (0.35 * residue_spread)
        + (0.15 * (1.0 - raw_dynamo_score))
        - (0.50 * divisibility_density)
    )

    if is_prime is None:
        is_prime = n in set(_small_primes(n))

    return DynamoScore(
        n=n,
        is_prime=bool(is_prime),
        hit_count=hit_count,
        divisibility_density=round(divisibility_density, 8),
        nonzero_fraction=round(nonzero_fraction, 8),
        raw_dynamo_score=round(raw_dynamo_score, 8),
        composite_coherence=round(composite_coherence, 8),
        residue_spread=round(residue_spread, 8),
        escape_score=round(escape_score, 8),
    )


def _auc(labels: Sequence[int], scores: Sequence[float]) -> float:
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have the same length")
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return float("nan")

    ranked = sorted(zip(scores, labels), key=lambda item: item[0])
    rank_sum_pos = 0.0
    rank = 1
    idx = 0
    while idx < len(ranked):
        end = idx + 1
        while end < len(ranked) and ranked[end][0] == ranked[idx][0]:
            end += 1
        avg_rank = (rank + rank + (end - idx) - 1) / 2.0
        for cursor in range(idx, end):
            if ranked[cursor][1] == 1:
                rank_sum_pos += avg_rank
        rank += end - idx
        idx = end

    return float(
        (rank_sum_pos - positives * (positives + 1) / 2.0) / (positives * negatives)
    )


def _binary_metric(
    labels: Sequence[int],
    scores: Sequence[float],
    *,
    seed: int,
    null_runs: int,
) -> BinaryMetric:
    rng = random.Random(seed)
    auc = _auc(labels, scores)
    nulls: list[float] = []
    label_list = list(labels)
    for _ in range(null_runs):
        shuffled = label_list[:]
        rng.shuffle(shuffled)
        nulls.append(_auc(shuffled, scores))
    null_p95 = float(np.quantile(nulls, 0.95))
    p_value = (1.0 + sum(1 for value in nulls if value >= auc)) / (null_runs + 1.0)
    return BinaryMetric(
        auc=round(auc, 6),
        null_mean=round(float(np.mean(nulls)), 6),
        null_p95=round(null_p95, 6),
        p_value=round(p_value, 6),
        beats_null95=bool(auc > null_p95),
    )


def _gap_bucket(gap: int, prime: int) -> int:
    expected = math.log(prime)
    if gap < 0.75 * expected:
        return 0
    if gap <= 1.5 * expected:
        return 1
    return 2


def _bridge_stats(
    scores: list[DynamoScore], bands: Sequence[int], seed: int, null_runs: int
) -> BridgeStats:
    by_n = {score.n: score for score in scores}
    primes = [score.n for score in scores if score.is_prime]
    deltas: list[float] = []
    large_gap_labels: list[int] = []
    current_escape: list[float] = []
    current_coherence: list[float] = []

    for left, right in zip(primes, primes[1:]):
        left_score = by_n[left]
        right_score = by_n[right]
        gap = right - left
        bucket = _gap_bucket(gap, left)
        deltas.append(right_score.escape_score - left_score.escape_score)
        large_gap_labels.append(int(bucket == 2))
        current_escape.append(left_score.escape_score)
        current_coherence.append(left_score.composite_coherence)

    if len(set(large_gap_labels)) < 2:
        # Keep the schema stable for tiny limits.
        empty = BinaryMetric(
            float("nan"), float("nan"), float("nan"), float("nan"), False
        )
        return BridgeStats(
            count=len(deltas),
            delta_escape_mean=round(float(np.mean(deltas)) if deltas else 0.0, 6),
            delta_escape_std=round(float(np.std(deltas)) if deltas else 0.0, 6),
            delta_escape_min=round(min(deltas) if deltas else 0.0, 6),
            delta_escape_max=round(max(deltas) if deltas else 0.0, 6),
            current_escape_large_gap_auc=empty,
            current_coherence_large_gap_auc=empty,
        )

    return BridgeStats(
        count=len(deltas),
        delta_escape_mean=round(float(np.mean(deltas)), 6),
        delta_escape_std=round(float(np.std(deltas)), 6),
        delta_escape_min=round(min(deltas), 6),
        delta_escape_max=round(max(deltas), 6),
        current_escape_large_gap_auc=_binary_metric(
            large_gap_labels,
            current_escape,
            seed=seed + 100,
            null_runs=null_runs,
        ),
        current_coherence_large_gap_auc=_binary_metric(
            large_gap_labels,
            current_coherence,
            seed=seed + 101,
            null_runs=null_runs,
        ),
    )


def _write_scores_csv(path: Path, scores: list[DynamoScore]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(scores[0]).keys()))
        writer.writeheader()
        for score in scores:
            writer.writerow(asdict(score))


def _write_bridge_csv(path: Path, scores: list[DynamoScore]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_n = {score.n: score for score in scores}
    primes = [score.n for score in scores if score.is_prime]
    rows: list[dict[str, int | float | str]] = []
    for left, right in zip(primes, primes[1:]):
        gap = right - left
        left_score = by_n[left]
        right_score = by_n[right]
        rows.append(
            {
                "prime": left,
                "next_prime": right,
                "gap_next": gap,
                "gap_bucket": CLASS_NAMES[_gap_bucket(gap, left)],
                "current_escape_score": left_score.escape_score,
                "next_escape_score": right_score.escape_score,
                "delta_escape_score": round(
                    right_score.escape_score - left_score.escape_score, 8
                ),
                "current_composite_coherence": left_score.composite_coherence,
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_probe(
    *,
    limit: int = DEFAULT_LIMIT,
    band_count: int = DEFAULT_BAND_COUNT,
    null_runs: int = DEFAULT_NULL_RUNS,
    seed: int = DEFAULT_SEED,
) -> tuple[ResidueDynamoProbeResult, list[DynamoScore]]:
    if limit < 100:
        raise ValueError("limit must be >= 100")
    if band_count < 4:
        raise ValueError("band_count must be >= 4")
    if null_runs < 40:
        raise ValueError("null_runs must be >= 40")

    bands = _first_primes(band_count)
    prime_table = _is_prime_table(limit)
    scores = [score_number(n, bands, prime_table[n]) for n in range(2, limit + 1)]

    composite_labels = [int(not score.is_prime) for score in scores]
    prime_labels = [int(score.is_prime) for score in scores]
    composite_coherence = [score.composite_coherence for score in scores]
    escape_scores = [score.escape_score for score in scores]
    raw_dynamo = [score.raw_dynamo_score for score in scores]

    prime_rows = [score for score in scores if score.is_prime]
    composite_rows = [score for score in scores if not score.is_prime]

    def means(rows: Sequence[DynamoScore]) -> dict[str, float]:
        return {
            "raw_dynamo_score": round(_mean([row.raw_dynamo_score for row in rows]), 6),
            "composite_coherence": round(
                _mean([row.composite_coherence for row in rows]), 6
            ),
            "escape_score": round(_mean([row.escape_score for row in rows]), 6),
            "hit_count": round(_mean([row.hit_count for row in rows]), 6),
        }

    composite_metric = _binary_metric(
        composite_labels,
        composite_coherence,
        seed=seed,
        null_runs=null_runs,
    )
    escape_metric = _binary_metric(
        prime_labels,
        escape_scores,
        seed=seed + 1,
        null_runs=null_runs,
    )
    raw_prime_metric = _binary_metric(
        prime_labels,
        raw_dynamo,
        seed=seed + 2,
        null_runs=null_runs,
    )
    bridge = _bridge_stats(scores, bands, seed, null_runs)

    if composite_metric.beats_null95 and escape_metric.beats_null95:
        verdict = "ESCAPE_CORRIDOR_SEPARATES_PRIMES"
    elif composite_metric.beats_null95:
        verdict = "COMPOSITE_COHERENCE_ONLY"
    else:
        verdict = "NO_RESIDUE_DYNAMO_SIGNAL"

    result = ResidueDynamoProbeResult(
        schema_version="residue_dynamo_escape_probe_v1",
        verdict=verdict,
        limit=limit,
        bands=bands,
        counts={"primes": len(prime_rows), "composites": len(composite_rows)},
        mean_scores={"primes": means(prime_rows), "composites": means(composite_rows)},
        composite_coherence_auc=composite_metric,
        prime_escape_auc=escape_metric,
        prime_raw_dynamo_auc=raw_prime_metric,
        bridge=bridge,
        claim_boundary=(
            "This is a wheel/residue-field probe. It validates the escape-corridor "
            "scoring surface against shuffled labels, not a new primality theorem. "
            "The bridge lane is reported separately because prime/composite separation "
            "does not imply next-gap prediction."
        ),
    )
    return result, scores


def _print_summary(result: ResidueDynamoProbeResult) -> None:
    print(f"verdict={result.verdict}")
    print(f"limit={result.limit} bands={result.bands}")
    print(
        "mean raw dynamo: "
        f"prime={result.mean_scores['primes']['raw_dynamo_score']:.6f} "
        f"composite={result.mean_scores['composites']['raw_dynamo_score']:.6f}"
    )
    print(
        "mean escape: "
        f"prime={result.mean_scores['primes']['escape_score']:.6f} "
        f"composite={result.mean_scores['composites']['escape_score']:.6f}"
    )
    print(
        "AUC composite_coherence="
        f"{result.composite_coherence_auc.auc:.3f} null95={result.composite_coherence_auc.null_p95:.3f}"
    )
    print(
        f"AUC prime_escape={result.prime_escape_auc.auc:.3f} null95={result.prime_escape_auc.null_p95:.3f}"
    )
    print(
        "bridge large-gap AUC: "
        f"escape={result.bridge.current_escape_large_gap_auc.auc:.3f} "
        f"coherence={result.bridge.current_coherence_large_gap_auc.auc:.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--band-count", type=int, default=DEFAULT_BAND_COUNT)
    parser.add_argument("--null-runs", type=int, default=DEFAULT_NULL_RUNS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts/eval/residue_dynamo_escape_probe"),
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full JSON report"
    )
    args = parser.parse_args()

    result, scores = run_probe(
        limit=args.limit,
        band_count=args.band_count,
        null_runs=args.null_runs,
        seed=args.seed,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "report.json"
    scores_path = args.out_dir / "residue_dynamo_scores.csv"
    bridge_path = args.out_dir / "prime_bridge_table.csv"
    report_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_scores_csv(scores_path, scores)
    _write_bridge_csv(bridge_path, scores)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        _print_summary(result)
        print(f"report={report_path}")
        print(f"scores_csv={scores_path}")
        print(f"bridge_csv={bridge_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
