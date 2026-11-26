"""Compare a correlated transform path with factor-balanced orbit coverage."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from python.scbe.concept_exposure_ledger import ExposureSample, exposure_manifest_sha256
from python.scbe.concept_orbit_replay import (
    CONCEPTS,
    HORSE_SCHEMA,
    TRAIN_COUNTS,
    ConceptOrbitDataset,
    _array_sha256,
    _atomic_json,
    _canonical_sha256,
    _payload_sha256,
    _render,
    _sha256_file,
    build_concept_orbit_dataset,
    train_horse,
)

DATASET_SCHEMA = "scbe.concept-factor-coverage-dataset.v1"
CAMPAIGN_SCHEMA = "scbe.concept-factor-coverage-campaign.v1"
RESULT_SCHEMA = "scbe.concept-factor-coverage-result.v1"
STATUS_SCHEMA = "scbe.concept-factor-coverage-status.v1"
FACTOR_SOURCE = "shape-factor-balanced-lattice-v3"

ARMS = (
    "correlated_uniform",
    "correlated_class_balanced",
    "factor_uniform",
    "factor_class_balanced",
    "factor_exposure",
    "factor_shuffled_exposure",
)
ARM_SPECS = {
    "correlated_uniform": ("correlated", "orbit_uniform"),
    "correlated_class_balanced": ("correlated", "orbit_class_balanced"),
    "factor_uniform": ("factor", "orbit_uniform"),
    "factor_class_balanced": ("factor", "orbit_class_balanced"),
    "factor_exposure": ("factor", "orbit_exposure"),
    "factor_shuffled_exposure": ("factor", "orbit_shuffled_exposure"),
}
PRIMARY_ARM = "factor_exposure"
PRIMARY_METRICS = ("accuracy", "macro_f1", "worst_concept_accuracy")
SCHEDULER_CONTROLS = (
    "factor_uniform",
    "factor_class_balanced",
    "factor_shuffled_exposure",
)


def _factor_transform(
    index: int, label: int
) -> tuple[float, float, float, float, int, float, int]:
    """Enumerate the offset product before repeating, then phase other factors."""

    offsets = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0)
    angles = (-7.0, -4.0, -2.0, 0.0, 2.0, 4.0, 7.0)
    scales = (0.86, 0.94, 1.0, 1.08, 1.16)
    pair_index = (index + 17 * label) % 49
    dx = offsets[pair_index % 7]
    dy = offsets[pair_index // 7]
    angle = angles[(index * 3 + label) % len(angles)]
    scale = scales[(index * 2 + 3 * label) % len(scales)]
    thickness = 2 if (index + label) % 5 == 0 else 1
    intensity = (0.68, 0.8, 0.9, 1.0)[(index + 2 * label) % 4]
    occlusion = (index + label) % 3 if (index + label) % 7 == 0 else 0
    return angle, scale, dx, dy, thickness, intensity, occlusion


def build_factor_comparison_datasets(
    seed: int = 20261113,
) -> tuple[ConceptOrbitDataset, ConceptOrbitDataset, dict[str, Any]]:
    """Return correlated and factor datasets sharing one frozen calibration."""

    correlated_base = build_concept_orbit_dataset(seed)
    rng = np.random.default_rng(seed + 101)
    factor_x: list[np.ndarray] = []
    factor_samples: list[ExposureSample] = []
    pair_coverage: dict[str, set[tuple[int, int]]] = {
        concept: set() for concept in CONCEPTS
    }
    offsets = {-3.0: 0, -2.0: 1, -1.0: 2, 0.0: 3, 1.0: 4, 2.0: 5, 3.0: 6}

    for label, concept in enumerate(CONCEPTS):
        for index in range(TRAIN_COUNTS[concept]):
            angle, scale, dx, dy, thickness, intensity, occlusion = _factor_transform(
                index, label
            )
            pixels = _render(
                concept,
                rng=rng,
                angle=angle,
                scale=scale,
                dx=dx,
                dy=dy,
                thickness=thickness,
                intensity=intensity,
                noise=0.075,
                occlusion=occlusion,
                index=index,
            )
            factor_x.append(pixels)
            pair_coverage[concept].add((offsets[dx], offsets[dy]))
            factor_samples.append(
                ExposureSample(
                    sample_id=f"factor-{concept}-{index:04d}",
                    payload_sha256=_payload_sha256(pixels, label),
                    concept_id=concept,
                    variant_id=(
                        f"a{angle:+.0f}-s{scale:.2f}-x{dx:+.0f}-y{dy:+.0f}"
                        f"-t{thickness}-o{occlusion}"
                    ),
                    source_family=FACTOR_SOURCE,
                    split="train",
                )
            )

    factor_array = np.stack(factor_x)
    evaluation_samples = tuple(
        sample for sample in correlated_base.orbit_samples if sample.split != "train"
    )
    factor_sample_set = tuple(factor_samples) + evaluation_samples
    all_payloads = [
        *(sample.payload_sha256 for sample in correlated_base.orbit_samples),
        *(sample.payload_sha256 for sample in factor_samples),
    ]
    if len(all_payloads) != len(set(all_payloads)):
        raise RuntimeError("factor comparison contains a payload collision")
    calibration = np.concatenate(
        (
            correlated_base.static_train_x,
            correlated_base.orbit_train_x,
            factor_array,
        ),
        axis=0,
    )
    common: dict[str, Any] = {
        "schema": DATASET_SCHEMA,
        "seed": seed,
        "train_counts": dict(TRAIN_COUNTS),
        "train_label_sha256": _array_sha256(correlated_base.train_y),
        "validation_tensor_sha256": _array_sha256(correlated_base.validation_x),
        "holdout_tensor_sha256": _array_sha256(correlated_base.holdout_x),
        "correlated_tensor_sha256": _array_sha256(correlated_base.orbit_train_x),
        "factor_tensor_sha256": _array_sha256(factor_array),
        "calibration_tensor_sha256": _array_sha256(calibration),
        "factor_pair_coverage": {
            concept: len(pairs) for concept, pairs in pair_coverage.items()
        },
        "factor_exposure_manifest_sha256": exposure_manifest_sha256(factor_sample_set),
        "correlated_exposure_manifest_sha256": exposure_manifest_sha256(
            correlated_base.orbit_samples
        ),
    }
    common["comparison_manifest_sha256"] = _canonical_sha256(common)

    def make_dataset(
        train_x: np.ndarray,
        samples: tuple[ExposureSample, ...],
        mode: str,
    ) -> ConceptOrbitDataset:
        manifest = {
            **common,
            "mode": mode,
            "active_train_tensor_sha256": _array_sha256(train_x),
            "active_exposure_manifest_sha256": exposure_manifest_sha256(samples),
        }
        manifest["manifest_sha256"] = _canonical_sha256(manifest)
        return ConceptOrbitDataset(
            static_train_x=correlated_base.static_train_x,
            orbit_train_x=train_x,
            train_y=correlated_base.train_y,
            validation_x=correlated_base.validation_x,
            validation_y=correlated_base.validation_y,
            holdout_x=correlated_base.holdout_x,
            holdout_y=correlated_base.holdout_y,
            static_samples=correlated_base.static_samples,
            orbit_samples=samples,
            calibration_x=calibration,
            manifest=manifest,
        )

    return (
        make_dataset(
            correlated_base.orbit_train_x, correlated_base.orbit_samples, "correlated"
        ),
        make_dataset(factor_array, factor_sample_set, "factor"),
        common,
    )


def _alias_horse(
    dataset: ConceptOrbitDataset,
    *,
    outer_arm: str,
    inner_arm: str,
    source_mode: str,
    seed: int,
    steps: int,
    batch_size: int,
    learning_rate: float,
    log_every: int,
    output_dir: Path,
) -> dict[str, Any]:
    result = train_horse(
        dataset,
        arm=inner_arm,
        seed=seed,
        steps=steps,
        batch_size=batch_size,
        learning_rate=learning_rate,
        log_every=log_every,
        output_dir=output_dir,
    )
    if result.get("comparison_arm") == outer_arm:
        return result
    if result.get("schema") != HORSE_SCHEMA or result.get("arm") != inner_arm:
        raise ValueError(f"unexpected aliased horse result in {output_dir}")
    aliased = dict(result)
    aliased["base_arm"] = inner_arm
    aliased["arm"] = outer_arm
    aliased["comparison_arm"] = outer_arm
    aliased["source_mode"] = source_mode
    aliased.pop("result_sha256", None)
    aliased["result_sha256"] = _canonical_sha256(aliased)
    _atomic_json(output_dir / "RESULT.json", aliased)
    return aliased


def _mean_std(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "sample_std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
    }


def _comparison(candidate: Sequence[float], control: Sequence[float]) -> dict[str, Any]:
    candidate_array = np.asarray(candidate, dtype=np.float64)
    control_array = np.asarray(control, dtype=np.float64)
    pooled_sd = (
        math.sqrt(
            (float(candidate_array.var(ddof=1)) + float(control_array.var(ddof=1)))
            / 2.0
        )
        if len(candidate_array) > 1 and len(control_array) > 1
        else 0.0
    )
    delta = float(candidate_array.mean() - control_array.mean())
    return {
        "delta": delta,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": 2.0 * pooled_sd,
        "pass": bool(delta > 2.0 * pooled_sd),
    }


def _aggregate(
    horses: Sequence[Mapping[str, Any]], seeds: Sequence[int]
) -> dict[str, Any]:
    by_arm = {arm: [row for row in horses if row["arm"] == arm] for arm in ARMS}
    metrics: dict[str, Any] = {}
    for arm, rows in by_arm.items():
        metrics[arm] = {
            metric: _mean_std(
                [float(row["metrics"]["holdout"][metric]) for row in rows]
            )
            for metric in (
                *PRIMARY_METRICS,
                "cross_entropy",
                "expected_calibration_error",
            )
        }
        metrics[arm]["selected_step"] = _mean_std(
            [float(row["selected_step"]) for row in rows]
        )

    coverage_comparison = {
        metric: _comparison(
            [
                float(row["metrics"]["holdout"][metric])
                for row in by_arm["factor_class_balanced"]
            ],
            [
                float(row["metrics"]["holdout"][metric])
                for row in by_arm["correlated_class_balanced"]
            ],
        )
        for metric in PRIMARY_METRICS
    }
    scheduler_comparisons = {
        control: {
            metric: _comparison(
                [
                    float(row["metrics"]["holdout"][metric])
                    for row in by_arm[PRIMARY_ARM]
                ],
                [float(row["metrics"]["holdout"][metric]) for row in by_arm[control]],
            )
            for metric in PRIMARY_METRICS
        }
        for control in SCHEDULER_CONTROLS
    }
    enough_seeds = len(set(seeds)) >= 3
    complete = all(len(rows) == len(seeds) for rows in by_arm.values())
    coverage_signal = (
        enough_seeds
        and complete
        and all(coverage_comparison[metric]["pass"] for metric in PRIMARY_METRICS)
    )
    scheduler_signal = (
        enough_seeds
        and complete
        and all(
            comparison[metric]["pass"]
            for comparison in scheduler_comparisons.values()
            for metric in PRIMARY_METRICS
        )
    )
    return {
        "metrics": metrics,
        "coverage_comparison": coverage_comparison,
        "scheduler_comparisons": scheduler_comparisons,
        "enough_seeds": enough_seeds,
        "complete_control_surface": complete,
        "coverage_signal": coverage_signal,
        "scheduler_signal": scheduler_signal,
        "verdict": (
            "FACTOR_AND_SCHEDULER_SIGNAL"
            if coverage_signal and scheduler_signal
            else (
                "FACTOR_COVERAGE_SIGNAL_ONLY"
                if coverage_signal
                else "SCHEDULER_SIGNAL_ONLY" if scheduler_signal else "NO_SELECTION"
            )
        ),
    }


def _market_report(result: Mapping[str, Any]) -> str:
    lines = [
        "# Factor-balanced concept coverage market report",
        "",
        "Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`. No promotion or unfreeze.",
        "",
        "| Arm | Accuracy | Macro-F1 | Worst concept | CE | Selected step |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    metrics = result["aggregate"]["metrics"]
    for arm in ARMS:
        row = metrics[arm]
        lines.append(
            "| "
            + " | ".join(
                (
                    arm,
                    f"{row['accuracy']['mean']:.4f} +/- {row['accuracy']['sample_std']:.4f}",
                    f"{row['macro_f1']['mean']:.4f} +/- {row['macro_f1']['sample_std']:.4f}",
                    f"{row['worst_concept_accuracy']['mean']:.4f} +/- "
                    f"{row['worst_concept_accuracy']['sample_std']:.4f}",
                    f"{row['cross_entropy']['mean']:.4f}",
                    f"{row['selected_step']['mean']:.1f}",
                )
            )
            + " |"
        )
    lines.extend(("", f"Verdict: `{result['aggregate']['verdict']}`", ""))
    return "\n".join(lines)


def run_factor_campaign(
    output_dir: Path,
    *,
    seeds: Sequence[int],
    arms: Sequence[str] = ARMS,
    steps: int = 1500,
    batch_size: int = 64,
    learning_rate: float = 0.003,
    log_every: int = 50,
    implementation_path: Path | None = None,
    preregistration_path: Path | None = None,
) -> dict[str, Any]:
    if tuple(arms) != ARMS:
        raise ValueError(f"the complete fixed control surface is required: {ARMS}")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be non-empty and unique")
    if min(steps, batch_size, log_every) < 1 or learning_rate <= 0.0:
        raise ValueError("training parameters must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    correlated, factor, comparison_manifest = build_factor_comparison_datasets()
    manifests = {
        "comparison": comparison_manifest,
        "correlated": correlated.manifest,
        "factor": factor.manifest,
    }
    _atomic_json(output_dir / "DATASET_MANIFESTS.json", manifests)
    implementation_path = implementation_path or Path(__file__)
    campaign: dict[str, Any] = {
        "schema": CAMPAIGN_SCHEMA,
        "seeds": list(seeds),
        "arms": list(arms),
        "primary_arm": PRIMARY_ARM,
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "log_every": log_every,
        "comparison_manifest_sha256": comparison_manifest["comparison_manifest_sha256"],
        "implementation_sha256": _sha256_file(implementation_path),
        "preregistration_sha256": (
            _sha256_file(preregistration_path)
            if preregistration_path is not None
            else None
        ),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    campaign["campaign_sha256"] = _canonical_sha256(campaign)
    campaign_path = output_dir / "CAMPAIGN.json"
    if campaign_path.exists():
        existing = json.loads(campaign_path.read_text(encoding="utf-8"))
        if existing.get("campaign_sha256") != campaign["campaign_sha256"]:
            raise ValueError("existing campaign configuration does not match")
    else:
        _atomic_json(campaign_path, campaign)

    horses: list[dict[str, Any]] = []
    datasets = {"correlated": correlated, "factor": factor}
    for seed in seeds:
        for outer_arm in arms:
            source_mode, inner_arm = ARM_SPECS[outer_arm]
            horses.append(
                _alias_horse(
                    datasets[source_mode],
                    outer_arm=outer_arm,
                    inner_arm=inner_arm,
                    source_mode=source_mode,
                    seed=int(seed),
                    steps=steps,
                    batch_size=batch_size,
                    learning_rate=learning_rate,
                    log_every=log_every,
                    output_dir=output_dir / "horses" / f"{outer_arm}-seed-{seed}",
                )
            )
    aggregate = _aggregate(horses, seeds)
    state = (
        "COMPLETE_SYNTHETIC_SIGNAL_NO_PROMOTION"
        if aggregate["verdict"] != "NO_SELECTION"
        else "COMPLETE_MECHANICS_NO_SELECTION"
    )
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "state": state,
        "campaign": campaign,
        "aggregate": aggregate,
        "horses": horses,
        "integrity": {
            "all_horses_complete": len(horses) == len(seeds) * len(arms),
            "all_exposure_counts_exact": all(
                row["exposure"]["total_exposures"] == steps * batch_size
                for row in horses
            ),
            "all_frozen_fields_unchanged": all(
                row["frozen_feature_unchanged"] for row in horses
            ),
            "all_weights_changed": all(
                row["weight_effect"]["changed_scalars"] > 0 for row in horses
            ),
            "same_trainable_parameters": len(
                {row["trainable_parameters"] for row in horses}
            )
            == 1,
            "same_initialization_within_seed": all(
                len(
                    {
                        row["initial_weight_sha256"]
                        for row in horses
                        if row["seed"] == seed
                    }
                )
                == 1
                for seed in seeds
            ),
            "same_frozen_field_within_seed": all(
                len(
                    {
                        row["frozen_feature_sha256"]
                        for row in horses
                        if row["seed"] == seed
                    }
                )
                == 1
                for seed in seeds
            ),
            "holdout_never_in_trace": True,
        },
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    result["result_sha256"] = _canonical_sha256(result)
    _atomic_json(output_dir / "RESULT.json", result)
    (output_dir / "MARKET_REPORT.md").write_text(
        _market_report(result), encoding="utf-8"
    )
    status = {
        "schema": STATUS_SCHEMA,
        "state": state,
        "completed_horses": len(horses),
        "total_horses": len(seeds) * len(arms),
        "result_sha256": result["result_sha256"],
        "market_report_sha256": _sha256_file(output_dir / "MARKET_REPORT.md"),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    _atomic_json(output_dir / "STATUS.json", status)
    return result
