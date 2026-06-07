"""Additive prime-boundary spectrum null test.

This tests the instrumental version of the "boundary layer" idea:

    known prime p -> additive boundary b = p + 1

The question is not whether p is prime. The known primes are the calibration set.
The question is whether the factor spectrum of p+1 carries prime-specific structure
after comparing it with size-matched even-number nulls.

Two nulls are reported:

1. raw even null: random even integers near p
2. wheel-admissible predecessor null: random even b near p where b-1 survives
   the same small-prime wheel constraints used by primes

If the real boundary only beats the raw null but not the wheel null, the signal is
mostly known residue/admissibility structure. If it beats both, the additive
boundary has residual prime-specific structure worth chasing.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_boundary_spectrum_null"
DEFAULT_WHEEL_PRIMES = (2, 3, 5, 7)
FEATURE_NAMES = (
    "omega",
    "big_omega",
    "log_tau",
    "two_adic",
    "largest_pf_log_ratio",
    "smooth_7",
    "smooth_29",
    "smooth_97",
)


@dataclass(frozen=True)
class BoundaryRecord:
    prime: int
    boundary: int
    gap_before: int
    gap_after: int
    log_prime: float
    mod_30: int
    mod_210: int
    omega: int
    big_omega: int
    tau: int
    two_adic: int
    largest_prime_factor: int
    largest_pf_log_ratio: float
    smooth_7: int
    smooth_29: int
    smooth_97: int
    boundary_class: str
    hybrid_operation_score: float


def nth_prime_upper_bound(n: int) -> int:
    if n < 6:
        return 16
    value = int(n * (math.log(n) + math.log(math.log(n))) + 32)
    return max(value, 32)


def simple_sieve(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    root = int(limit**0.5)
    for value in range(2, root + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = b"\x00" * (
                ((limit - start) // value) + 1
            )
    return [idx for idx, is_prime in enumerate(sieve) if is_prime]


def first_n_primes(n: int) -> list[int]:
    if n < 3:
        raise ValueError("n must be at least 3")
    limit = nth_prime_upper_bound(n)
    while True:
        primes = simple_sieve(limit)
        if len(primes) >= n:
            return primes[:n]
        limit *= 2


def factorize(value: int, primes: Iterable[int]) -> dict[int, int]:
    if value < 2:
        return {}
    remaining = value
    factors: dict[int, int] = {}
    for prime in primes:
        if prime * prime > remaining:
            break
        while remaining % prime == 0:
            factors[prime] = factors.get(prime, 0) + 1
            remaining //= prime
    if remaining > 1:
        factors[remaining] = factors.get(remaining, 0) + 1
    return factors


def divisor_count(factors: dict[int, int]) -> int:
    total = 1
    for exponent in factors.values():
        total *= exponent + 1
    return total


def boundary_class(factors: dict[int, int]) -> str:
    if not factors:
        return "unit"
    largest = max(factors)
    if set(factors) == {2}:
        return "tower_2_power"
    if (
        factors.get(2) == 1
        and len(factors) == 2
        and all(exp == 1 for exp in factors.values())
    ):
        return "semiprime_2q"
    if largest <= 7:
        return "smooth_7_shattered"
    if largest <= 29:
        return "smooth_29"
    if len(factors) >= 5:
        return "many_factor_generic"
    return "generic"


def features_from_factors(value: int, factors: dict[int, int]) -> tuple[float, ...]:
    omega = len(factors)
    big_omega = sum(factors.values())
    tau = divisor_count(factors)
    largest_pf = max(factors) if factors else 1
    log_ratio = math.log(largest_pf) / max(math.log(value), 1e-12)
    return (
        float(omega),
        float(big_omega),
        math.log(float(tau)),
        float(factors.get(2, 0)),
        log_ratio,
        1.0 if largest_pf <= 7 else 0.0,
        1.0 if largest_pf <= 29 else 0.0,
        1.0 if largest_pf <= 97 else 0.0,
    )


def hybrid_operation_score(
    value: int, factors: dict[int, int], gap_after: int, log_prime: float
) -> float:
    """Single bounded feature for the user's "hybrid operation bucket" idea.

    This intentionally does not decide primality. It combines factor-shadow
    density with the known next-step scale so records can be sorted/clustered.
    """
    (
        omega,
        big_omega,
        log_tau,
        two_adic,
        largest_ratio,
        smooth_7,
        smooth_29,
        smooth_97,
    ) = features_from_factors(value, factors)
    density = omega + 0.5 * big_omega + log_tau + 0.25 * two_adic
    smooth_bonus = 0.5 * smooth_7 + 0.25 * smooth_29 + 0.1 * smooth_97
    rough_penalty = largest_ratio
    gap_pressure = math.log1p(gap_after) / max(log_prime, 1e-12)
    return density + smooth_bonus - rough_penalty - gap_pressure


def build_boundary_record(
    primes: list[int], index: int, factor_primes: list[int]
) -> BoundaryRecord:
    prime = primes[index]
    boundary = prime + 1
    factors = factorize(boundary, factor_primes)
    (
        omega,
        big_omega,
        _log_tau,
        two_adic,
        largest_ratio,
        smooth_7,
        smooth_29,
        smooth_97,
    ) = features_from_factors(boundary, factors)
    gap_before = prime - primes[index - 1]
    gap_after = primes[index + 1] - prime
    log_prime = math.log(prime)
    return BoundaryRecord(
        prime=prime,
        boundary=boundary,
        gap_before=gap_before,
        gap_after=gap_after,
        log_prime=log_prime,
        mod_30=prime % 30,
        mod_210=prime % 210,
        omega=int(omega),
        big_omega=int(big_omega),
        tau=divisor_count(factors),
        two_adic=int(two_adic),
        largest_prime_factor=max(factors) if factors else 1,
        largest_pf_log_ratio=largest_ratio,
        smooth_7=int(smooth_7),
        smooth_29=int(smooth_29),
        smooth_97=int(smooth_97),
        boundary_class=boundary_class(factors),
        hybrid_operation_score=hybrid_operation_score(
            boundary, factors, gap_after, log_prime
        ),
    )


def random_even_near(anchor: int, rng: random.Random) -> int:
    span = max(1_000, int(math.sqrt(anchor)) * 4)
    lo = max(4, anchor - span)
    hi = anchor + span
    value = rng.randrange(lo // 2, hi // 2 + 1) * 2
    return max(4, value)


def survives_wheel_predecessor(boundary: int, wheel_primes: tuple[int, ...]) -> bool:
    predecessor = boundary - 1
    return all(
        predecessor % prime != 0 or predecessor == prime for prime in wheel_primes
    )


def random_wheel_even_near(
    anchor: int, rng: random.Random, wheel_primes: tuple[int, ...]
) -> int:
    span = max(1_000, int(math.sqrt(anchor)) * 4)
    for attempt in range(20_000):
        candidate = random_even_near(anchor, rng)
        if survives_wheel_predecessor(candidate, wheel_primes):
            return candidate
        if attempt and attempt % 5_000 == 0:
            span *= 2
    raise RuntimeError("could not sample wheel-admissible even boundary")


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def summarize_feature_rows(rows: list[tuple[float, ...]]) -> dict[str, float]:
    return {
        name: mean([row[idx] for row in rows]) for idx, name in enumerate(FEATURE_NAMES)
    }


def summarize_classes(classes: list[str]) -> dict[str, float]:
    counts = Counter(classes)
    total = sum(counts.values()) or 1
    return {name: count / total for name, count in sorted(counts.items())}


def zscore_train_test(
    train_rows: list[tuple[float, ...]], test_rows: list[tuple[float, ...]]
) -> tuple[list[tuple[float, ...]], list[tuple[float, ...]]]:
    dim = len(train_rows[0])
    mus = [mean([row[idx] for row in train_rows]) for idx in range(dim)]
    sigmas = []
    for idx in range(dim):
        col = [row[idx] for row in train_rows]
        sigma = statistics.pstdev(col)
        sigmas.append(sigma if sigma > 1e-12 else 1.0)

    def transform(rows: list[tuple[float, ...]]) -> list[tuple[float, ...]]:
        return [
            tuple((row[idx] - mus[idx]) / sigmas[idx] for idx in range(dim))
            for row in rows
        ]

    return transform(train_rows), transform(test_rows)


def centroid_accuracy(
    positive_rows: list[tuple[float, ...]],
    negative_rows: list[tuple[float, ...]],
    seed: int,
    shuffle_labels: bool = False,
) -> float:
    rng = random.Random(seed)
    samples = [(row, 1) for row in positive_rows] + [(row, 0) for row in negative_rows]
    rng.shuffle(samples)
    if shuffle_labels:
        labels = [label for _row, label in samples]
        rng.shuffle(labels)
        samples = [(samples[idx][0], labels[idx]) for idx in range(len(samples))]

    split = max(2, int(len(samples) * 0.7))
    train = samples[:split]
    test = samples[split:]
    train_rows_raw = [row for row, _label in train]
    test_rows_raw = [row for row, _label in test]
    train_rows, test_rows = zscore_train_test(train_rows_raw, test_rows_raw)
    train_labels = [label for _row, label in train]

    centroids: dict[int, tuple[float, ...]] = {}
    for label in (0, 1):
        label_rows = [
            row
            for row, row_label in zip(train_rows, train_labels)
            if row_label == label
        ]
        if not label_rows:
            return 0.5
        centroids[label] = tuple(
            mean([row[idx] for row in label_rows]) for idx in range(len(label_rows[0]))
        )

    correct = 0
    for row, (_raw_row, label) in zip(test_rows, test):
        distances = {
            centroid_label: sum(
                (value - centroids[centroid_label][idx]) ** 2
                for idx, value in enumerate(row)
            )
            for centroid_label in (0, 1)
        }
        predicted = 1 if distances[1] <= distances[0] else 0
        correct += int(predicted == label)
    return correct / len(test)


def null95(
    positive_rows: list[tuple[float, ...]],
    negative_rows: list[tuple[float, ...]],
    seed: int,
    trials: int,
) -> float:
    scores = [
        centroid_accuracy(
            positive_rows, negative_rows, seed=seed + 10_000 + idx, shuffle_labels=True
        )
        for idx in range(trials)
    ]
    scores.sort()
    return scores[min(len(scores) - 1, int(math.ceil(0.95 * len(scores))) - 1)]


def compare_against_null(
    positive_rows: list[tuple[float, ...]],
    negative_rows: list[tuple[float, ...]],
    seed: int,
    trials: int,
) -> dict[str, float | str]:
    real = centroid_accuracy(
        positive_rows, negative_rows, seed=seed, shuffle_labels=False
    )
    threshold = null95(positive_rows, negative_rows, seed=seed, trials=trials)
    margin = real - threshold
    return {
        "centroid_accuracy": real,
        "shuffle_null95": threshold,
        "margin": margin,
        "verdict": (
            "RESIDUAL_BOUNDARY_SIGNAL" if margin > 0.03 else "MATCHES_NULL_OR_WHEEL"
        ),
    }


def run_experiment(n_primes: int, seed: int, null_trials: int) -> dict[str, object]:
    primes = first_n_primes(n_primes + 2)
    max_boundary = primes[n_primes] + 1
    factor_primes = simple_sieve(int(math.sqrt(max_boundary + 10_000)) + 100)
    rng = random.Random(seed)

    records = [
        build_boundary_record(primes, index, factor_primes)
        for index in range(4, n_primes)
    ]

    prime_rows = [
        features_from_factors(
            record.boundary, factorize(record.boundary, factor_primes)
        )
        for record in records
    ]

    raw_even_values = [random_even_near(record.prime, rng) for record in records]
    wheel_even_values = [
        random_wheel_even_near(record.prime, rng, DEFAULT_WHEEL_PRIMES)
        for record in records
    ]

    raw_rows = [
        features_from_factors(value, factorize(value, factor_primes))
        for value in raw_even_values
    ]
    wheel_rows = [
        features_from_factors(value, factorize(value, factor_primes))
        for value in wheel_even_values
    ]
    raw_classes = [
        boundary_class(factorize(value, factor_primes)) for value in raw_even_values
    ]
    wheel_classes = [
        boundary_class(factorize(value, factor_primes)) for value in wheel_even_values
    ]

    class_counts = Counter(record.boundary_class for record in records)
    tower_examples = [
        record.prime for record in records if record.boundary_class == "tower_2_power"
    ][:12]

    return {
        "schema": "prime-boundary-spectrum-null-v1",
        "n_primes_requested": n_primes,
        "n_records": len(records),
        "seed": seed,
        "wheel_primes": list(DEFAULT_WHEEL_PRIMES),
        "hypothesis": (
            "p+1 boundary spectra should beat raw even nulls if residue constraints matter; "
            "they must beat wheel-admissible predecessor nulls to show residual prime-specific structure."
        ),
        "feature_names": list(FEATURE_NAMES),
        "prime_boundary_means": summarize_feature_rows(prime_rows),
        "raw_even_null_means": summarize_feature_rows(raw_rows),
        "wheel_even_null_means": summarize_feature_rows(wheel_rows),
        "prime_boundary_class_share": summarize_classes(
            [record.boundary_class for record in records]
        ),
        "raw_even_class_share": summarize_classes(raw_classes),
        "wheel_even_class_share": summarize_classes(wheel_classes),
        "classifier_prime_vs_raw_even": compare_against_null(
            prime_rows, raw_rows, seed, null_trials
        ),
        "classifier_prime_vs_wheel_even": compare_against_null(
            prime_rows, wheel_rows, seed + 1, null_trials
        ),
        "tower_boundary_count": class_counts["tower_2_power"],
        "tower_boundary_examples": tower_examples,
        "top_hybrid_operation_records": [
            asdict(record)
            for record in sorted(
                records, key=lambda item: item.hybrid_operation_score, reverse=True
            )[:12]
        ],
        "decision_record": {
            "action": "research_probe",
            "reason": "test additive boundary spectrum against raw and wheel-matched nulls",
            "confidence": "bounded_by_sieve_range_and_null_trials",
            "promotion": "QUARANTINE_RESEARCH_ONLY",
        },
    }


def write_outputs(result: dict[str, object], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )

    records = result["top_hybrid_operation_records"]
    csv_path = out_dir / "top_hybrid_operation_records.csv"
    if isinstance(records, list) and records:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    return {"summary_json": str(summary_path), "top_records_csv": str(csv_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-primes", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--null-trials", type=int, default=100)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--json", action="store_true", help="print compact JSON summary to stdout"
    )
    args = parser.parse_args()

    result = run_experiment(args.n_primes, args.seed, args.null_trials)
    paths = write_outputs(result, args.out_dir)
    result["artifact_paths"] = paths
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        raw = result["classifier_prime_vs_raw_even"]
        wheel = result["classifier_prime_vs_wheel_even"]
        print("prime_boundary_spectrum_null")
        print(f"records={result['n_records']} seed={result['seed']}")
        print(
            "prime_vs_raw_even "
            f"acc={raw['centroid_accuracy']:.3f} null95={raw['shuffle_null95']:.3f} "
            f"margin={raw['margin']:.3f} verdict={raw['verdict']}"
        )
        print(
            "prime_vs_wheel_even "
            f"acc={wheel['centroid_accuracy']:.3f} null95={wheel['shuffle_null95']:.3f} "
            f"margin={wheel['margin']:.3f} verdict={wheel['verdict']}"
        )
        print(
            f"tower_boundaries={result['tower_boundary_count']} examples={result['tower_boundary_examples']}"
        )
        print(f"summary={paths['summary_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
