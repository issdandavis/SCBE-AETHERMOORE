"""Source-disjoint concept-orbit replay around a frozen sheet feature field.

The experiment in this module is deliberately small and non-authoritative.  It
tests whether repeated *transformed* views build a more transferable concept
region than repeated fixed pixels, and whether the concept-exposure scheduler
adds value beyond ordinary class balancing over the same orbit.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    ExposureSample,
    class_balanced_probabilities,
    exposure_manifest_sha256,
    weight_effect_receipt,
)

DATASET_SCHEMA = "scbe.concept-orbit-dataset.v1"
CAMPAIGN_SCHEMA = "scbe.concept-orbit-campaign.v1"
HORSE_SCHEMA = "scbe.concept-orbit-horse.v1"
RESULT_SCHEMA = "scbe.concept-orbit-result.v1"
STATUS_SCHEMA = "scbe.concept-orbit-status.v1"

CONCEPTS = ("horizontal", "vertical", "diag_down", "diag_up", "plus", "box")
TRAIN_COUNTS = {
    "horizontal": 240,
    "vertical": 200,
    "diag_down": 120,
    "diag_up": 80,
    "plus": 60,
    "box": 40,
}
ARMS = (
    "static_uniform",
    "static_class_balanced",
    "orbit_uniform",
    "orbit_class_balanced",
    "orbit_exposure",
    "orbit_shuffled_exposure",
)
PRIMARY_ARM = "orbit_exposure"
REQUIRED_CONTROLS = tuple(arm for arm in ARMS if arm != PRIMARY_ARM)
PRIMARY_METRICS = ("accuracy", "macro_f1", "worst_concept_accuracy")

STATIC_TRAIN_SOURCE = "shape-static-cardinal-v2"
ORBIT_TRAIN_SOURCE = "shape-orbit-affine-v2"
VALIDATION_SOURCE = "shape-validation-phase-v2"
HOLDOUT_SOURCE = "shape-holdout-obscured-v2"


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


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    with pending.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(pending, path)


def _paint(canvas: np.ndarray, row: int, column: int, thickness: int) -> None:
    radius = max(0, thickness - 1)
    for delta_row in range(-radius, radius + 1):
        for delta_column in range(-radius, radius + 1):
            target_row = row + delta_row
            target_column = column + delta_column
            if 0 <= target_row < 16 and 0 <= target_column < 16:
                canvas[target_row, target_column] = 1.0


def _shape(concept: str, *, thickness: int = 1) -> np.ndarray:
    canvas = np.zeros((16, 16), dtype=np.float64)
    center = 7
    span = range(-5, 6)
    if concept in {"horizontal", "plus"}:
        for offset in span:
            _paint(canvas, center, center + offset, thickness)
    if concept in {"vertical", "plus"}:
        for offset in span:
            _paint(canvas, center + offset, center, thickness)
    if concept == "diag_down":
        for offset in span:
            _paint(canvas, center + offset, center + offset, thickness)
    elif concept == "diag_up":
        for offset in span:
            _paint(canvas, center + offset, center - offset, thickness)
    elif concept == "box":
        radius = 4
        for offset in range(-radius, radius + 1):
            _paint(canvas, center - radius, center + offset, thickness)
            _paint(canvas, center + radius, center + offset, thickness)
            _paint(canvas, center + offset, center - radius, thickness)
            _paint(canvas, center + offset, center + radius, thickness)
    return canvas


def _affine_sheet(
    sheet: np.ndarray,
    *,
    angle_degrees: float,
    scale: float,
    dx: float,
    dy: float,
) -> np.ndarray:
    """Apply a deterministic inverse-mapped bilinear affine transform."""

    if scale <= 0.0:
        raise ValueError("scale must be positive")
    rows, columns = np.indices((16, 16), dtype=np.float64)
    center = 7.5
    target_x = columns - center - dx
    target_y = rows - center - dy
    radians = math.radians(angle_degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    source_x = (cosine * target_x + sine * target_y) / scale + center
    source_y = (-sine * target_x + cosine * target_y) / scale + center

    x0 = np.floor(source_x).astype(np.int64)
    y0 = np.floor(source_y).astype(np.int64)
    x1 = x0 + 1
    y1 = y0 + 1
    wx = source_x - x0
    wy = source_y - y0
    result = np.zeros((16, 16), dtype=np.float64)
    for xs, ys, weight in (
        (x0, y0, (1.0 - wx) * (1.0 - wy)),
        (x1, y0, wx * (1.0 - wy)),
        (x0, y1, (1.0 - wx) * wy),
        (x1, y1, wx * wy),
    ):
        valid = (xs >= 0) & (xs < 16) & (ys >= 0) & (ys < 16)
        result[valid] += sheet[ys[valid], xs[valid]] * weight[valid]
    return np.clip(result, 0.0, 1.0)


def _occlude(sheet: np.ndarray, *, kind: int, index: int) -> np.ndarray:
    result = sheet.copy()
    if kind == 1:
        row = 3 + (index * 5) % 10
        result[row, 5:11] *= 0.15
    elif kind == 2:
        column = 3 + (index * 7) % 10
        result[5:11, column] *= 0.15
    return result


def _render(
    concept: str,
    *,
    rng: np.random.Generator,
    angle: float,
    scale: float,
    dx: float,
    dy: float,
    thickness: int,
    intensity: float,
    noise: float,
    occlusion: int,
    index: int,
) -> np.ndarray:
    pixels = _affine_sheet(
        _shape(concept, thickness=thickness),
        angle_degrees=angle,
        scale=scale,
        dx=dx,
        dy=dy,
    )
    pixels = _occlude(pixels, kind=occlusion, index=index)
    pixels = np.clip(
        pixels * intensity + rng.normal(0.0, noise, pixels.shape), 0.0, 1.0
    )
    return pixels.astype(np.float32)


def _payload_sha256(pixels: np.ndarray, label: int) -> str:
    digest = sha256()
    digest.update(np.ascontiguousarray(pixels, dtype=np.float32).tobytes())
    digest.update(int(label).to_bytes(2, byteorder="little", signed=False))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ConceptOrbitDataset:
    static_train_x: np.ndarray
    orbit_train_x: np.ndarray
    train_y: np.ndarray
    validation_x: np.ndarray
    validation_y: np.ndarray
    holdout_x: np.ndarray
    holdout_y: np.ndarray
    static_samples: tuple[ExposureSample, ...]
    orbit_samples: tuple[ExposureSample, ...]
    calibration_x: np.ndarray
    manifest: dict[str, Any]

    def train_x(self, arm: str) -> np.ndarray:
        return self.static_train_x if arm.startswith("static_") else self.orbit_train_x

    def samples(self, arm: str) -> tuple[ExposureSample, ...]:
        return self.static_samples if arm.startswith("static_") else self.orbit_samples


def _training_transform(
    index: int,
) -> tuple[float, float, float, float, int, float, int]:
    angles = (-7.0, -4.0, -2.0, 0.0, 2.0, 4.0, 7.0)
    scales = (0.86, 0.94, 1.0, 1.08, 1.16)
    offsets = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0)
    angle = angles[index % len(angles)]
    scale = scales[(index // 2) % len(scales)]
    dx = offsets[(index * 3 + 1) % len(offsets)]
    dy = offsets[(index * 5 + 2) % len(offsets)]
    thickness = 2 if index % 5 == 0 else 1
    intensity = (0.68, 0.8, 0.9, 1.0)[index % 4]
    occlusion = index % 3 if index % 7 == 0 else 0
    return angle, scale, dx, dy, thickness, intensity, occlusion


def build_concept_orbit_dataset(seed: int = 20261113) -> ConceptOrbitDataset:
    """Create fixed and transformed training sheets plus sealed evaluation sets."""

    static_rng = np.random.default_rng(seed)
    orbit_rng = np.random.default_rng(seed + 1)
    validation_rng = np.random.default_rng(seed + 2)
    holdout_rng = np.random.default_rng(seed + 3)
    static_x: list[np.ndarray] = []
    orbit_x: list[np.ndarray] = []
    train_y: list[int] = []
    static_train_samples: list[ExposureSample] = []
    orbit_train_samples: list[ExposureSample] = []
    validation_x: list[np.ndarray] = []
    validation_y: list[int] = []
    validation_samples: list[ExposureSample] = []
    holdout_x: list[np.ndarray] = []
    holdout_y: list[int] = []
    holdout_samples: list[ExposureSample] = []
    static_offsets = ((-3.0, -1.0), (-1.0, 3.0), (1.0, -3.0), (3.0, 1.0))

    for label, concept in enumerate(CONCEPTS):
        for index in range(TRAIN_COUNTS[concept]):
            dx, dy = static_offsets[index % len(static_offsets)]
            intensity = 0.78 if index % 2 == 0 else 1.0
            static_pixels = _render(
                concept,
                rng=static_rng,
                angle=0.0,
                scale=1.0,
                dx=dx,
                dy=dy,
                thickness=1,
                intensity=intensity,
                noise=0.08,
                occlusion=0,
                index=index,
            )
            transform = _training_transform(index + label * 11)
            angle, scale, orbit_dx, orbit_dy, thickness, orbit_intensity, occlusion = (
                transform
            )
            orbit_pixels = _render(
                concept,
                rng=orbit_rng,
                angle=angle,
                scale=scale,
                dx=orbit_dx,
                dy=orbit_dy,
                thickness=thickness,
                intensity=orbit_intensity,
                noise=0.075,
                occlusion=occlusion,
                index=index,
            )
            train_y.append(label)
            static_x.append(static_pixels)
            orbit_x.append(orbit_pixels)
            static_train_samples.append(
                ExposureSample(
                    sample_id=f"static-{concept}-{index:04d}",
                    payload_sha256=_payload_sha256(static_pixels, label),
                    concept_id=concept,
                    variant_id=f"fixed-{int(dx):+d}-{int(dy):+d}-i{index % 2}",
                    source_family=STATIC_TRAIN_SOURCE,
                    split="train",
                )
            )
            orbit_train_samples.append(
                ExposureSample(
                    sample_id=f"orbit-{concept}-{index:04d}",
                    payload_sha256=_payload_sha256(orbit_pixels, label),
                    concept_id=concept,
                    variant_id=(
                        f"a{angle:+.0f}-s{scale:.2f}-x{orbit_dx:+.0f}-y{orbit_dy:+.0f}"
                        f"-t{thickness}-o{occlusion}"
                    ),
                    source_family=ORBIT_TRAIN_SOURCE,
                    split="train",
                )
            )

        validation_angles = (-6.0, -3.0, 1.0, 3.0, 6.0)
        validation_offsets = (
            (-2.0, 0.0),
            (0.0, -2.0),
            (0.0, 2.0),
            (2.0, 0.0),
            (0.0, 0.0),
        )
        for index in range(80):
            dx, dy = validation_offsets[index % len(validation_offsets)]
            angle = validation_angles[(index + label) % len(validation_angles)]
            scale = (0.9, 1.04, 1.12)[index % 3]
            pixels = _render(
                concept,
                rng=validation_rng,
                angle=angle,
                scale=scale,
                dx=dx,
                dy=dy,
                thickness=2 if index % 4 == 0 else 1,
                intensity=(0.74, 0.88, 1.0)[index % 3],
                noise=0.09,
                occlusion=1 if index % 6 == 0 else 0,
                index=index,
            )
            validation_x.append(pixels)
            validation_y.append(label)
            validation_samples.append(
                ExposureSample(
                    sample_id=f"validation-{concept}-{index:04d}",
                    payload_sha256=_payload_sha256(pixels, label),
                    concept_id=concept,
                    variant_id=f"validation-phase-{index % 30:02d}",
                    source_family=VALIDATION_SOURCE,
                    split="anchor",
                )
            )

        holdout_angles = (-5.0, -1.0, 5.0)
        holdout_offsets = (
            (-2.0, -2.0),
            (-2.0, 2.0),
            (0.0, 0.0),
            (2.0, -2.0),
            (2.0, 2.0),
        )
        for index in range(100):
            dx, dy = holdout_offsets[index % len(holdout_offsets)]
            pixels = _render(
                concept,
                rng=holdout_rng,
                angle=holdout_angles[(index + 2 * label) % len(holdout_angles)],
                scale=(0.92, 1.1)[index % 2],
                dx=dx,
                dy=dy,
                thickness=2,
                intensity=(0.72, 0.86, 1.0)[index % 3],
                noise=0.1,
                occlusion=1 + (index % 2),
                index=index,
            )
            holdout_x.append(pixels)
            holdout_y.append(label)
            holdout_samples.append(
                ExposureSample(
                    sample_id=f"holdout-{concept}-{index:04d}",
                    payload_sha256=_payload_sha256(pixels, label),
                    concept_id=concept,
                    variant_id=f"holdout-obscured-{index % 30:02d}",
                    source_family=HOLDOUT_SOURCE,
                    split="holdout",
                )
            )

    static_array = np.stack(static_x)
    orbit_array = np.stack(orbit_x)
    labels = np.asarray(train_y, dtype=np.int64)
    validation_array = np.stack(validation_x)
    validation_labels = np.asarray(validation_y, dtype=np.int64)
    holdout_array = np.stack(holdout_x)
    holdout_labels = np.asarray(holdout_y, dtype=np.int64)
    calibration = np.concatenate((static_array, orbit_array), axis=0)
    static_samples = tuple(static_train_samples + validation_samples + holdout_samples)
    orbit_samples = tuple(orbit_train_samples + validation_samples + holdout_samples)
    all_digests = [
        *[sample.payload_sha256 for sample in static_train_samples],
        *[sample.payload_sha256 for sample in orbit_train_samples],
        *[sample.payload_sha256 for sample in validation_samples],
        *[sample.payload_sha256 for sample in holdout_samples],
    ]
    if len(all_digests) != len(set(all_digests)):
        raise RuntimeError("concept-orbit dataset contains a payload collision")
    manifest: dict[str, Any] = {
        "schema": DATASET_SCHEMA,
        "seed": seed,
        "shape": [16, 16],
        "concepts": list(CONCEPTS),
        "train_counts": dict(TRAIN_COUNTS),
        "validation_records_per_concept": 80,
        "holdout_records_per_concept": 100,
        "source_families": {
            "static_train": STATIC_TRAIN_SOURCE,
            "orbit_train": ORBIT_TRAIN_SOURCE,
            "validation": VALIDATION_SOURCE,
            "holdout": HOLDOUT_SOURCE,
        },
        "source_disjoint": len(
            {STATIC_TRAIN_SOURCE, ORBIT_TRAIN_SOURCE, VALIDATION_SOURCE, HOLDOUT_SOURCE}
        )
        == 4,
        "static_train_tensor_sha256": _array_sha256(static_array),
        "orbit_train_tensor_sha256": _array_sha256(orbit_array),
        "train_label_sha256": _array_sha256(labels),
        "validation_tensor_sha256": _array_sha256(validation_array),
        "validation_label_sha256": _array_sha256(validation_labels),
        "holdout_tensor_sha256": _array_sha256(holdout_array),
        "holdout_label_sha256": _array_sha256(holdout_labels),
        "static_exposure_manifest_sha256": exposure_manifest_sha256(static_samples),
        "orbit_exposure_manifest_sha256": exposure_manifest_sha256(orbit_samples),
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
    return ConceptOrbitDataset(
        static_train_x=static_array,
        orbit_train_x=orbit_array,
        train_y=labels,
        validation_x=validation_array,
        validation_y=validation_labels,
        holdout_x=holdout_array,
        holdout_y=holdout_labels,
        static_samples=static_samples,
        orbit_samples=orbit_samples,
        calibration_x=calibration,
        manifest=manifest,
    )


def _geometric_features(sheets: np.ndarray) -> np.ndarray:
    values = np.asarray(sheets, dtype=np.float64)
    row_mass = values.mean(axis=2)
    column_mass = values.mean(axis=1)
    anti_values = values[:, :, ::-1]
    diagonal = np.stack(
        [
            np.diagonal(values, offset=offset, axis1=1, axis2=2).mean(axis=1)
            for offset in range(-15, 16)
        ],
        axis=1,
    )
    anti_diagonal = np.stack(
        [
            np.diagonal(anti_values, offset=offset, axis1=1, axis2=2).mean(axis=1)
            for offset in range(-15, 16)
        ],
        axis=1,
    )
    pooled = (
        values.reshape(len(values), 4, 4, 4, 4)
        .mean(axis=(2, 4))
        .reshape(len(values), -1)
    )
    rows, columns = np.indices((16, 16), dtype=np.float64)
    mass = values.sum(axis=(1, 2)) + 1e-8
    center_x = (values * columns).sum(axis=(1, 2)) / mass
    center_y = (values * rows).sum(axis=(1, 2)) / mass
    x_delta = columns[None, :, :] - center_x[:, None, None]
    y_delta = rows[None, :, :] - center_y[:, None, None]
    moment_xx = (values * x_delta * x_delta).sum(axis=(1, 2)) / mass
    moment_yy = (values * y_delta * y_delta).sum(axis=(1, 2)) / mass
    moment_xy = (values * x_delta * y_delta).sum(axis=(1, 2)) / mass
    moments = np.stack(
        (
            mass / 256.0,
            center_x / 15.0,
            center_y / 15.0,
            moment_xx / 64.0,
            moment_yy / 64.0,
            moment_xy / 64.0,
        ),
        axis=1,
    )
    return np.concatenate(
        (row_mass, column_mass, diagonal, anti_diagonal, pooled, moments), axis=1
    )


@dataclass(frozen=True, slots=True)
class FrozenSheetFeatureField:
    projection: np.ndarray
    bias: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    sha256: str

    def _raw(self, sheets: np.ndarray) -> np.ndarray:
        flattened = np.asarray(sheets, dtype=np.float64).reshape(len(sheets), -1)
        random_features = np.tanh(flattened @ self.projection + self.bias)
        return np.concatenate((random_features, _geometric_features(sheets)), axis=1)

    def transform(self, sheets: np.ndarray) -> np.ndarray:
        return (self._raw(sheets) - self.mean) / self.scale


def build_frozen_sheet_feature_field(
    calibration_x: np.ndarray,
    *,
    seed: int,
    random_width: int = 64,
) -> FrozenSheetFeatureField:
    rng = np.random.default_rng(100_000 + seed)
    input_width = int(np.prod(calibration_x.shape[1:]))
    projection = rng.normal(
        0.0, 1.0 / math.sqrt(input_width), (input_width, random_width)
    )
    bias = rng.uniform(-0.3, 0.3, random_width)
    flattened = calibration_x.reshape(len(calibration_x), -1).astype(np.float64)
    raw = np.concatenate(
        (np.tanh(flattened @ projection + bias), _geometric_features(calibration_x)),
        axis=1,
    )
    mean = raw.mean(axis=0)
    scale = raw.std(axis=0)
    scale[scale < 1e-6] = 1.0
    digest = sha256()
    for value in (projection, bias, mean, scale):
        digest.update(_array_sha256(value).encode("ascii"))
    return FrozenSheetFeatureField(projection, bias, mean, scale, digest.hexdigest())


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=1, keepdims=True)


def _cross_entropy(probabilities: np.ndarray, labels: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0))


def _metrics(
    features: np.ndarray, labels: np.ndarray, weight: np.ndarray, bias: np.ndarray
) -> dict[str, Any]:
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
        mask = (confidence >= lower) & (
            confidence < upper if upper < 1.0 else confidence <= upper
        )
        if mask.any():
            ece += float(mask.mean()) * abs(
                float(correct[mask].mean()) - float(confidence[mask].mean())
            )
    return {
        "cross_entropy": float(losses.mean()),
        "accuracy": float(correct.mean()),
        "macro_f1": float(np.mean(f1_values)),
        "worst_concept_accuracy": min(concept_accuracy.values()),
        "expected_calibration_error": ece,
        "concept_accuracy": concept_accuracy,
    }


def _shuffled_samples(
    samples: Sequence[ExposureSample], *, seed: int
) -> tuple[ExposureSample, ...]:
    train = [sample for sample in samples if sample.split == "train"]
    concepts = np.asarray([sample.concept_id for sample in train], dtype=object)
    rng = np.random.default_rng(700_000 + seed)
    shuffled = concepts[rng.permutation(len(concepts))]
    replacements = dict(
        zip((sample.sample_id for sample in train), shuffled, strict=True)
    )
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


def _seed_for_arm(seed: int, arm: str) -> int:
    digest = sha256(f"{seed}:{arm}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little")


def _initial_weights(seed: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(200_000 + seed)
    return (
        rng.normal(0.0, 0.02, (width, len(CONCEPTS))).astype(np.float64),
        np.zeros(len(CONCEPTS), dtype=np.float64),
    )


def _checkpoint_key(metrics: Mapping[str, Any]) -> tuple[float, float, float]:
    return (
        float(metrics["macro_f1"]),
        float(metrics["worst_concept_accuracy"]),
        -float(metrics["cross_entropy"]),
    )


def train_horse(
    dataset: ConceptOrbitDataset,
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
    field = build_frozen_sheet_feature_field(dataset.calibration_x, seed=seed)
    train_x = dataset.train_x(arm)
    samples = dataset.samples(arm)
    train_features = field.transform(train_x)
    validation_features = field.transform(dataset.validation_x)
    holdout_features = field.transform(dataset.holdout_x)
    initial_weight, initial_bias = _initial_weights(seed, train_features.shape[1])
    weight = initial_weight.copy()
    bias = initial_bias.copy()
    initial_vector = np.concatenate((weight.ravel(), bias))
    audit_ledger = ConceptExposureLedger(samples, gradient_width=len(CONCEPTS))
    sampling_ledger = audit_ledger
    if arm == "orbit_shuffled_exposure":
        sampling_ledger = ConceptExposureLedger(
            _shuffled_samples(samples, seed=seed), gradient_width=len(CONCEPTS)
        )
    fixed_probabilities: np.ndarray | None = None
    if arm.endswith("_uniform"):
        fixed_probabilities = np.full(len(dataset.train_y), 1.0 / len(dataset.train_y))
    elif arm.endswith("_class_balanced"):
        fixed_probabilities = class_balanced_probabilities(samples)

    rng = np.random.default_rng(_seed_for_arm(seed, arm))
    moment_weight = np.zeros_like(weight)
    variance_weight = np.zeros_like(weight)
    moment_bias = np.zeros_like(bias)
    variance_bias = np.zeros_like(bias)
    beta_one = 0.9
    beta_two = 0.999
    epsilon = 1e-8
    train_ids = audit_ledger.train_sample_ids
    best_weight = weight.copy()
    best_bias = bias.copy()
    best_step = 0
    best_validation = _metrics(validation_features, dataset.validation_y, weight, bias)
    best_key = _checkpoint_key(best_validation)
    trace_path = output_dir / "TRACE.jsonl"
    with trace_path.open("w", encoding="utf-8") as trace:
        for step in range(1, steps + 1):
            probabilities = (
                fixed_probabilities
                if fixed_probabilities is not None
                else sampling_ledger.sampling_probabilities()
            )
            indices = rng.choice(
                len(dataset.train_y), size=batch_size, replace=True, p=probabilities
            )
            batch_features = train_features[indices]
            batch_labels = dataset.train_y[indices]
            predicted = _softmax(batch_features @ weight + bias)
            losses = _cross_entropy(predicted, batch_labels)
            gradient_logits = predicted.copy()
            gradient_logits[np.arange(batch_size), batch_labels] -= 1.0
            sample_ids = [train_ids[int(index)] for index in indices]
            audit_ledger.observe_batch(sample_ids, losses, gradient_logits)
            if sampling_ledger is not audit_ledger:
                sampling_ledger.observe_batch(sample_ids, losses, gradient_logits)

            gradient_weight = batch_features.T @ gradient_logits / batch_size
            gradient_bias = gradient_logits.mean(axis=0)
            moment_weight = (
                beta_one * moment_weight + (1.0 - beta_one) * gradient_weight
            )
            variance_weight = beta_two * variance_weight + (1.0 - beta_two) * np.square(
                gradient_weight
            )
            moment_bias = beta_one * moment_bias + (1.0 - beta_one) * gradient_bias
            variance_bias = beta_two * variance_bias + (1.0 - beta_two) * np.square(
                gradient_bias
            )
            correction_one = 1.0 - beta_one**step
            correction_two = 1.0 - beta_two**step
            phase = (step - 1) / max(1, steps - 1)
            step_rate = learning_rate * (
                0.1 + 0.9 * 0.5 * (1.0 + math.cos(math.pi * phase))
            )
            weight -= (
                step_rate
                * (moment_weight / correction_one)
                / (np.sqrt(variance_weight / correction_two) + epsilon)
            )
            bias -= (
                step_rate
                * (moment_bias / correction_one)
                / (np.sqrt(variance_bias / correction_two) + epsilon)
            )

            if step == 1 or step % log_every == 0 or step == steps:
                validation = _metrics(
                    validation_features, dataset.validation_y, weight, bias
                )
                key = _checkpoint_key(validation)
                if key > best_key:
                    best_key = key
                    best_step = step
                    best_validation = validation
                    best_weight = weight.copy()
                    best_bias = bias.copy()
                row = {
                    "step": step,
                    "learning_rate": step_rate,
                    "train": _metrics(train_features, dataset.train_y, weight, bias),
                    "validation": validation,
                    "best_validation_step": best_step,
                    "weight_delta_l2": float(
                        np.linalg.norm(
                            np.concatenate((weight.ravel(), bias)) - initial_vector
                        )
                    ),
                    "total_exposures": int(audit_ledger.exposure_counts.sum()),
                    "sampling_probability_min": float(probabilities.min()),
                    "sampling_probability_max": float(probabilities.max()),
                }
                trace.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                trace.flush()

    selected_vector = np.concatenate((best_weight.ravel(), best_bias))
    metrics = {
        "train": _metrics(train_features, dataset.train_y, best_weight, best_bias),
        "validation": best_validation,
        "holdout": _metrics(
            holdout_features, dataset.holdout_y, best_weight, best_bias
        ),
    }
    result: dict[str, Any] = {
        "schema": HORSE_SCHEMA,
        "arm": arm,
        "seed": seed,
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "selected_step": best_step,
        "trainable_parameters": int(best_weight.size + best_bias.size),
        "frozen_feature_sha256": field.sha256,
        "frozen_feature_unchanged": True,
        "initial_weight_sha256": _array_sha256(initial_vector),
        "metrics": metrics,
        "weight_effect": weight_effect_receipt(initial_vector, selected_vector),
        "terminal_weight_effect": weight_effect_receipt(
            initial_vector, np.concatenate((weight.ravel(), bias))
        ),
        "exposure": audit_ledger.report(),
        "sampling_exposure": (
            sampling_ledger.report() if sampling_ledger is not audit_ledger else None
        ),
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "trace_sha256": _sha256_file(trace_path),
        "authority": {
            "tool_dispatch": "DISABLED",
            "promotion": "NOT_AUTHORIZED",
            "partial_unfreeze": "NONE",
            "validation_sampling": "PROHIBITED",
            "holdout_sampling": "PROHIBITED",
        },
    }
    result["result_sha256"] = _canonical_sha256(result)
    _atomic_npz(output_dir / "WEIGHTS.npz", weight=best_weight, bias=best_bias)
    _atomic_json(result_path, result)
    return result


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
    comparisons: dict[str, Any] = {}
    for control in REQUIRED_CONTROLS:
        comparisons[control] = {
            metric: _comparison(
                [
                    float(row["metrics"]["holdout"][metric])
                    for row in by_arm[PRIMARY_ARM]
                ],
                [float(row["metrics"]["holdout"][metric]) for row in by_arm[control]],
            )
            for metric in PRIMARY_METRICS
        }
    data_comparison = {
        metric: _comparison(
            [
                float(row["metrics"]["holdout"][metric])
                for row in by_arm["orbit_class_balanced"]
            ],
            [
                float(row["metrics"]["holdout"][metric])
                for row in by_arm["static_class_balanced"]
            ],
        )
        for metric in PRIMARY_METRICS
    }
    enough_seeds = len(set(seeds)) >= 3
    complete = all(len(rows) == len(seeds) for rows in by_arm.values())
    scheduler_selection = (
        enough_seeds
        and complete
        and all(
            comparison[metric]["pass"]
            for comparison in comparisons.values()
            for metric in PRIMARY_METRICS
        )
    )
    data_signal = (
        enough_seeds
        and complete
        and all(data_comparison[metric]["pass"] for metric in PRIMARY_METRICS)
    )
    return {
        "metrics": metrics,
        "comparisons": comparisons,
        "data_comparison": data_comparison,
        "enough_seeds": enough_seeds,
        "complete_control_surface": complete,
        "scheduler_selection_candidate": scheduler_selection,
        "orbit_data_signal": data_signal,
        "verdict": (
            "SCHEDULER_SELECTION_CANDIDATE"
            if scheduler_selection
            else "ORBIT_DATA_SIGNAL_ONLY" if data_signal else "NO_SELECTION"
        ),
    }


def _market_report(result: Mapping[str, Any]) -> str:
    lines = [
        "# Concept-orbit replay market report",
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


def run_campaign(
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
    if len(set(seeds)) != len(seeds) or not seeds:
        raise ValueError("seeds must be non-empty and unique")
    if min(steps, batch_size, log_every) < 1 or learning_rate <= 0.0:
        raise ValueError("training parameters must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = build_concept_orbit_dataset()
    _atomic_json(output_dir / "DATASET_MANIFEST.json", dataset.manifest)
    implementation_path = implementation_path or Path(__file__)
    campaign: dict[str, Any] = {
        "schema": CAMPAIGN_SCHEMA,
        "seeds": list(seeds),
        "arms": list(arms),
        "primary_arm": PRIMARY_ARM,
        "required_controls": list(REQUIRED_CONTROLS),
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "log_every": log_every,
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
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
    for seed in seeds:
        for arm in arms:
            horses.append(
                train_horse(
                    dataset,
                    arm=arm,
                    seed=int(seed),
                    steps=steps,
                    batch_size=batch_size,
                    learning_rate=learning_rate,
                    log_every=log_every,
                    output_dir=output_dir / "horses" / f"{arm}-seed-{seed}",
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
    market = _market_report(result)
    (output_dir / "MARKET_REPORT.md").write_text(market, encoding="utf-8")
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
