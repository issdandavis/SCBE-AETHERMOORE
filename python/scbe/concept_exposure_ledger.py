"""Bounded concept-exposure accounting for training around frozen components.

The ledger is deliberately outside the governed execution path.  It may choose
which *training* record is seen next, but it cannot mutate a frozen component,
read holdout records into the sampler, or grant action authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

EXPOSURE_LEDGER_SCHEMA = "scbe.concept-exposure-ledger.v2"
EXPOSURE_REPORT_SCHEMA = "scbe.concept-exposure-report.v2"
LEGACY_EXPOSURE_LEDGER_SCHEMA = "scbe.concept-exposure-ledger.v1"
WEIGHT_EFFECT_SCHEMA = "scbe.weight-effect-receipt.v1"
VALID_SPLITS = frozenset({"train", "holdout", "anchor"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _finite_float(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ExposureSample:
    """Identity-only description of one train, holdout, or anchor record."""

    sample_id: str
    payload_sha256: str
    concept_id: str
    variant_id: str
    source_family: str
    split: str
    operation_id: str = "unspecified"
    view_id: str = "canonical"

    def __post_init__(self) -> None:
        for name in (
            "sample_id",
            "concept_id",
            "variant_id",
            "source_family",
            "operation_id",
            "view_id",
        ):
            value = str(getattr(self, name)).strip()
            if not value or len(value) > 160:
                raise ValueError(f"{name} must contain 1..160 characters")
            object.__setattr__(self, name, value)
        digest = str(self.payload_sha256).strip().casefold()
        if not _SHA256.fullmatch(digest):
            raise ValueError("payload_sha256 must be a lowercase SHA-256 digest")
        object.__setattr__(self, "payload_sha256", digest)
        split = str(self.split).strip().casefold()
        if split not in VALID_SPLITS:
            raise ValueError(f"split must be one of {sorted(VALID_SPLITS)}")
        object.__setattr__(self, "split", split)

    def identity_record(self) -> dict[str, str]:
        return {
            "sample_id": self.sample_id,
            "payload_sha256": self.payload_sha256,
            "concept_id": self.concept_id,
            "variant_id": self.variant_id,
            "source_family": self.source_family,
            "split": self.split,
            "operation_id": self.operation_id,
            "view_id": self.view_id,
        }


class ConceptExposureLedger:
    """Track repeated views and bounded gradient sketches for training records.

    Only records declared as ``train`` receive an index or sampling mass.
    Holdout and anchor identities contribute to the sealed manifest so a caller
    cannot silently move them into training after the ledger is constructed.
    """

    def __init__(
        self,
        samples: Sequence[ExposureSample],
        *,
        gradient_width: int,
        elite_capacity: int = 8,
        ema_rate: float = 0.2,
        exploration_floor: float = 0.1,
        minimum_exposures_per_concept: int = 64,
        saturation_improvement: float = 1e-4,
        saturation_loss: float = 0.5,
    ) -> None:
        if gradient_width < 1:
            raise ValueError("gradient_width must be positive")
        if elite_capacity < 1:
            raise ValueError("elite_capacity must be positive")
        if not 0.0 < ema_rate <= 1.0:
            raise ValueError("ema_rate must be in (0, 1]")
        if not 0.0 <= exploration_floor < 1.0:
            raise ValueError("exploration_floor must be in [0, 1)")
        if minimum_exposures_per_concept < 1:
            raise ValueError("minimum_exposures_per_concept must be positive")
        self.gradient_width = int(gradient_width)
        self.elite_capacity = int(elite_capacity)
        self.ema_rate = float(ema_rate)
        self.exploration_floor = float(exploration_floor)
        self.minimum_exposures_per_concept = int(minimum_exposures_per_concept)
        self.saturation_improvement = _finite_float(
            saturation_improvement, name="saturation_improvement"
        )
        self.saturation_loss = _finite_float(saturation_loss, name="saturation_loss")

        self.samples = tuple(samples)
        if not self.samples:
            raise ValueError("samples must not be empty")
        sample_ids = [sample.sample_id for sample in self.samples]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("sample_id values must be unique")
        train_sources = {
            sample.source_family for sample in self.samples if sample.split == "train"
        }
        evaluation_sources = {
            sample.source_family for sample in self.samples if sample.split != "train"
        }
        overlap = train_sources & evaluation_sources
        if overlap:
            raise ValueError(
                f"train and evaluation source families must be disjoint: {sorted(overlap)}"
            )

        self._train_samples = tuple(
            sample for sample in self.samples if sample.split == "train"
        )
        if not self._train_samples:
            raise ValueError("at least one train sample is required")
        self._train_index = {
            sample.sample_id: index for index, sample in enumerate(self._train_samples)
        }
        self._concepts = tuple(
            sorted({sample.concept_id for sample in self._train_samples})
        )
        self._concept_index = {name: index for index, name in enumerate(self._concepts)}
        self._sample_concepts = np.asarray(
            [self._concept_index[sample.concept_id] for sample in self._train_samples],
            dtype=np.int64,
        )
        variant_keys = [
            (sample.concept_id, sample.variant_id) for sample in self._train_samples
        ]
        unique_variants = tuple(sorted(set(variant_keys)))
        variant_index = {key: index for index, key in enumerate(unique_variants)}
        self._variant_keys = unique_variants
        self._sample_variants = np.asarray(
            [variant_index[key] for key in variant_keys], dtype=np.int64
        )
        self._sample_operations, self._operation_keys = self._axis_indices(
            sample.operation_id for sample in self._train_samples
        )
        self._sample_views, self._view_keys = self._axis_indices(
            sample.view_id for sample in self._train_samples
        )
        self._sample_sources, self._source_keys = self._axis_indices(
            sample.source_family for sample in self._train_samples
        )

        size = len(self._train_samples)
        self._counts = np.zeros(size, dtype=np.int64)
        self._loss_ema = np.full(size, np.nan, dtype=np.float64)
        self._improvement_ema = np.zeros(size, dtype=np.float64)
        self._last_gradient = np.zeros((size, self.gradient_width), dtype=np.float64)
        self._has_gradient = np.zeros(size, dtype=bool)
        self._elites: dict[str, list[tuple[float, np.ndarray]]] = {
            concept: [] for concept in self._concepts
        }
        self._manifest = {
            "schema": EXPOSURE_LEDGER_SCHEMA,
            "samples": [sample.identity_record() for sample in self.samples],
            "gradient_width": self.gradient_width,
            "elite_capacity": self.elite_capacity,
            "ema_rate": self.ema_rate,
            "exploration_floor": self.exploration_floor,
            "minimum_exposures_per_concept": self.minimum_exposures_per_concept,
            "saturation_improvement": self.saturation_improvement,
            "saturation_loss": self.saturation_loss,
        }
        self.manifest_sha256 = _canonical_sha256(self._manifest)
        self._legacy_manifest_sha256: str | None = None
        if all(
            sample.operation_id == "unspecified" and sample.view_id == "canonical"
            for sample in self.samples
        ):
            legacy_manifest = {
                **self._manifest,
                "schema": LEGACY_EXPOSURE_LEDGER_SCHEMA,
                "samples": [
                    {
                        "sample_id": sample.sample_id,
                        "payload_sha256": sample.payload_sha256,
                        "concept_id": sample.concept_id,
                        "variant_id": sample.variant_id,
                        "source_family": sample.source_family,
                        "split": sample.split,
                    }
                    for sample in self.samples
                ],
            }
            self._legacy_manifest_sha256 = _canonical_sha256(legacy_manifest)

    @property
    def train_sample_ids(self) -> tuple[str, ...]:
        return tuple(sample.sample_id for sample in self._train_samples)

    @property
    def exposure_counts(self) -> np.ndarray:
        return self._counts.copy()

    def _prototype(self, concept: str) -> np.ndarray | None:
        elites = self._elites[concept]
        if not elites:
            return None
        weights = np.asarray(
            [max(score, 1e-12) for score, _ in elites], dtype=np.float64
        )
        gradients = np.stack([gradient for _, gradient in elites])
        prototype = np.average(gradients, axis=0, weights=weights)
        norm = float(np.linalg.norm(prototype))
        if norm <= 1e-12:
            return None
        return prototype / norm

    @staticmethod
    def _axis_indices(values: Iterable[str]) -> tuple[np.ndarray, tuple[str, ...]]:
        rows = tuple(values)
        keys = tuple(sorted(set(rows)))
        index = {name: position for position, name in enumerate(keys)}
        return np.asarray([index[name] for name in rows], dtype=np.int64), keys

    def _axis_need(self, indices: np.ndarray, cardinality: int) -> np.ndarray:
        total_exposures = int(self._counts.sum())
        counts = np.bincount(indices, weights=self._counts, minlength=cardinality)
        mean = total_exposures / max(1, cardinality)
        need = np.sqrt((mean + 1.0) / (counts[indices] + 1.0))
        return np.clip(need, 0.5, 2.5)

    def observe_batch(
        self,
        sample_ids: Sequence[str],
        losses: Sequence[float] | np.ndarray,
        gradient_sketches: Sequence[Sequence[float]] | np.ndarray,
    ) -> None:
        """Record actual train exposures after one optimizer observation."""

        if len(sample_ids) == 0:
            raise ValueError("an observation batch must not be empty")
        loss_array = np.asarray(losses, dtype=np.float64)
        gradient_array = np.asarray(gradient_sketches, dtype=np.float64)
        if loss_array.shape != (len(sample_ids),):
            raise ValueError("losses must have one scalar per sample")
        if gradient_array.shape != (len(sample_ids), self.gradient_width):
            raise ValueError("gradient_sketches have the wrong shape")
        if not np.all(np.isfinite(loss_array)) or not np.all(
            np.isfinite(gradient_array)
        ):
            raise ValueError("observations must be finite")
        if np.any(loss_array < 0.0):
            raise ValueError("losses must be non-negative")

        for sample_id, loss, gradient in zip(
            sample_ids, loss_array, gradient_array, strict=True
        ):
            try:
                index = self._train_index[str(sample_id)]
            except KeyError as exc:
                raise ValueError(
                    "holdout, anchor, or unknown sample cannot enter training"
                ) from exc
            prior = self._loss_ema[index]
            improvement = float(prior - loss) if math.isfinite(float(prior)) else 0.0
            if math.isfinite(float(prior)):
                self._loss_ema[index] = (
                    1.0 - self.ema_rate
                ) * prior + self.ema_rate * loss
            else:
                self._loss_ema[index] = loss
            self._improvement_ema[index] = (
                1.0 - self.ema_rate
            ) * self._improvement_ema[index] + self.ema_rate * improvement
            norm = float(np.linalg.norm(gradient))
            if norm > 1e-12:
                normalized = np.asarray(gradient / norm, dtype=np.float64)
                self._last_gradient[index] = normalized
                self._has_gradient[index] = True
                if improvement > 0.0:
                    concept = self._train_samples[index].concept_id
                    elites = self._elites[concept]
                    elites.append((improvement, normalized.copy()))
                    elites.sort(key=lambda row: row[0], reverse=True)
                    del elites[self.elite_capacity :]
            self._counts[index] += 1

    def sampling_probabilities(self) -> np.ndarray:
        """Return bounded adaptive mass over train records only."""

        size = len(self._train_samples)
        total_exposures = int(self._counts.sum())
        concept_counts = np.bincount(
            self._sample_concepts,
            weights=self._counts,
            minlength=len(self._concepts),
        )
        variant_counts = np.bincount(
            self._sample_variants,
            weights=self._counts,
            minlength=len(self._variant_keys),
        )
        mean_concept = total_exposures / max(1, len(self._concepts))
        mean_sample = total_exposures / max(1, size)
        mean_variant = total_exposures / max(1, len(self._variant_keys))
        concept_need = np.sqrt(
            (mean_concept + 1.0) / (concept_counts[self._sample_concepts] + 1.0)
        )
        sample_need = np.sqrt((mean_sample + 1.0) / (self._counts + 1.0))
        variant_need = np.sqrt(
            (mean_variant + 1.0) / (variant_counts[self._sample_variants] + 1.0)
        )
        concept_need = np.clip(concept_need, 0.5, 2.5)
        sample_need = np.clip(sample_need, 0.5, 2.5)
        variant_need = np.clip(variant_need, 0.5, 2.5)
        operation_need = self._axis_need(
            self._sample_operations, len(self._operation_keys)
        )
        view_need = self._axis_need(self._sample_views, len(self._view_keys))
        source_need = self._axis_need(self._sample_sources, len(self._source_keys))

        finite_losses = self._loss_ema[np.isfinite(self._loss_ema)]
        loss_fill = float(np.median(finite_losses)) if finite_losses.size else 1.0
        loss_scale = max(loss_fill, 1e-6)
        losses = np.where(np.isfinite(self._loss_ema), self._loss_ema, loss_fill)
        loss_factor = np.clip(0.75 + 0.5 * (losses / loss_scale), 0.75, 2.0)

        alignment_factor = np.ones(size, dtype=np.float64)
        for concept in self._concepts:
            prototype = self._prototype(concept)
            mask = self._sample_concepts == self._concept_index[concept]
            unseen = mask & ~self._has_gradient
            alignment_factor[unseen] = 1.1
            if prototype is not None:
                indices = np.flatnonzero(mask & self._has_gradient)
                if indices.size:
                    alignment = self._last_gradient[indices] @ prototype
                    alignment_factor[indices] = np.clip(1.0 + 0.2 * alignment, 0.8, 1.2)

        scores = (
            concept_need
            * sample_need
            * variant_need
            * operation_need
            * view_need
            * source_need
            * loss_factor
            * alignment_factor
        )
        median_score = max(float(np.median(scores)), 1e-12)
        scores = np.clip(scores, median_score / 8.0, median_score * 8.0)
        probabilities = scores / float(scores.sum())
        probabilities = (
            1.0 - self.exploration_floor
        ) * probabilities + self.exploration_floor / size
        probabilities /= float(probabilities.sum())
        if not np.all(np.isfinite(probabilities)) or np.any(probabilities <= 0.0):
            raise RuntimeError("adaptive sampling produced invalid mass")
        return probabilities

    def _concept_report(self, concept: str) -> dict[str, Any]:
        mask = self._sample_concepts == self._concept_index[concept]
        counts = self._counts[mask]
        seen = counts > 0
        losses = self._loss_ema[mask]
        finite = np.isfinite(losses)
        improvements = self._improvement_ema[mask]
        variants = self._sample_variants[mask]
        seen_variants = {
            int(variant)
            for variant, count in zip(variants, counts, strict=True)
            if count > 0
        }
        total = int(counts.sum())
        effective = (
            float(total * total / np.square(counts, dtype=np.float64).sum())
            if total and np.square(counts, dtype=np.float64).sum() > 0.0
            else 0.0
        )
        elites = self._elites[concept]
        elite_coherence = 0.0
        if elites:
            elite_coherence = float(
                np.linalg.norm(
                    np.mean(np.stack([gradient for _, gradient in elites]), axis=0)
                )
            )
        mean_loss = float(np.mean(losses[finite])) if finite.any() else None
        mean_improvement = float(np.mean(improvements[seen])) if seen.any() else 0.0
        total_variants = len(set(int(value) for value in variants))
        saturation = bool(
            total >= self.minimum_exposures_per_concept
            and len(seen_variants) == total_variants
            and mean_loss is not None
            and mean_loss <= self.saturation_loss
            and abs(mean_improvement) <= self.saturation_improvement
        )
        return {
            "exposures": total,
            "unique_samples_seen": int(seen.sum()),
            "sample_count": int(mask.sum()),
            "variants_seen": len(seen_variants),
            "variant_count": total_variants,
            "effective_sample_exposures": effective,
            "mean_loss_ema": mean_loss,
            "mean_improvement_ema": mean_improvement,
            "elite_gradient_count": len(elites),
            "elite_gradient_coherence": elite_coherence,
            "saturated": saturation,
        }

    def report(self) -> dict[str, Any]:
        """Return a payload-free, replayable accounting report."""

        cells: dict[tuple[str, str, str, str], list[int]] = {}
        for index, sample in enumerate(self._train_samples):
            key = (
                sample.concept_id,
                sample.operation_id,
                sample.view_id,
                sample.source_family,
            )
            cells.setdefault(key, []).append(index)
        tensor_rows = []
        for key, indices in sorted(cells.items()):
            counts = self._counts[np.asarray(indices, dtype=np.int64)]
            presentations = int(counts.sum())
            tensor_rows.append(
                {
                    "concept_id": key[0],
                    "operation_id": key[1],
                    "view_id": key[2],
                    "source_family": key[3],
                    "sample_count": len(indices),
                    "presentations": presentations,
                    "unique_samples_seen": int(np.count_nonzero(counts)),
                    "effective_sample_presentations": (
                        float(
                            presentations
                            * presentations
                            / np.square(counts, dtype=np.float64).sum()
                        )
                        if presentations
                        and np.square(counts, dtype=np.float64).sum() > 0.0
                        else 0.0
                    ),
                }
            )

        report: dict[str, Any] = {
            "schema": EXPOSURE_REPORT_SCHEMA,
            "ledger_manifest_sha256": self.manifest_sha256,
            "train_sample_count": len(self._train_samples),
            "holdout_sample_count": sum(
                sample.split == "holdout" for sample in self.samples
            ),
            "anchor_sample_count": sum(
                sample.split == "anchor" for sample in self.samples
            ),
            "train_source_families": sorted(
                {
                    sample.source_family
                    for sample in self.samples
                    if sample.split == "train"
                }
            ),
            "evaluation_source_families": sorted(
                {
                    sample.source_family
                    for sample in self.samples
                    if sample.split != "train"
                }
            ),
            "total_exposures": int(self._counts.sum()),
            "exposure_tensor": {
                "axes": [
                    "concept_id",
                    "operation_id",
                    "view_id",
                    "source_family",
                    "presentations",
                ],
                "operation_ids": list(self._operation_keys),
                "view_ids": list(self._view_keys),
                "source_families": list(self._source_keys),
                "cell_count": len(tensor_rows),
                "cells": tensor_rows,
            },
            "concepts": {
                concept: self._concept_report(concept) for concept in self._concepts
            },
            "authority": {
                "execution": "NONE",
                "promotion": "NOT_AUTHORIZED",
                "holdout_sampling": "PROHIBITED",
            },
        }
        report["report_sha256"] = _canonical_sha256(report)
        return report

    def state_dict(self) -> dict[str, Any]:
        """Return JSON-compatible state for exact checkpoint continuation."""

        return {
            "schema": EXPOSURE_LEDGER_SCHEMA,
            "manifest_sha256": self.manifest_sha256,
            "counts": self._counts.tolist(),
            "loss_ema": [
                float(value) if math.isfinite(float(value)) else None
                for value in self._loss_ema
            ],
            "improvement_ema": self._improvement_ema.tolist(),
            "last_gradient": self._last_gradient.tolist(),
            "has_gradient": self._has_gradient.tolist(),
            "elites": {
                concept: [
                    {"score": float(score), "gradient": gradient.tolist()}
                    for score, gradient in rows
                ]
                for concept, rows in self._elites.items()
            },
        }

    def restore_state(self, state: Mapping[str, Any]) -> None:
        """Restore a state only when its sealed sample manifest matches."""

        schema = state.get("schema")
        if schema == EXPOSURE_LEDGER_SCHEMA:
            expected_manifest = self.manifest_sha256
        elif (
            schema == LEGACY_EXPOSURE_LEDGER_SCHEMA
            and self._legacy_manifest_sha256 is not None
        ):
            expected_manifest = self._legacy_manifest_sha256
        else:
            raise ValueError("unknown exposure-ledger state schema")
        if state.get("manifest_sha256") != expected_manifest:
            raise ValueError("exposure-ledger manifest mismatch")
        size = len(self._train_samples)
        counts = np.asarray(state.get("counts"), dtype=np.int64)
        loss_ema = np.asarray(
            [np.nan if value is None else value for value in state.get("loss_ema", ())],
            dtype=np.float64,
        )
        improvement = np.asarray(state.get("improvement_ema"), dtype=np.float64)
        gradient = np.asarray(state.get("last_gradient"), dtype=np.float64)
        has_gradient = np.asarray(state.get("has_gradient"), dtype=bool)
        if counts.shape != (size,) or np.any(counts < 0):
            raise ValueError("invalid exposure counts")
        if loss_ema.shape != (size,) or improvement.shape != (size,):
            raise ValueError("invalid exposure loss state")
        if gradient.shape != (size, self.gradient_width) or has_gradient.shape != (
            size,
        ):
            raise ValueError("invalid exposure gradient state")
        if not np.all(np.isfinite(improvement)) or not np.all(np.isfinite(gradient)):
            raise ValueError("exposure state must be finite")
        elite_payload = state.get("elites")
        if not isinstance(elite_payload, Mapping) or set(elite_payload) != set(
            self._concepts
        ):
            raise ValueError("invalid elite-gradient state")
        restored_elites: dict[str, list[tuple[float, np.ndarray]]] = {}
        for concept in self._concepts:
            rows = elite_payload[concept]
            if not isinstance(rows, list) or len(rows) > self.elite_capacity:
                raise ValueError("invalid elite-gradient capacity")
            restored: list[tuple[float, np.ndarray]] = []
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("invalid elite-gradient row")
                score = _finite_float(row.get("score"), name="elite score")
                vector = np.asarray(row.get("gradient"), dtype=np.float64)
                if score <= 0.0 or vector.shape != (self.gradient_width,):
                    raise ValueError("invalid elite-gradient row")
                if not np.all(np.isfinite(vector)):
                    raise ValueError("elite gradient must be finite")
                restored.append((score, vector))
            restored_elites[concept] = restored
        self._counts = counts
        self._loss_ema = loss_ema
        self._improvement_ema = improvement
        self._last_gradient = gradient
        self._has_gradient = has_gradient
        self._elites = restored_elites


def class_balanced_probabilities(samples: Sequence[ExposureSample]) -> np.ndarray:
    """Return the ordinary inverse-frequency control over train records."""

    train = [sample for sample in samples if sample.split == "train"]
    if not train:
        raise ValueError("at least one train sample is required")
    counts: dict[str, int] = {}
    for sample in train:
        counts[sample.concept_id] = counts.get(sample.concept_id, 0) + 1
    mass = np.asarray(
        [1.0 / counts[sample.concept_id] for sample in train], dtype=np.float64
    )
    mass /= float(mass.sum())
    return mass


def weight_effect_receipt(initial: np.ndarray, final: np.ndarray) -> dict[str, Any]:
    """Describe a real finite weight change without storing the weights."""

    before = np.asarray(initial)
    after = np.asarray(final)
    if before.shape != after.shape or before.dtype != after.dtype:
        raise ValueError("weight arrays must have identical shape and dtype")
    if not np.all(np.isfinite(before)) or not np.all(np.isfinite(after)):
        raise ValueError("weight arrays must be finite")
    delta = np.asarray(after - before)
    receipt: dict[str, Any] = {
        "schema": WEIGHT_EFFECT_SCHEMA,
        "shape": list(before.shape),
        "dtype": str(before.dtype),
        "initial_sha256": _array_sha256(before),
        "final_sha256": _array_sha256(after),
        "delta_l2": float(np.linalg.norm(delta)),
        "delta_linf": float(np.max(np.abs(delta))) if delta.size else 0.0,
        "changed_scalars": int(np.count_nonzero(delta)),
        "scalar_count": int(delta.size),
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def exposure_manifest_sha256(samples: Iterable[ExposureSample]) -> str:
    """Hash sample identities without reading or serializing payload contents."""

    records = [sample.identity_record() for sample in samples]
    return _canonical_sha256({"samples": records})
