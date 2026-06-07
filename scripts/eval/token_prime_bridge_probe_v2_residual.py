"""Token-prime bridge probe v2: residual structure beyond wheel admissibility.

v1 showed that prime-specific features beat a smooth monotone-index sidecar on
`gap_next_bucket`. The honest next gate is stricter: does anything remain after
we give the model the known wheel/admissibility coordinates?

This probe compares:

    monotone_index
    monotone_index + wheel_admissibility
    monotone_index + wheel_admissibility + residual_backwards_features

The headline metric is not "full beats null"; it is:

    delta_full_minus_wheel

and that delta must beat a paired shuffled-label delta null. If it does not,
the v1 signal is useful known geometry, not new residual structure.

Run:
    python scripts/eval/token_prime_bridge_probe_v2_residual.py
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

from scripts.eval.token_prime_bridge_probe import RNG_SEED, _phase  # noqa: E402
from scripts.eval.token_prime_bridge_probe_v1 import (  # noqa: E402
    DEFAULT_NULLS,
    DEFAULT_PRIME_COUNT,
    ClassificationMetrics,
    NullClassificationMetrics,
    _build_real_prime_records,
    _class_distribution,
    _evaluate_classifier,
    _majority_floor,
    _max_abs_feature_target_corr,
    _monotone_index_features,
    _null_metrics,
    _past_prime_composite_phase,
)
from src.geoseal_cli import _small_factor_pressure  # noqa: E402


@dataclass(frozen=True)
class PairedDeltaNullMetrics:
    delta_mean: float
    delta_p95: float
    delta_max: float
    p_value: float
    runs: int


@dataclass(frozen=True)
class PrimeBridgeV2ResidualResult:
    schema_version: str
    verdict: str
    dataset: dict[str, int | str]
    split: dict[str, int | float]
    target: str
    feature_dim: dict[str, int]
    class_distribution: dict[str, int]
    majority_floor: ClassificationMetrics
    monotone_index_score: ClassificationMetrics
    wheel_admissibility_score: ClassificationMetrics
    full_residual_score: ClassificationMetrics
    full_shuffled_null: NullClassificationMetrics
    paired_delta_null: PairedDeltaNullMetrics
    delta_wheel_minus_monotone: float
    delta_full_minus_wheel: float
    leakage_audit: dict[str, float | bool | list[str]]
    control_contract: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _wheel_admissibility_features(
    records: Sequence[dict[str, int | float]],
) -> tuple[np.ndarray, list[str]]:
    rows: list[list[float]] = []
    names: list[str] = []
    for record in records:
        value = int(record["prime"])
        row: list[float] = []
        row_names: list[str] = []
        for modulus in (6, 30, 210):
            sin_phase, cos_phase = _phase(value, modulus)
            row.extend([sin_phase, cos_phase])
            row_names.extend([f"wheel_mod_{modulus}_sin", f"wheel_mod_{modulus}_cos"])
        row.append((value % 30) / 29.0)
        row_names.append("wheel_residue_lane_mod30_norm")
        if not names:
            names = row_names
        rows.append(row)
    return np.asarray(rows, dtype=float), names


def _residual_backwards_features(
    records: Sequence[dict[str, int | float]],
) -> tuple[np.ndarray, list[str]]:
    rows: list[list[float]] = []
    names = [
        "gap_prev",
        "gap_prev_over_logp",
        "past_composite_fraction",
        "pressure_p_minus_1",
        "pressure_p_plus_1",
    ]
    for record in records:
        value = int(record["prime"])
        gap_prev = int(record["gap_prev"])
        log_value = math.log(value)
        rows.append(
            [
                gap_prev,
                gap_prev / log_value,
                _past_prime_composite_phase(value),
                _small_factor_pressure(value - 1) / 12.0,
                _small_factor_pressure(value + 1) / 12.0,
            ]
        )
    return np.asarray(rows, dtype=float), names


def _pad_zeros(features: np.ndarray, width: int) -> np.ndarray:
    if features.shape[1] > width:
        raise ValueError("cannot pad features to a smaller width")
    if features.shape[1] == width:
        return features
    return np.hstack(
        [
            features,
            np.zeros((features.shape[0], width - features.shape[1]), dtype=float),
        ]
    )


def _paired_delta_null(
    full_features: np.ndarray,
    wheel_features: np.ndarray,
    labels: np.ndarray,
    train_idx: Sequence[int],
    test_idx: Sequence[int],
    real_delta: float,
    null_runs: int,
    seed: int,
) -> PairedDeltaNullMetrics:
    rng = np.random.default_rng(seed)
    values: list[float] = []
    train_count = len(train_idx)
    for _ in range(null_runs):
        permutation = rng.permutation(train_count)
        full_score = _evaluate_classifier(
            full_features,
            labels,
            train_idx,
            test_idx,
            train_label_permutation=permutation,
        ).balanced_accuracy
        wheel_score = _evaluate_classifier(
            wheel_features,
            labels,
            train_idx,
            test_idx,
            train_label_permutation=permutation,
        ).balanced_accuracy
        values.append(full_score - wheel_score)
    arr = np.asarray(values, dtype=float)
    p_value = (1.0 + float(np.sum(arr >= real_delta))) / (null_runs + 1.0)
    return PairedDeltaNullMetrics(
        delta_mean=float(np.mean(arr)),
        delta_p95=float(np.quantile(arr, 0.95)),
        delta_max=float(np.max(arr)),
        p_value=float(p_value),
        runs=null_runs,
    )


def run_probe(
    prime_count: int = DEFAULT_PRIME_COUNT,
    null_runs: int = DEFAULT_NULLS,
    train_fraction: float = 0.65,
    seed: int = RNG_SEED,
) -> PrimeBridgeV2ResidualResult:
    if null_runs < 40:
        raise ValueError("null_runs must be >= 40")
    if not 0.2 <= train_fraction <= 0.8:
        raise ValueError("train_fraction must be between 0.2 and 0.8")

    records = _build_real_prime_records(prime_count)
    labels = np.asarray([int(record["bucket"]) for record in records], dtype=int)

    rng = np.random.default_rng(seed + 11)
    indices = np.arange(len(records))
    rng.shuffle(indices)
    train_size = int(len(records) * train_fraction)
    train_idx = indices[:train_size].tolist()
    test_idx = indices[train_size:].tolist()

    wheel_features, wheel_names = _wheel_admissibility_features(records)
    residual_features, residual_names = _residual_backwards_features(records)
    monotone_features, monotone_names = _monotone_index_features(
        records,
        width=wheel_features.shape[1] + residual_features.shape[1],
    )

    full_width = (
        monotone_features.shape[1]
        + wheel_features.shape[1]
        + residual_features.shape[1]
    )
    monotone_block = _pad_zeros(monotone_features, full_width)
    wheel_block = np.hstack(
        [monotone_features, wheel_features, np.zeros_like(residual_features)]
    )
    full_block = np.hstack([monotone_features, wheel_features, residual_features])
    assert monotone_block.shape[1] == wheel_block.shape[1] == full_block.shape[1]
    assert "gap_next" not in wheel_names
    assert "gap_next" not in residual_names

    monotone_score = _evaluate_classifier(monotone_block, labels, train_idx, test_idx)
    wheel_score = _evaluate_classifier(wheel_block, labels, train_idx, test_idx)
    full_score = _evaluate_classifier(full_block, labels, train_idx, test_idx)
    majority_score = _majority_floor(labels, test_idx)
    full_null = _null_metrics(
        full_block,
        labels,
        train_idx,
        test_idx,
        full_score.balanced_accuracy,
        null_runs,
        seed + 12,
    )

    delta_wheel_minus_monotone = (
        wheel_score.balanced_accuracy - monotone_score.balanced_accuracy
    )
    delta_full_minus_wheel = (
        full_score.balanced_accuracy - wheel_score.balanced_accuracy
    )
    delta_null = _paired_delta_null(
        full_block,
        wheel_block,
        labels,
        train_idx,
        test_idx,
        delta_full_minus_wheel,
        null_runs,
        seed + 13,
    )

    residual_beats_wheel = delta_full_minus_wheel > max(0.0, delta_null.delta_p95)
    full_beats_null = full_score.balanced_accuracy > full_null.balanced_accuracy_p95
    full_beats_floor = full_score.balanced_accuracy > majority_score.balanced_accuracy
    if residual_beats_wheel and full_beats_null and full_beats_floor:
        verdict = "RESIDUAL_STRUCTURE_BEYOND_WHEEL"
    elif full_beats_null and not residual_beats_wheel:
        verdict = "WHEEL_ADMISSIBILITY_EXPLAINS_SIGNAL"
    else:
        verdict = "RESIDUAL_STRUCTURE_NOT_SUPPORTED"

    full_names = monotone_names + wheel_names + residual_names
    wheel_names_padded = (
        monotone_names
        + wheel_names
        + [f"zero_residual_pad_{i}" for i in range(residual_features.shape[1])]
    )
    return PrimeBridgeV2ResidualResult(
        schema_version="token_prime_bridge_probe_v2_residual",
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
            "seed": seed + 11,
            "train_fraction": train_fraction,
        },
        target="gap_next_bucket",
        feature_dim={
            "monotone_index": monotone_block.shape[1],
            "wheel_admissibility": wheel_block.shape[1],
            "full_residual": full_block.shape[1],
        },
        class_distribution=_class_distribution(labels),
        majority_floor=majority_score,
        monotone_index_score=monotone_score,
        wheel_admissibility_score=wheel_score,
        full_residual_score=full_score,
        full_shuffled_null=full_null,
        paired_delta_null=delta_null,
        delta_wheel_minus_monotone=float(delta_wheel_minus_monotone),
        delta_full_minus_wheel=float(delta_full_minus_wheel),
        leakage_audit={
            "dims_equal": monotone_block.shape[1]
            == wheel_block.shape[1]
            == full_block.shape[1],
            "target_name_absent_from_full_features": "gap_next" not in full_names,
            "wheel_baseline_has_no_residual_columns": not any(
                name.startswith(("gap_prev", "past_", "pressure_"))
                for name in wheel_names_padded
            ),
            "max_feature_target_corr_monotone": _max_abs_feature_target_corr(
                monotone_block, labels
            ),
            "max_feature_target_corr_wheel": _max_abs_feature_target_corr(
                wheel_block, labels
            ),
            "max_feature_target_corr_full": _max_abs_feature_target_corr(
                full_block, labels
            ),
            "monotone_feature_names": monotone_names,
            "wheel_feature_names": wheel_names,
            "residual_feature_names": residual_names,
        },
        control_contract={
            "monotone_index": "smooth density/index coordinates only",
            "wheel_admissibility": "monotone coordinates plus mod 6/30/210 residue admissibility",
            "full_residual": "wheel_admissibility plus backward gap/phase/neighbor-pressure features",
            "headline": "delta_full_minus_wheel",
            "pass_condition": "full residual arm beats wheel baseline by more than paired shuffled-label delta p95",
        },
    )


def _print_summary(result: PrimeBridgeV2ResidualResult) -> None:
    print(result.verdict)
    print(
        f"N={result.dataset['prime_count']} train={result.split['train']} "
        f"test={result.split['test']} nulls={result.full_shuffled_null.runs}"
    )
    print(f"class_distribution={result.class_distribution}")
    print(
        "monotone_index: "
        f"bal_acc={result.monotone_index_score.balanced_accuracy:.4f} "
        f"raw_acc={result.monotone_index_score.raw_accuracy:.4f}"
    )
    print(
        "wheel_admissibility: "
        f"bal_acc={result.wheel_admissibility_score.balanced_accuracy:.4f} "
        f"raw_acc={result.wheel_admissibility_score.raw_accuracy:.4f}"
    )
    print(
        "full_residual: "
        f"bal_acc={result.full_residual_score.balanced_accuracy:.4f} "
        f"raw_acc={result.full_residual_score.raw_accuracy:.4f} "
        f"null95={result.full_shuffled_null.balanced_accuracy_p95:.4f} "
        f"p={result.full_shuffled_null.p_value:.4f}"
    )
    print(
        "delta_wheel_minus_monotone="
        f"{result.delta_wheel_minus_monotone:.4f} "
        "delta_full_minus_wheel="
        f"{result.delta_full_minus_wheel:.4f} "
        "paired_delta_p95="
        f"{result.paired_delta_null.delta_p95:.4f} "
        f"paired_delta_p={result.paired_delta_null.p_value:.4f}"
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
        default=Path("artifacts/eval/token_prime_bridge_probe_v2_residual.json"),
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
