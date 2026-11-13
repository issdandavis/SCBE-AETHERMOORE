#!/usr/bin/env python3
"""Train a tiny frozen-feature probe under controlled exposure schedulers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.concept_exposure_ledger import (  # noqa: E402
    ConceptExposureLedger,
    ExposureSample,
    class_balanced_probabilities,
    exposure_manifest_sha256,
    weight_effect_receipt,
)

CAMPAIGN_SCHEMA = "scbe.concept-exposure-curriculum-campaign.v1"
HORSE_SCHEMA = "scbe.concept-exposure-curriculum-horse.v1"
DATASET_SCHEMA = "scbe.concept-exposure-shape-dataset.v1"
RESULT_SCHEMA = "scbe.concept-exposure-curriculum-result.v1"
STATUS_SCHEMA = "scbe.concept-exposure-curriculum-status.v1"
CONCEPTS = ("horizontal", "vertical", "diag_down", "diag_up", "plus", "box")
ARMS = (
    "uniform",
    "class_balanced",
    "exposure_curriculum",
    "shuffled_exposure",
    "random_fixed",
)
PRIMARY_ARM = "exposure_curriculum"
CONTROL_ARMS = tuple(arm for arm in ARMS if arm != PRIMARY_ARM)
PRIMARY_METRICS = ("accuracy", "macro_f1", "worst_concept_accuracy")
TRAIN_COUNTS = {
    "horizontal": 240,
    "vertical": 200,
    "diag_down": 120,
    "diag_up": 80,
    "plus": 60,
    "box": 40,
}
TRAIN_SOURCE = "shape-renderer-cardinal-thin-v1"
HOLDOUT_SOURCE = "shape-renderer-interstitial-thick-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(value, encoding="utf-8")
    os.replace(pending, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    with pending.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(pending, path)


def _paint(canvas: np.ndarray, row: int, column: int, thickness: int) -> None:
    radius = max(0, thickness - 1)
    for delta_row in range(-radius, radius + 1):
        for delta_column in range(-radius, radius + 1):
            target_row = row + delta_row
            target_column = column + delta_column
            if 0 <= target_row < canvas.shape[0] and 0 <= target_column < canvas.shape[1]:
                canvas[target_row, target_column] = 1.0


def _shape(concept: str, *, dx: int, dy: int, thickness: int) -> np.ndarray:
    canvas = np.zeros((16, 16), dtype=np.float32)
    center_row = 7 + dy
    center_column = 7 + dx
    span = range(-5, 6)
    if concept in {"horizontal", "plus"}:
        for offset in span:
            _paint(canvas, center_row, center_column + offset, thickness)
    if concept in {"vertical", "plus"}:
        for offset in span:
            _paint(canvas, center_row + offset, center_column, thickness)
    if concept == "diag_down":
        for offset in span:
            _paint(canvas, center_row + offset, center_column + offset, thickness)
    elif concept == "diag_up":
        for offset in span:
            _paint(canvas, center_row + offset, center_column - offset, thickness)
    elif concept == "box":
        radius = 4
        for offset in range(-radius, radius + 1):
            _paint(canvas, center_row - radius, center_column + offset, thickness)
            _paint(canvas, center_row + radius, center_column + offset, thickness)
            _paint(canvas, center_row + offset, center_column - radius, thickness)
            _paint(canvas, center_row + offset, center_column + radius, thickness)
    return canvas


@dataclass(frozen=True, slots=True)
class ShapeDataset:
    train_x: np.ndarray
    train_y: np.ndarray
    holdout_x: np.ndarray
    holdout_y: np.ndarray
    samples: tuple[ExposureSample, ...]
    manifest: dict[str, Any]

    @property
    def train_samples(self) -> tuple[ExposureSample, ...]:
        return tuple(sample for sample in self.samples if sample.split == "train")


def _payload_sha256(pixels: np.ndarray, label: int) -> str:
    digest = sha256()
    digest.update(np.ascontiguousarray(pixels, dtype=np.float32).tobytes())
    digest.update(int(label).to_bytes(2, byteorder="little", signed=False))
    return digest.hexdigest()


def build_shape_dataset(seed: int = 20261113) -> ShapeDataset:
    """Build imbalanced train and source-disjoint balanced holdout sheets."""

    rng = np.random.default_rng(seed)
    train_offsets = ((-3, -1), (-1, 3), (1, -3), (3, 1))
    holdout_offsets = ((-2, -2), (-2, 2), (0, 0), (2, -2), (2, 2))
    train_x: list[np.ndarray] = []
    train_y: list[int] = []
    holdout_x: list[np.ndarray] = []
    holdout_y: list[int] = []
    samples: list[ExposureSample] = []

    for label, concept in enumerate(CONCEPTS):
        count = TRAIN_COUNTS[concept]
        for index in range(count):
            dx, dy = train_offsets[index % len(train_offsets)]
            intensity_band = index % 2
            pixels = _shape(concept, dx=dx, dy=dy, thickness=1)
            intensity = 0.78 if intensity_band == 0 else 1.0
            pixels = np.clip(
                pixels * intensity + rng.normal(0.0, 0.08, pixels.shape),
                0.0,
                1.0,
            ).astype(np.float32)
            sample_id = f"train-{concept}-{index:04d}"
            variant_id = f"offset-{dx:+d}-{dy:+d}-thin-i{intensity_band}"
            train_x.append(pixels)
            train_y.append(label)
            samples.append(
                ExposureSample(
                    sample_id=sample_id,
                    payload_sha256=_payload_sha256(pixels, label),
                    concept_id=concept,
                    variant_id=variant_id,
                    source_family=TRAIN_SOURCE,
                    split="train",
                )
            )

        for index in range(100):
            dx, dy = holdout_offsets[index % len(holdout_offsets)]
            pixels = _shape(concept, dx=dx, dy=dy, thickness=2)
            if index % 2:
                occlusion_row = (3 * index + label) % 16
                pixels[occlusion_row, max(0, 6 + dx) : min(16, 10 + dx)] = 0.0
            pixels = np.clip(
                pixels * 0.9 + rng.normal(0.0, 0.1, pixels.shape),
                0.0,
                1.0,
            ).astype(np.float32)
            sample_id = f"holdout-{concept}-{index:04d}"
            variant_id = f"offset-{dx:+d}-{dy:+d}-thick-o{index % 2}"
            holdout_x.append(pixels)
            holdout_y.append(label)
            samples.append(
                ExposureSample(
                    sample_id=sample_id,
                    payload_sha256=_payload_sha256(pixels, label),
                    concept_id=concept,
                    variant_id=variant_id,
                    source_family=HOLDOUT_SOURCE,
                    split="holdout",
                )
            )

    train_array = np.stack(train_x)
    train_labels = np.asarray(train_y, dtype=np.int64)
    holdout_array = np.stack(holdout_x)
    holdout_labels = np.asarray(holdout_y, dtype=np.int64)
    manifest: dict[str, Any] = {
        "schema": DATASET_SCHEMA,
        "seed": seed,
        "shape": [16, 16],
        "concepts": list(CONCEPTS),
        "train_counts": dict(TRAIN_COUNTS),
        "holdout_records_per_concept": 100,
        "train_source_family": TRAIN_SOURCE,
        "holdout_source_family": HOLDOUT_SOURCE,
        "train_tensor_sha256": _array_sha256(train_array),
        "train_label_sha256": _array_sha256(train_labels),
        "holdout_tensor_sha256": _array_sha256(holdout_array),
        "holdout_label_sha256": _array_sha256(holdout_labels),
        "exposure_manifest_sha256": exposure_manifest_sha256(samples),
        "source_disjoint": TRAIN_SOURCE != HOLDOUT_SOURCE,
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
    return ShapeDataset(
        train_x=train_array,
        train_y=train_labels,
        holdout_x=holdout_array,
        holdout_y=holdout_labels,
        samples=tuple(samples),
        manifest=manifest,
    )


@dataclass(frozen=True, slots=True)
class FrozenFeatureField:
    projection: np.ndarray
    bias: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    sha256: str

    def transform(self, sheets: np.ndarray) -> np.ndarray:
        flattened = np.asarray(sheets, dtype=np.float64).reshape(len(sheets), -1)
        projected = np.tanh(flattened @ self.projection + self.bias)
        return (projected - self.mean) / self.scale


def build_frozen_feature_field(train_x: np.ndarray, *, seed: int, width: int = 96) -> FrozenFeatureField:
    rng = np.random.default_rng(100_000 + seed)
    input_width = int(np.prod(train_x.shape[1:]))
    projection = rng.normal(0.0, 1.0 / math.sqrt(input_width), (input_width, width))
    bias = rng.uniform(-0.3, 0.3, width)
    raw = np.tanh(train_x.reshape(len(train_x), -1).astype(np.float64) @ projection + bias)
    mean = raw.mean(axis=0)
    scale = raw.std(axis=0)
    scale[scale < 1e-6] = 1.0
    digest = sha256()
    for value in (projection, bias, mean, scale):
        digest.update(_array_sha256(value).encode("ascii"))
    return FrozenFeatureField(projection, bias, mean, scale, digest.hexdigest())


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=1, keepdims=True)


def _cross_entropy(probabilities: np.ndarray, labels: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0))


def _metrics(features: np.ndarray, labels: np.ndarray, weight: np.ndarray, bias: np.ndarray) -> dict[str, Any]:
    probabilities = _softmax(features @ weight + bias)
    losses = _cross_entropy(probabilities, labels)
    predictions = probabilities.argmax(axis=1)
    concept_accuracy: dict[str, float] = {}
    f1_values: list[float] = []
    for label, concept in enumerate(CONCEPTS):
        mask = labels == label
        concept_accuracy[concept] = float(np.mean(predictions[mask] == labels[mask]))
        true_positive = int(np.sum((predictions == label) & (labels == label)))
        false_positive = int(np.sum((predictions == label) & (labels != label)))
        false_negative = int(np.sum((predictions != label) & (labels == label)))
        denominator = 2 * true_positive + false_positive + false_negative
        f1_values.append(2 * true_positive / denominator if denominator else 0.0)
    confidence = probabilities.max(axis=1)
    correct = predictions == labels
    ece = 0.0
    for lower in np.linspace(0.0, 0.9, 10):
        upper = lower + 0.1
        mask = (confidence >= lower) & (confidence < upper if upper < 1.0 else confidence <= upper)
        if mask.any():
            ece += float(mask.mean()) * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    return {
        "cross_entropy": float(losses.mean()),
        "accuracy": float(correct.mean()),
        "macro_f1": float(np.mean(f1_values)),
        "worst_concept_accuracy": min(concept_accuracy.values()),
        "expected_calibration_error": ece,
        "concept_accuracy": concept_accuracy,
    }


def _shuffled_samples(samples: Sequence[ExposureSample], *, seed: int) -> tuple[ExposureSample, ...]:
    train = [sample for sample in samples if sample.split == "train"]
    concepts = np.asarray([sample.concept_id for sample in train], dtype=object)
    rng = np.random.default_rng(700_000 + seed)
    shuffled = concepts[rng.permutation(len(concepts))]
    replacements = dict(zip((sample.sample_id for sample in train), shuffled, strict=True))
    return tuple(
        ExposureSample(
            sample_id=sample.sample_id,
            payload_sha256=sample.payload_sha256,
            concept_id=str(replacements.get(sample.sample_id, sample.concept_id)),
            variant_id=sample.variant_id,
            source_family=sample.source_family,
            split=sample.split,
        )
        for sample in samples
    )


def _fixed_random_probabilities(size: int, *, seed: int, floor: float = 0.1) -> np.ndarray:
    rng = np.random.default_rng(800_000 + seed)
    scores = rng.lognormal(mean=0.0, sigma=0.8, size=size)
    median = float(np.median(scores))
    scores = np.clip(scores, median / 8.0, median * 8.0)
    probabilities = scores / float(scores.sum())
    probabilities = (1.0 - floor) * probabilities + floor / size
    return probabilities / float(probabilities.sum())


def _seed_for_arm(seed: int, arm: str) -> int:
    digest = sha256(f"{seed}:{arm}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little")


def _initial_weights(seed: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(200_000 + seed)
    return (
        rng.normal(0.0, 0.02, (width, len(CONCEPTS))).astype(np.float64),
        np.zeros(len(CONCEPTS), dtype=np.float64),
    )


def train_horse(
    dataset: ShapeDataset,
    *,
    arm: str,
    seed: int,
    steps: int,
    batch_size: int,
    learning_rate: float,
    log_every: int,
    output_dir: Path,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    result_path = output_dir / "RESULT.json"
    if result_path.exists():
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        if existing.get("schema") != HORSE_SCHEMA:
            raise ValueError(f"unexpected existing horse result: {result_path}")
        return existing

    output_dir.mkdir(parents=True, exist_ok=True)
    feature_field = build_frozen_feature_field(dataset.train_x, seed=seed)
    train_features = feature_field.transform(dataset.train_x)
    holdout_features = feature_field.transform(dataset.holdout_x)
    initial_weight, initial_bias = _initial_weights(seed, train_features.shape[1])
    weight = initial_weight.copy()
    bias = initial_bias.copy()
    initial_vector = np.concatenate((initial_weight.ravel(), initial_bias))
    initial_weight_sha256 = _array_sha256(initial_vector)

    audit_ledger = ConceptExposureLedger(dataset.samples, gradient_width=len(CONCEPTS))
    sampling_ledger = audit_ledger
    if arm == "shuffled_exposure":
        sampling_ledger = ConceptExposureLedger(
            _shuffled_samples(dataset.samples, seed=seed), gradient_width=len(CONCEPTS)
        )
    fixed_probabilities: np.ndarray | None = None
    if arm == "uniform":
        fixed_probabilities = np.full(len(dataset.train_y), 1.0 / len(dataset.train_y))
    elif arm == "class_balanced":
        fixed_probabilities = class_balanced_probabilities(dataset.samples)
    elif arm == "random_fixed":
        fixed_probabilities = _fixed_random_probabilities(len(dataset.train_y), seed=seed)

    rng = np.random.default_rng(_seed_for_arm(seed, arm))
    moment_weight = np.zeros_like(weight)
    variance_weight = np.zeros_like(weight)
    moment_bias = np.zeros_like(bias)
    variance_bias = np.zeros_like(bias)
    beta_one = 0.9
    beta_two = 0.999
    epsilon = 1e-8
    train_ids = audit_ledger.train_sample_ids
    trace_path = output_dir / "TRACE.jsonl"
    with trace_path.open("w", encoding="utf-8") as trace:
        for step in range(1, steps + 1):
            if fixed_probabilities is not None:
                probabilities = fixed_probabilities
            else:
                probabilities = sampling_ledger.sampling_probabilities()
            indices = rng.choice(len(dataset.train_y), size=batch_size, replace=True, p=probabilities)
            batch_features = train_features[indices]
            batch_labels = dataset.train_y[indices]
            predictions = _softmax(batch_features @ weight + bias)
            losses = _cross_entropy(predictions, batch_labels)
            gradient_logits = predictions.copy()
            gradient_logits[np.arange(batch_size), batch_labels] -= 1.0
            sample_ids = [train_ids[int(index)] for index in indices]
            audit_ledger.observe_batch(sample_ids, losses, gradient_logits)
            if sampling_ledger is not audit_ledger:
                sampling_ledger.observe_batch(sample_ids, losses, gradient_logits)

            gradient_weight = batch_features.T @ gradient_logits / batch_size
            gradient_bias = gradient_logits.mean(axis=0)
            moment_weight = beta_one * moment_weight + (1.0 - beta_one) * gradient_weight
            variance_weight = beta_two * variance_weight + (1.0 - beta_two) * np.square(gradient_weight)
            moment_bias = beta_one * moment_bias + (1.0 - beta_one) * gradient_bias
            variance_bias = beta_two * variance_bias + (1.0 - beta_two) * np.square(gradient_bias)
            correction_one = 1.0 - beta_one**step
            correction_two = 1.0 - beta_two**step
            weight -= (
                learning_rate * (moment_weight / correction_one) / (np.sqrt(variance_weight / correction_two) + epsilon)
            )
            bias -= learning_rate * (moment_bias / correction_one) / (np.sqrt(variance_bias / correction_two) + epsilon)

            if step == 1 or step % log_every == 0 or step == steps:
                row = {
                    "step": step,
                    "train": _metrics(train_features, dataset.train_y, weight, bias),
                    "holdout": _metrics(holdout_features, dataset.holdout_y, weight, bias),
                    "weight_delta_l2": float(np.linalg.norm(np.concatenate((weight.ravel(), bias)) - initial_vector)),
                    "total_exposures": int(audit_ledger.exposure_counts.sum()),
                    "sampling_probability_min": float(probabilities.min()),
                    "sampling_probability_max": float(probabilities.max()),
                }
                trace.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                trace.flush()
                print(
                    json.dumps(
                        {
                            "arm": arm,
                            "seed": seed,
                            "step": step,
                            "holdout_accuracy": row["holdout"]["accuracy"],
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

    final_vector = np.concatenate((weight.ravel(), bias))
    final_metrics = {
        "train": _metrics(train_features, dataset.train_y, weight, bias),
        "holdout": _metrics(holdout_features, dataset.holdout_y, weight, bias),
    }
    result: dict[str, Any] = {
        "schema": HORSE_SCHEMA,
        "arm": arm,
        "seed": seed,
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "trainable_parameters": int(weight.size + bias.size),
        "frozen_feature_sha256": feature_field.sha256,
        "frozen_feature_unchanged": True,
        "initial_weight_sha256": initial_weight_sha256,
        "metrics": final_metrics,
        "weight_effect": weight_effect_receipt(initial_vector, final_vector),
        "exposure": audit_ledger.report(),
        "sampling_exposure": (sampling_ledger.report() if sampling_ledger is not audit_ledger else None),
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "trace_sha256": _sha256_file(trace_path),
        "authority": {
            "tool_dispatch": "DISABLED",
            "promotion": "NOT_AUTHORIZED",
            "partial_unfreeze": "NONE",
        },
    }
    result["result_sha256"] = _canonical_sha256(result)
    _atomic_npz(output_dir / "WEIGHTS.npz", weight=weight, bias=bias)
    _atomic_json(result_path, result)
    return result


def _mean_std(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "sample_std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
    }


def _aggregate(horses: Sequence[Mapping[str, Any]], seeds: Sequence[int]) -> dict[str, Any]:
    by_arm = {arm: [row for row in horses if row["arm"] == arm] for arm in ARMS}
    metrics: dict[str, Any] = {}
    for arm, rows in by_arm.items():
        if not rows:
            continue
        metrics[arm] = {
            metric: _mean_std([float(row["metrics"]["holdout"][metric]) for row in rows])
            for metric in (
                *PRIMARY_METRICS,
                "cross_entropy",
                "expected_calibration_error",
            )
        }
    complete_surface = all(len(by_arm[arm]) == len(seeds) for arm in ARMS)
    enough_seeds = len(seeds) >= 3
    comparisons: dict[str, Any] = {}
    all_pass = complete_surface and enough_seeds
    if PRIMARY_ARM in metrics:
        for control in CONTROL_ARMS:
            if control not in metrics:
                all_pass = False
                continue
            comparisons[control] = {}
            for metric in PRIMARY_METRICS:
                candidate = metrics[PRIMARY_ARM][metric]
                baseline = metrics[control][metric]
                delta = candidate["mean"] - baseline["mean"]
                pooled_sd = math.sqrt((candidate["sample_std"] ** 2 + baseline["sample_std"] ** 2) / 2.0)
                threshold = 2.0 * pooled_sd
                passed = delta > 0.0 and delta > threshold
                comparisons[control][metric] = {
                    "delta": delta,
                    "pooled_sd": pooled_sd,
                    "two_pooled_sd": threshold,
                    "pass": passed,
                }
                all_pass = all_pass and passed
    else:
        all_pass = False
    return {
        "metrics": metrics,
        "comparisons": comparisons,
        "complete_control_surface": complete_surface,
        "enough_seeds": enough_seeds,
        "selection_candidate": all_pass,
        "verdict": "MECHANICS_SELECTION_CANDIDATE" if all_pass else "NO_SELECTION",
    }


def _market_report(aggregate: Mapping[str, Any], seeds: Sequence[int]) -> str:
    lines = [
        "# Concept-exposure curriculum market report",
        "",
        "Evidence class: `SYNTHETIC_SOURCE_DISJOINT_MECHANICS_ONLY`. No promotion or unfreeze.",
        "",
        f"Seeds: {', '.join(str(seed) for seed in seeds)}",
        "",
        "| Arm | Accuracy | Macro-F1 | Worst concept | CE | ECE |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in ARMS:
        if arm not in aggregate["metrics"]:
            continue
        row = aggregate["metrics"][arm]
        lines.append(
            "| "
            + " | ".join(
                (
                    arm,
                    f"{row['accuracy']['mean']:.4f} +/- {row['accuracy']['sample_std']:.4f}",
                    f"{row['macro_f1']['mean']:.4f} +/- {row['macro_f1']['sample_std']:.4f}",
                    (
                        f"{row['worst_concept_accuracy']['mean']:.4f} +/- "
                        f"{row['worst_concept_accuracy']['sample_std']:.4f}"
                    ),
                    f"{row['cross_entropy']['mean']:.4f}",
                    f"{row['expected_calibration_error']['mean']:.4f}",
                )
            )
            + " |"
        )
    lines.extend(("", f"Verdict: `{aggregate['verdict']}`", ""))
    return "\n".join(lines)


def run_campaign(
    output_dir: Path,
    *,
    seeds: Sequence[int],
    arms: Sequence[str],
    steps: int,
    batch_size: int,
    learning_rate: float,
    log_every: int,
) -> dict[str, Any]:
    if min(steps, batch_size, log_every) < 1 or learning_rate <= 0.0:
        raise ValueError("training arguments must be positive")
    if len(seeds) != len(set(seeds)) or not seeds:
        raise ValueError("seeds must be unique and non-empty")
    if len(arms) != len(set(arms)) or not arms or any(arm not in ARMS for arm in arms):
        raise ValueError("arms must be unique known values")
    output = output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    dataset = build_shape_dataset()
    _atomic_json(output / "DATASET_MANIFEST.json", dataset.manifest)
    preregistration = REPO_ROOT / "docs/research/CONCEPT_EXPOSURE_CURRICULUM_PREREGISTRATION_20261113.md"
    implementation = Path(__file__).resolve()
    ledger_implementation = REPO_ROOT / "python/scbe/concept_exposure_ledger.py"
    campaign: dict[str, Any] = {
        "schema": CAMPAIGN_SCHEMA,
        "seeds": list(seeds),
        "arms": list(arms),
        "primary_arm": PRIMARY_ARM,
        "required_controls": list(CONTROL_ARMS),
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "log_every": log_every,
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "implementation_sha256": _sha256_file(implementation),
        "ledger_implementation_sha256": _sha256_file(ledger_implementation),
        "preregistration_sha256": _sha256_file(preregistration),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    campaign["campaign_sha256"] = _canonical_sha256(campaign)
    campaign["created_at_utc"] = _utc_now()
    existing_campaign = output / "CAMPAIGN.json"
    if existing_campaign.exists():
        prior = json.loads(existing_campaign.read_text(encoding="utf-8"))
        if prior.get("campaign_sha256") != campaign["campaign_sha256"]:
            raise ValueError("output directory already belongs to another campaign")
        campaign = prior
    else:
        _atomic_json(existing_campaign, campaign)
    existing_result = output / "RESULT.json"
    if existing_result.exists():
        prior_result = json.loads(existing_result.read_text(encoding="utf-8"))
        if prior_result.get("schema") != RESULT_SCHEMA:
            raise ValueError("output directory contains an unknown result schema")
        if prior_result.get("campaign", {}).get("campaign_sha256") != campaign["campaign_sha256"]:
            raise ValueError("completed result does not match the campaign")
        return prior_result

    horses: list[dict[str, Any]] = []
    for seed in seeds:
        seed_initial_hashes: set[str] = set()
        seed_feature_hashes: set[str] = set()
        for arm in arms:
            result = train_horse(
                dataset,
                arm=arm,
                seed=seed,
                steps=steps,
                batch_size=batch_size,
                learning_rate=learning_rate,
                log_every=log_every,
                output_dir=output / "horses" / f"{arm}-seed-{seed}",
            )
            horses.append(result)
            seed_initial_hashes.add(str(result["initial_weight_sha256"]))
            seed_feature_hashes.add(str(result["frozen_feature_sha256"]))
        if len(seed_initial_hashes) != 1 or len(seed_feature_hashes) != 1:
            raise RuntimeError("arms did not share the same seed initialization")

    aggregate = _aggregate(horses, seeds)
    trainable_counts = {int(row["trainable_parameters"]) for row in horses}
    integrity = {
        "equal_trainable_parameters": len(trainable_counts) == 1,
        "all_frozen_features_unchanged": all(row["frozen_feature_unchanged"] for row in horses),
        "all_weights_changed": all(row["weight_effect"]["changed_scalars"] > 0 for row in horses),
        "source_disjoint": bool(dataset.manifest["source_disjoint"]),
        "all_exposure_counts_exact": all(row["exposure"]["total_exposures"] == steps * batch_size for row in horses),
    }
    state = (
        "COMPLETE_MECHANICS_SELECTION_CANDIDATE"
        if aggregate["selection_candidate"] and all(integrity.values())
        else "COMPLETE_MECHANICS_NO_SELECTION"
    )
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "completed_at_utc": _utc_now(),
        "campaign": campaign,
        "horses": horses,
        "aggregate": aggregate,
        "integrity": integrity,
        "state": state,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    result["result_sha256"] = _canonical_sha256(result)
    _atomic_json(output / "RESULT.json", result)
    report = _market_report(aggregate, seeds)
    _atomic_text(output / "MARKET_REPORT.md", report)
    status = {
        "schema": STATUS_SCHEMA,
        "state": state,
        "completed_horses": len(horses),
        "total_horses": len(seeds) * len(arms),
        "result_sha256": _sha256_file(output / "RESULT.json"),
        "market_report_sha256": _sha256_file(output / "MARKET_REPORT.md"),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    _atomic_json(output / "STATUS.json", status)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--arm", action="append", choices=ARMS, dest="arms")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--log-every", type=int, default=100)
    args = parser.parse_args()
    result = run_campaign(
        args.output_dir,
        seeds=tuple(args.seeds or (11, 29, 47)),
        arms=tuple(args.arms or ARMS),
        steps=args.steps,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        log_every=args.log_every,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "verdict": result["aggregate"]["verdict"],
                "result_sha256": result["result_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
