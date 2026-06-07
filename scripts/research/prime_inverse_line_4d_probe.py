"""4D inverse-line prime indicator probe.

This builds the "line piece" the user asked for as an inverse operation test:

Forward atlas:
    n -> factor profile

Inverse-line probe:
    surrounding operation field -> does n sit on the prime floor?

Anti-tautology rule: the 4D feature vector never includes the factorization of
the candidate n itself. It only uses scale, wheel region, and factor-shadow
measurements from neighboring integers. The hard null is a wheel-admissible
composite near the same scale.

The 4D coordinates are:

    x0 scale              = log(n)
    x1 regional bearing   = admissible mod-30 lane index
    x2 boundary density   = BigOmega(n-1) + BigOmega(n+1)
    x3 shadow curvature   = immediate boundary density minus wider shadow

If this beats the wheel-composite null, it is a real indicator surface. If it
collapses, the 4D line is a useful map of known structure but not a finder.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.prime_boundary_spectrum_null import (
    factorize,
    first_n_primes,
    simple_sieve,
)

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_inverse_line_4d"
ADMISSIBLE_MOD_30 = (1, 7, 11, 13, 17, 19, 23, 29)
LANE_INDEX = {residue: idx for idx, residue in enumerate(ADMISSIBLE_MOD_30)}
FEATURE_NAMES = (
    "log_n",
    "mod30_lane",
    "boundary_big_omega",
    "shadow_curvature",
)
FEATURE_SET_NAMES = (
    "inverse_shadow_4d",
    "boundary_pair_4d",
    "scale_free_shadow_4d",
    "scale_free_pair_4d",
)


@dataclass(frozen=True)
class InverseLineRecord:
    n: int
    label: str
    sample_kind: str
    log_n: float
    mod30_lane: float
    boundary_big_omega: float
    shadow_curvature: float
    boundary_left_big_omega: int
    boundary_right_big_omega: int
    wider_shadow_big_omega: float
    residue_mod_30: int
    feature_vector: tuple[float, float, float, float]


def big_omega(value: int, factor_primes: Iterable[int]) -> int:
    return sum(factorize(value, factor_primes).values())


def survives_wheel(value: int, wheel_primes: Sequence[int] = (2, 3, 5)) -> bool:
    return value > 1 and all(value % prime != 0 for prime in wheel_primes)


def four_dimensional_features(
    n: int, factor_primes: Sequence[int]
) -> tuple[float, float, float, float, int, int, float]:
    residue = n % 30
    lane = LANE_INDEX.get(residue)
    if lane is None:
        raise ValueError(f"n={n} is outside admissible mod-30 lanes")
    left = big_omega(n - 1, factor_primes)
    right = big_omega(n + 1, factor_primes)
    immediate = float(left + right)
    wider_values = [
        big_omega(n - 4, factor_primes),
        big_omega(n - 3, factor_primes),
        big_omega(n - 2, factor_primes),
        big_omega(n + 2, factor_primes),
        big_omega(n + 3, factor_primes),
        big_omega(n + 4, factor_primes),
    ]
    wider = sum(wider_values) / len(wider_values)
    shadow_curvature = math.log1p(immediate) - math.log1p(wider)
    return (
        math.log(n),
        lane / max(len(ADMISSIBLE_MOD_30) - 1, 1),
        math.log1p(immediate),
        shadow_curvature,
        left,
        right,
        wider,
    )


def is_prime_by_set(value: int, prime_set: set[int]) -> bool:
    return value in prime_set


def random_wheel_composite_near(
    center: int,
    prime_set: set[int],
    rng: random.Random,
    radius: int = 600,
) -> int:
    for _attempt in range(10_000):
        candidate = center + rng.randint(-radius, radius)
        if candidate < 11:
            continue
        if candidate % 2 == 0:
            candidate += 1
        if survives_wheel(candidate) and not is_prime_by_set(candidate, prime_set):
            return candidate
    raise RuntimeError(f"could not sample wheel composite near {center}")


def build_records(n_primes: int = 10_000, seed: int = 41) -> list[InverseLineRecord]:
    if n_primes < 50:
        raise ValueError("n_primes must be at least 50")
    rng = random.Random(seed)
    primes = first_n_primes(n_primes + 200)
    max_candidate = primes[n_primes - 1] + 2_000
    all_primes = simple_sieve(max_candidate + 16)
    prime_set = set(all_primes)
    factor_primes = simple_sieve(int(math.sqrt(max_candidate + 16)) + 16)

    positives = [
        prime for prime in primes if prime > 5 and prime <= primes[n_primes - 1]
    ]
    records: list[InverseLineRecord] = []

    def make_record(value: int, label: str, sample_kind: str) -> InverseLineRecord:
        (
            log_n,
            mod30_lane,
            boundary_big_omega,
            shadow_curvature,
            left,
            right,
            wider,
        ) = four_dimensional_features(value, factor_primes)
        return InverseLineRecord(
            n=value,
            label=label,
            sample_kind=sample_kind,
            log_n=log_n,
            mod30_lane=mod30_lane,
            boundary_big_omega=boundary_big_omega,
            shadow_curvature=shadow_curvature,
            boundary_left_big_omega=left,
            boundary_right_big_omega=right,
            wider_shadow_big_omega=wider,
            residue_mod_30=value % 30,
            feature_vector=(log_n, mod30_lane, boundary_big_omega, shadow_curvature),
        )

    for prime in positives:
        records.append(make_record(prime, "prime", "known_prime"))
        composite = random_wheel_composite_near(prime, prime_set, rng)
        records.append(make_record(composite, "composite", "wheel_composite"))
    return records


def zscore(
    train_rows: Sequence[Sequence[float]], rows: Sequence[Sequence[float]]
) -> list[list[float]]:
    width = len(train_rows[0])
    means = [
        sum(row[idx] for row in train_rows) / len(train_rows) for idx in range(width)
    ]
    stds: list[float] = []
    for idx in range(width):
        variance = sum((row[idx] - means[idx]) ** 2 for row in train_rows) / len(
            train_rows
        )
        stds.append(math.sqrt(variance) or 1.0)
    return [
        [(row[idx] - means[idx]) / stds[idx] for idx in range(width)] for row in rows
    ]


def train_test_indices(
    records: Sequence[InverseLineRecord], seed: int = 41
) -> tuple[list[int], list[int]]:
    rng = random.Random(seed)
    by_label: dict[str, list[int]] = defaultdict(list)
    for idx, record in enumerate(records):
        by_label[record.label].append(idx)
    train: list[int] = []
    test: list[int] = []
    for indices in by_label.values():
        shuffled = list(indices)
        rng.shuffle(shuffled)
        cut = int(0.7 * len(shuffled))
        train.extend(shuffled[:cut])
        test.extend(shuffled[cut:])
    return sorted(train), sorted(test)


def feature_vector_for(
    record: InverseLineRecord, feature_set: str = "inverse_shadow_4d"
) -> tuple[float, ...]:
    if feature_set == "inverse_shadow_4d":
        return record.feature_vector
    if feature_set == "boundary_pair_4d":
        return (
            record.log_n,
            record.mod30_lane,
            math.log1p(record.boundary_left_big_omega),
            math.log1p(record.boundary_right_big_omega),
        )
    if feature_set == "scale_free_shadow_4d":
        return (
            record.mod30_lane,
            record.boundary_big_omega,
            record.shadow_curvature,
            math.log1p(record.wider_shadow_big_omega),
        )
    if feature_set == "scale_free_pair_4d":
        return (
            record.mod30_lane,
            math.log1p(record.boundary_left_big_omega),
            math.log1p(record.boundary_right_big_omega),
            record.shadow_curvature,
        )
    raise ValueError(f"unknown feature set: {feature_set}")


def centroid_accuracy(
    records: Sequence[InverseLineRecord],
    seed: int = 41,
    shuffle_train_labels: bool = False,
    feature_set: str = "inverse_shadow_4d",
) -> float:
    train_idx, test_idx = train_test_indices(records, seed=seed)
    raw_rows = [
        feature_vector_for(record, feature_set=feature_set) for record in records
    ]
    scaled = zscore([raw_rows[idx] for idx in train_idx], raw_rows)
    train_labels = [records[idx].label for idx in train_idx]
    if shuffle_train_labels:
        rng = random.Random(seed + 1009)
        rng.shuffle(train_labels)

    sums: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for idx, label in zip(train_idx, train_labels):
        row = scaled[idx]
        sums.setdefault(label, [0.0] * len(row))
        counts[label] = counts.get(label, 0) + 1
        for col, value in enumerate(row):
            sums[label][col] += value
    centroids = {
        label: [value / counts[label] for value in values]
        for label, values in sums.items()
    }

    correct = 0
    for idx in test_idx:
        row = scaled[idx]
        predicted = min(
            centroids,
            key=lambda label: sum(
                (row[col] - centroids[label][col]) ** 2 for col in range(len(row))
            ),
        )
        correct += int(predicted == records[idx].label)
    return correct / len(test_idx)


def null_p95(
    records: Sequence[InverseLineRecord],
    trials: int = 100,
    seed: int = 41,
    feature_set: str = "inverse_shadow_4d",
) -> float:
    scores = [
        centroid_accuracy(
            records,
            seed=seed + trial,
            shuffle_train_labels=True,
            feature_set=feature_set,
        )
        for trial in range(trials)
    ]
    return sorted(scores)[int(math.ceil(0.95 * len(scores))) - 1]


def class_means(records: Sequence[InverseLineRecord]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[InverseLineRecord]] = defaultdict(list)
    for record in records:
        grouped[record.label].append(record)
    means: dict[str, dict[str, float]] = {}
    for label, items in grouped.items():
        means[label] = {
            name: sum(getattr(item, name) for item in items) / len(items)
            for name in FEATURE_NAMES
        }
    return means


def run_probe(
    n_primes: int = 10_000,
    null_trials: int = 100,
    seed: int = 41,
    out_dir: Path | None = None,
) -> dict[str, object]:
    records = build_records(n_primes=n_primes, seed=seed)
    feature_set_results = {}
    for feature_set in FEATURE_SET_NAMES:
        real_acc = centroid_accuracy(records, seed=seed, feature_set=feature_set)
        shuffled_null95 = null_p95(
            records, trials=null_trials, seed=seed, feature_set=feature_set
        )
        feature_set_results[feature_set] = {
            "centroid_accuracy": real_acc,
            "shuffle_null95": shuffled_null95,
            "margin": real_acc - shuffled_null95,
        }

    best_feature_set = max(
        feature_set_results, key=lambda name: feature_set_results[name]["margin"]
    )
    best_metrics = feature_set_results[best_feature_set]
    survives = best_metrics["centroid_accuracy"] > best_metrics["shuffle_null95"] + 0.02
    verdict = (
        "INVERSE_LINE_INDICATOR_SURVIVES_NULL"
        if survives
        else "INVERSE_LINE_COLLAPSES_TO_NULL"
    )

    summary: dict[str, object] = {
        "n_records": len(records),
        "n_primes": sum(record.label == "prime" for record in records),
        "n_wheel_composites": sum(record.label == "composite" for record in records),
        "feature_names": FEATURE_NAMES,
        "feature_set_names": FEATURE_SET_NAMES,
        "best_feature_set": best_feature_set,
        "metrics": best_metrics,
        "feature_set_results": feature_set_results,
        "class_means": class_means(records),
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": verdict,
            "survives_null": survives,
            "claim_boundary": (
                "Uses only 4D residue/neighbor factor-shadow coordinates, never factorization of n. "
                "A surviving result is an indicator on known mapped numbers, not a primality proof."
            ),
        },
    }
    if out_dir is not None:
        write_artifacts(records, summary, out_dir)
    return summary


def write_artifacts(
    records: Sequence[InverseLineRecord],
    summary: dict[str, object],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (out_dir / "inverse_line_records.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(records[0]).keys()))
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-primes", type=int, default=10_000)
    parser.add_argument("--null-trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(
        n_primes=args.n_primes,
        null_trials=args.null_trials,
        seed=args.seed,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary["metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    print(json.dumps(summary["class_means"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
