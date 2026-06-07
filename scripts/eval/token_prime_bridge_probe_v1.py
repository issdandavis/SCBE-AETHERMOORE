"""Token-prime bridge probe v1: real-prime structure vs monotone-index baseline.

v0 was a wiring positive control. It recovered an injected smooth relation:

    synthetic token sidecar -> prime_index/log(prime)

That does not prove "prime" carries useful structure. This v1 gate implements
``docs/eval/token_prime_bridge_probe_v1_gate_spec.md``:

    source A: prime-specific residual features over real consecutive primes
    source B: equally wide monotone-index features
    target:   gap_next_bucket {small, normal, large}
    metric:   balanced accuracy, not retrieval rank

Headline metric:

    delta_prime_minus_monotone

Beating a shuffled-pair null is necessary but not sufficient. Prime structure
must beat an equally rich monotone-index sidecar by more than null noise.

Run:
    python scripts/eval/token_prime_bridge_probe_v1.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.eval.token_prime_bridge_probe import (  # noqa: E402
    RNG_SEED,
    _first_primes,
    _phase,
    _ridge_bridge,
    _train_test_split,
    _zscore_fit,
)
from src.geoseal_cli import _small_factor_pressure  # noqa: E402

DEFAULT_PRIME_COUNT = 4000
DEFAULT_NULLS = 400
CLASSES = (0, 1, 2)
CLASS_NAMES = {0: "small", 1: "normal", 2: "large"}


@dataclass(frozen=True)
class ClassificationMetrics:
    balanced_accuracy: float
    raw_accuracy: float
    per_class_recall: dict[str, float]
    confusion: list[list[int]]


@dataclass(frozen=True)
class NullClassificationMetrics:
    balanced_accuracy_mean: float
    balanced_accuracy_p95: float
    balanced_accuracy_max: float
    p_value: float
    runs: int


@dataclass(frozen=True)
class PrimeBridgeV1Result:
    schema_version: str
    verdict: str
    dataset: dict[str, int | str]
    split: dict[str, int | float]
    target: str
    feature_dim: dict[str, int]
    class_distribution: dict[str, int]
    majority_floor: ClassificationMetrics
    prime_structure_score: ClassificationMetrics
    monotone_index_score: ClassificationMetrics
    prime_shuffled_null: NullClassificationMetrics
    monotone_shuffled_null: NullClassificationMetrics
    delta_prime_minus_monotone: float
    delta_prime_minus_null: float
    null_noise_margin: float
    leakage_audit: dict[str, float | bool | list[str]]
    control_contract: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _is_prime_trial(value: int) -> bool:
    if value < 2:
        return False
    if value in (2, 3):
        return True
    if value % 2 == 0:
        return False
    factor = 3
    while factor * factor <= value:
        if value % factor == 0:
            return False
        factor += 2
    return True


def _past_prime_composite_phase(center: int, radius: int = 30) -> float:
    start = max(1, center - radius)
    end = center - 1
    prime_count = 0
    composite_count = 0
    for value in range(start, end + 1):
        if _is_prime_trial(value):
            prime_count += 1
        elif value > 1:
            composite_count += 1
    total = prime_count + composite_count
    return composite_count / total if total else 0.0


def _gap_bucket(gap_next: int, value: int) -> int:
    expected = math.log(value)
    if gap_next < 0.75 * expected:
        return 0
    if gap_next <= 1.5 * expected:
        return 1
    return 2


def _build_real_prime_records(prime_count: int) -> list[dict[str, int | float]]:
    if prime_count < 500:
        raise ValueError("prime_count must be >= 500 for a stable real-prime split")
    primes = _first_primes(prime_count + 2)
    records: list[dict[str, int | float]] = []
    for row in range(prime_count):
        # Skip p_1=2 so every record has a previous and next prime.
        prime_index = row + 2
        value = primes[prime_index - 1]
        previous_prime = primes[prime_index - 2]
        next_prime = primes[prime_index]
        gap_prev = value - previous_prime
        gap_next = next_prime - value
        records.append(
            {
                "row": row,
                "prime_index": prime_index,
                "prime": value,
                "previous_prime": previous_prime,
                "next_prime": next_prime,
                "gap_prev": gap_prev,
                "gap_next": gap_next,
                "bucket": _gap_bucket(gap_next, value),
            }
        )
    return records


def _prime_structure_features(
    records: Sequence[dict[str, int | float]],
) -> tuple[np.ndarray, list[str]]:
    rows: list[list[float]] = []
    names: list[str] = []
    for record in records:
        value = int(record["prime"])
        gap_prev = int(record["gap_prev"])
        log_value = math.log(value)
        row: list[float] = []
        row_names: list[str] = []

        for modulus in (6, 30, 210):
            sin_phase, cos_phase = _phase(value, modulus)
            row.extend([sin_phase, cos_phase])
            row_names.extend([f"prime_mod_{modulus}_sin", f"prime_mod_{modulus}_cos"])

        row.append((value % 30) / 29.0)
        row_names.append("residue_lane_mod30_norm")

        row.extend(
            [
                gap_prev,
                gap_prev / log_value,
                _past_prime_composite_phase(value),
                _small_factor_pressure(value - 1) / 12.0,
                _small_factor_pressure(value + 1) / 12.0,
            ]
        )
        row_names.extend(
            [
                "gap_prev",
                "gap_prev_over_logp",
                "past_composite_fraction",
                "pressure_p_minus_1",
                "pressure_p_plus_1",
            ]
        )

        if not names:
            names = row_names
        rows.append(row)
    return np.asarray(rows, dtype=float), names


def _monotone_index_features(
    records: Sequence[dict[str, int | float]], width: int
) -> tuple[np.ndarray, list[str]]:
    max_index = max(int(record["prime_index"]) for record in records)
    rows: list[list[float]] = []
    for record in records:
        index = int(record["prime_index"])
        x = index / max_index
        features = [
            x,
            math.log(index) / math.log(max_index),
            x * x,
            math.sqrt(x),
            x**3,
            x**4,
        ]
        names = [
            "rank_norm",
            "log_rank_norm",
            "rank_norm_sq",
            "sqrt_rank_norm",
            "rank_norm_cu",
            "rank_norm_4",
        ]
        for k in (17, 29, 43, 61):
            features.extend([math.sin(index / k), math.cos(index / k)])
            names.extend([f"sin_i_over_{k}", f"cos_i_over_{k}"])
        power = 5
        while len(features) < width:
            features.append(x**power)
            names.append(f"rank_norm_pow_{power}")
            power += 1
        rows.append(features[:width])
    return np.asarray(rows, dtype=float), names[:width]


def _one_hot_labels(labels: np.ndarray) -> np.ndarray:
    out = np.zeros((len(labels), len(CLASSES)), dtype=float)
    for row, label in enumerate(labels):
        out[row, int(label)] = 1.0
    return out


def _balanced_accuracy(
    predicted: np.ndarray, labels: np.ndarray
) -> ClassificationMetrics:
    confusion = [[0 for _ in CLASSES] for _ in CLASSES]
    for truth, pred in zip(labels, predicted):
        confusion[int(truth)][int(pred)] += 1

    recalls: dict[str, float] = {}
    recall_values: list[float] = []
    for class_id in CLASSES:
        total = sum(confusion[class_id])
        recall = confusion[class_id][class_id] / total if total else 0.0
        recalls[CLASS_NAMES[class_id]] = float(recall)
        recall_values.append(float(recall))
    raw_accuracy = float(np.mean(predicted == labels)) if len(labels) else 0.0
    return ClassificationMetrics(
        balanced_accuracy=float(sum(recall_values) / len(CLASSES)),
        raw_accuracy=raw_accuracy,
        per_class_recall=recalls,
        confusion=confusion,
    )


def _evaluate_classifier(
    features: np.ndarray,
    labels: np.ndarray,
    train_idx: Sequence[int],
    test_idx: Sequence[int],
    *,
    alpha: float = 1e-2,
    train_label_permutation: np.ndarray | None = None,
) -> ClassificationMetrics:
    train_features = features[list(train_idx)]
    train_labels = labels[list(train_idx)]
    if train_label_permutation is not None:
        train_labels = train_labels[train_label_permutation]
    train_targets = _one_hot_labels(train_labels)

    feature_mean, feature_scale = _zscore_fit(train_features)
    train_z = (train_features - feature_mean) / feature_scale
    bridge = _ridge_bridge(train_z, train_targets, alpha=alpha)

    test_z = (features[list(test_idx)] - feature_mean) / feature_scale
    scores = test_z @ bridge
    predicted = np.argmax(scores, axis=1)
    return _balanced_accuracy(predicted, labels[list(test_idx)])


def _null_metrics(
    features: np.ndarray,
    labels: np.ndarray,
    train_idx: Sequence[int],
    test_idx: Sequence[int],
    real_score: float,
    null_runs: int,
    seed: int,
) -> NullClassificationMetrics:
    rng = np.random.default_rng(seed)
    values: list[float] = []
    train_count = len(train_idx)
    for _ in range(null_runs):
        permutation = rng.permutation(train_count)
        values.append(
            _evaluate_classifier(
                features,
                labels,
                train_idx,
                test_idx,
                train_label_permutation=permutation,
            ).balanced_accuracy
        )
    arr = np.asarray(values, dtype=float)
    p_value = (1.0 + float(np.sum(arr >= real_score))) / (null_runs + 1.0)
    return NullClassificationMetrics(
        balanced_accuracy_mean=float(np.mean(arr)),
        balanced_accuracy_p95=float(np.quantile(arr, 0.95)),
        balanced_accuracy_max=float(np.max(arr)),
        p_value=float(p_value),
        runs=null_runs,
    )


def _majority_floor(
    labels: np.ndarray, test_idx: Sequence[int]
) -> ClassificationMetrics:
    train_labels = labels[
        [idx for idx in range(len(labels)) if idx not in set(test_idx)]
    ]
    values, counts = np.unique(train_labels, return_counts=True)
    majority = int(values[int(np.argmax(counts))])
    predicted = np.asarray([majority] * len(test_idx), dtype=int)
    return _balanced_accuracy(predicted, labels[list(test_idx)])


def _max_abs_feature_target_corr(features: np.ndarray, labels: np.ndarray) -> float:
    target = labels.astype(float)
    target_std = float(np.std(target))
    if target_std < 1e-12:
        return 0.0
    max_corr = 0.0
    for col in range(features.shape[1]):
        feature = features[:, col]
        if float(np.std(feature)) < 1e-12:
            continue
        corr = float(np.corrcoef(feature, target)[0, 1])
        if math.isfinite(corr):
            max_corr = max(max_corr, abs(corr))
    return max_corr


def _class_distribution(labels: np.ndarray) -> dict[str, int]:
    return {
        CLASS_NAMES[class_id]: int(np.sum(labels == class_id)) for class_id in CLASSES
    }


def run_probe(
    prime_count: int = DEFAULT_PRIME_COUNT,
    null_runs: int = DEFAULT_NULLS,
    train_fraction: float = 0.65,
    seed: int = RNG_SEED,
) -> PrimeBridgeV1Result:
    if null_runs < 40:
        raise ValueError("null_runs must be >= 40")
    if not 0.2 <= train_fraction <= 0.8:
        raise ValueError("train_fraction must be between 0.2 and 0.8")

    records = _build_real_prime_records(prime_count)
    labels = np.asarray([int(record["bucket"]) for record in records], dtype=int)
    train_idx, test_idx = _train_test_split(len(records), train_fraction, seed=seed + 1)

    prime_features, prime_names = _prime_structure_features(records)
    monotone_features, monotone_names = _monotone_index_features(
        records, width=prime_features.shape[1]
    )
    assert prime_features.shape[1] == monotone_features.shape[1]
    assert "gap_next" not in prime_names
    assert all(
        "prime" not in name and "gap" not in name and "pressure" not in name
        for name in monotone_names
    )

    prime_score = _evaluate_classifier(prime_features, labels, train_idx, test_idx)
    monotone_score = _evaluate_classifier(
        monotone_features, labels, train_idx, test_idx
    )
    majority_score = _majority_floor(labels, test_idx)
    prime_null = _null_metrics(
        prime_features,
        labels,
        train_idx,
        test_idx,
        prime_score.balanced_accuracy,
        null_runs,
        seed + 2,
    )
    monotone_null = _null_metrics(
        monotone_features,
        labels,
        train_idx,
        test_idx,
        monotone_score.balanced_accuracy,
        null_runs,
        seed + 3,
    )

    delta_prime_minus_monotone = (
        prime_score.balanced_accuracy - monotone_score.balanced_accuracy
    )
    delta_prime_minus_null = (
        prime_score.balanced_accuracy - prime_null.balanced_accuracy_mean
    )
    null_noise_margin = (
        monotone_null.balanced_accuracy_p95 - monotone_null.balanced_accuracy_mean
    )

    prime_beats_monotone = delta_prime_minus_monotone > null_noise_margin
    prime_beats_null = prime_score.balanced_accuracy > prime_null.balanced_accuracy_p95
    prime_beats_floor = prime_score.balanced_accuracy > majority_score.balanced_accuracy
    if prime_beats_monotone and prime_beats_null and prime_beats_floor:
        verdict = "PRIME_STRUCTURE_ADDS_SIGNAL"
    elif prime_beats_null and not prime_beats_monotone:
        verdict = "PRIME_BEATS_NULL_NOT_MONOTONE_POSITIVE_CONTROL_ONLY"
    else:
        verdict = "PRIME_STRUCTURE_NOT_SUPPORTED"

    return PrimeBridgeV1Result(
        schema_version="token_prime_bridge_probe_v1",
        verdict=verdict,
        dataset={
            "source": "first_N_real_consecutive_primes",
            "prime_count": prime_count,
            "sample_count": len(records),
            "first_prime": int(records[0]["prime"]),
            "last_prime": int(records[-1]["prime"]),
        },
        split={
            "train": len(train_idx),
            "test": len(test_idx),
            "seed": seed + 1,
            "train_fraction": train_fraction,
        },
        target="gap_next_bucket",
        feature_dim={
            "prime": prime_features.shape[1],
            "monotone": monotone_features.shape[1],
        },
        class_distribution=_class_distribution(labels),
        majority_floor=majority_score,
        prime_structure_score=prime_score,
        monotone_index_score=monotone_score,
        prime_shuffled_null=prime_null,
        monotone_shuffled_null=monotone_null,
        delta_prime_minus_monotone=float(delta_prime_minus_monotone),
        delta_prime_minus_null=float(delta_prime_minus_null),
        null_noise_margin=float(null_noise_margin),
        leakage_audit={
            "dims_equal": prime_features.shape[1] == monotone_features.shape[1],
            "target_name_absent_from_prime_features": "gap_next" not in prime_names,
            "monotone_has_no_prime_derived_columns": all(
                "prime" not in name and "gap" not in name and "pressure" not in name
                for name in monotone_names
            ),
            "max_feature_target_corr_prime": _max_abs_feature_target_corr(
                prime_features, labels
            ),
            "max_feature_target_corr_monotone": _max_abs_feature_target_corr(
                monotone_features, labels
            ),
            "prime_feature_names": prime_names,
            "monotone_feature_names": monotone_names,
        },
        control_contract={
            "prime_structure": "residue/gap_prev/past_phase/neighbor_pressure features over real primes",
            "monotone_index": "equal-width smooth index/log/power/sin-cos features with no prime lookup",
            "target": "gap_next_bucket, excluded from all input columns",
            "metric": "balanced accuracy over small/normal/large buckets",
            "headline": "delta_prime_minus_monotone",
            "pass_condition": "prime beats monotone by more than monotone shuffled-null p95 spread",
        },
    )


def _print_summary(result: PrimeBridgeV1Result) -> None:
    print(result.verdict)
    print(
        f"N={result.dataset['prime_count']} train={result.split['train']} "
        f"test={result.split['test']} nulls={result.prime_shuffled_null.runs}"
    )
    print(f"class_distribution={result.class_distribution}")
    print(
        "prime_structure: "
        f"bal_acc={result.prime_structure_score.balanced_accuracy:.4f} "
        f"raw_acc={result.prime_structure_score.raw_accuracy:.4f} "
        f"null95={result.prime_shuffled_null.balanced_accuracy_p95:.4f} "
        f"p={result.prime_shuffled_null.p_value:.4f}"
    )
    print(
        "monotone_index: "
        f"bal_acc={result.monotone_index_score.balanced_accuracy:.4f} "
        f"raw_acc={result.monotone_index_score.raw_accuracy:.4f} "
        f"null95={result.monotone_shuffled_null.balanced_accuracy_p95:.4f}"
    )
    print(
        "majority_floor: "
        f"bal_acc={result.majority_floor.balanced_accuracy:.4f} "
        f"raw_acc={result.majority_floor.raw_accuracy:.4f}"
    )
    print(
        "delta_prime_minus_monotone="
        f"{result.delta_prime_minus_monotone:.4f} "
        f"null_noise_margin={result.null_noise_margin:.4f}"
    )
    print(f"leakage_audit={result.leakage_audit}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prime-count", type=int, default=DEFAULT_PRIME_COUNT)
    parser.add_argument("--null-runs", type=int, default=DEFAULT_NULLS)
    parser.add_argument("--train-fraction", type=float, default=0.65)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("artifacts/eval/token_prime_bridge_probe_v1.json"),
    )
    args = parser.parse_args()

    result = run_probe(
        prime_count=args.prime_count,
        null_runs=args.null_runs,
        train_fraction=args.train_fraction,
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    _print_summary(result)
    print(f"artifact={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
