"""Experimental bridge for layering SCBE storage systems together.

This module keeps the experiment bounded: it projects one record into several
existing storage surfaces and measures how their geometry interacts, including
negative-vector folding through signed-octree mirroring.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

from src.ai_brain.entropic_layer import EntropicLayer, EntropicState
from hydra.lattice25d_ops import NoteRecord, intent_from_metrics, text_metrics
from hydra.octree_sphere_grid import HyperbolicLattice25D, OCTANT_NAMES, SignTriplet
from src.crypto.octree import HyperbolicOctree
from src.knowledge.quasicrystal_voxel_drive import QuasiCrystalVoxelDrive

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
REALM_LIGHT = "light_realm"
REALM_SHADOW = "shadow_realm"
REALM_PATH = "path"


@dataclass
class MeshRecord:
    note_id: str
    tongue: str
    lattice_bundle_id: str
    hyperbolic_realm: str
    octree_point: tuple[float, float, float]
    qc_coords: list[float]
    signed_intent: list[float]
    focus_delta: float
    entropic_volume: float
    entropic_volume_ratio: float
    entropic_escape: bool
    adaptive_k: int
    fold_applied: bool = False
    fold_target_octant: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _hash_unit(seed: str) -> float:
    digest = hashlib.blake2s(seed.encode("utf-8"), digest_size=8).digest()
    raw = int.from_bytes(digest, "big", signed=False)
    return raw / float((1 << 64) - 1)


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize_ball(vector: Iterable[float], *, limit: float = 0.94) -> list[float]:
    arr = np.asarray(list(vector), dtype=float)
    norm = float(np.linalg.norm(arr))
    if norm > limit and norm > 0:
        arr = arr * (limit / norm)
    return [float(v) for v in arr.tolist()]


def _cyclic_phase_distance(a: float, b: float) -> float:
    two_pi = 2.0 * math.pi
    d = abs((a - b) % two_pi)
    return min(d, two_pi - d)


def _select_tongue(preferred: str, index: int, seed: str) -> str:
    if preferred in TONGUES:
        return preferred
    offset = int(_hash_unit(seed) * 10_000)
    return TONGUES[(index + offset) % len(TONGUES)]


def _position_for_record(
    note_id: str, *, phase_rad: float | None = None, radius: float = 0.72
) -> tuple[float, float, float]:
    angle = 2.0 * math.pi * _hash_unit(f"{note_id}|angle")
    radial = 0.08 + radius * _hash_unit(f"{note_id}|radius")
    x = math.cos(angle) * radial
    y = math.sin(angle) * radial
    phase = phase_rad if phase_rad is not None else 2.0 * math.pi * _hash_unit(f"{note_id}|phase")
    return x, y, phase


def _positive_to_signed(intent: list[float]) -> list[float]:
    return [float((2.0 * value) - 1.0) for value in intent]


def _qc_coords_from_state(x: float, y: float, phase_rad: float, signed_intent: list[float]) -> list[float]:
    phase_sin = math.sin(phase_rad)
    phase_cos = math.cos(phase_rad)
    coords = [x, y, phase_sin, phase_cos, signed_intent[0], signed_intent[1] + signed_intent[2]]
    return _normalize_ball(coords, limit=0.93)


def _octree_point_from_state(
    x: float, y: float, phase_rad: float, signed_intent: list[float]
) -> tuple[float, float, float]:
    z = _clip(math.sin(phase_rad) * 0.82 + signed_intent[2] * 0.12, -0.94, 0.94)
    point = _normalize_ball((x, y, z), limit=0.94)
    return (point[0], point[1], point[2])


def _realm_from_signed_vector(signed_intent: list[float]) -> str:
    total = sum(signed_intent)
    if total <= -0.35:
        return REALM_SHADOW
    if total >= 0.35:
        return REALM_LIGHT
    return REALM_PATH


def _fold_target_octant(source_octant: SignTriplet, signed_intent: list[float], threshold: float) -> SignTriplet:
    flips = [component <= -threshold for component in signed_intent]
    return tuple((not sign) if flip else sign for sign, flip in zip(source_octant, flips))  # type: ignore[return-value]


def _find_bundle_voxel(lattice: HyperbolicLattice25D, bundle_id: str):
    for voxel in lattice.octree.root.collect_all():
        if (voxel.payload or {}).get("_bundle_id") == bundle_id:
            return voxel
    return None


class StorageInteractionMesh:
    """Layer several existing storage systems using one shared projection path."""

    def __init__(
        self,
        *,
        lattice: HyperbolicLattice25D | None = None,
        hyperbolic_octree: HyperbolicOctree | None = None,
        quasi_drive: QuasiCrystalVoxelDrive | None = None,
        focus_phase_rad: float = 0.5,
        focus_bandwidth: float = 0.18,
        fold_negative_vectors: bool = True,
        fold_threshold: float = 0.15,
    ):
        self.lattice = lattice or HyperbolicLattice25D(index_mode="hybrid", quadtree_capacity=12, cell_size=0.5)
        self.hyperbolic_octree = hyperbolic_octree or HyperbolicOctree(grid_size=64, max_depth=3)
        self.quasi_drive = quasi_drive or QuasiCrystalVoxelDrive(resolution=32)
        self.entropic_layer = EntropicLayer()
        self.focus_phase_rad = focus_phase_rad
        self.focus_bandwidth = focus_bandwidth
        self.fold_negative_vectors = fold_negative_vectors
        self.fold_threshold = fold_threshold
        self.records: list[MeshRecord] = []

    def ingest_notes(self, notes: list[NoteRecord]) -> list[MeshRecord]:
        for idx, note in enumerate(notes):
            metrics = text_metrics(note.text or "")
            positive_intent = intent_from_metrics(metrics)
            signed_intent = _positive_to_signed(positive_intent)
            note_id = note.note_id or f"note-{idx}"
            tongue = _select_tongue(note.tongue, idx, note_id)
            x, y, phase_rad = _position_for_record(note_id, phase_rad=note.phase_rad)

            bundle = self.lattice.insert_bundle(
                x=x,
                y=y,
                phase_rad=phase_rad,
                tongue=tongue,
                authority=note.authority or "public",
                intent_vector=positive_intent,
                intent_label=note_id[:48],
                payload={
                    "note_id": note_id,
                    "source": note.source,
                    "tags": list(note.tags),
                    "metrics": metrics,
                    "signed_intent": signed_intent,
                    "text_preview": (note.text or "")[:220],
                },
            )

            octree_point = _octree_point_from_state(x, y, phase_rad, signed_intent)
            realm = _realm_from_signed_vector(signed_intent)
            self.hyperbolic_octree.insert(np.array(octree_point, dtype=float), realm)

            qc_coords = _qc_coords_from_state(x, y, phase_rad, signed_intent)
            self.quasi_drive.store(
                note_id,
                (note.text or "").encode("utf-8"),
                qc_coords,
                category=realm,
            )

            entropic_state = EntropicState(
                position=list(qc_coords),
                velocity=[signed_intent[0], signed_intent[1], signed_intent[2], 0.0, 0.0, 0.0],
            )
            entropic_assessment = self.entropic_layer.detect_escape(entropic_state)
            adaptive_k = self.entropic_layer.adaptive_k(
                _clip(sum(positive_intent) / max(1, len(positive_intent)), 0.0, 1.0)
            )

            focus_delta = _cyclic_phase_distance(phase_rad, self.focus_phase_rad)
            record = MeshRecord(
                note_id=note_id,
                tongue=tongue,
                lattice_bundle_id=bundle.bundle_id,
                hyperbolic_realm=realm,
                octree_point=octree_point,
                qc_coords=qc_coords,
                signed_intent=signed_intent,
                focus_delta=focus_delta,
                entropic_volume=entropic_assessment.volume,
                entropic_volume_ratio=entropic_assessment.volume_ratio,
                entropic_escape=entropic_assessment.escaped,
                adaptive_k=adaptive_k,
                metadata={"metrics": metrics, "source": note.source, "tags": list(note.tags)},
            )

            if self.fold_negative_vectors:
                voxel = _find_bundle_voxel(self.lattice, bundle.bundle_id)
                if voxel is not None:
                    target = _fold_target_octant(voxel.octant, signed_intent, self.fold_threshold)
                    if target != voxel.octant:
                        self.lattice.octree.mirror_octant(voxel.octant, target, transform_intent=True)
                        record.fold_applied = True
                        record.fold_target_octant = OCTANT_NAMES[target]

            self.records.append(record)

        return list(self.records)

    def attachment_ring_records(self) -> list[MeshRecord]:
        return [record for record in self.records if record.focus_delta <= self.focus_bandwidth]

    def stats(self) -> dict[str, Any]:
        ring_records = self.attachment_ring_records()
        fold_count = sum(1 for record in self.records if record.fold_applied)
        entropic_escape_count = sum(1 for record in self.records if record.entropic_escape)
        adaptive_k_values = [record.adaptive_k for record in self.records]
        return {
            "record_count": len(self.records),
            "focus_phase_rad": self.focus_phase_rad,
            "focus_bandwidth": self.focus_bandwidth,
            "attachment_ring_count": len(ring_records),
            "fold_count": fold_count,
            "entropic_escape_count": entropic_escape_count,
            "max_entropic_volume_ratio": max((record.entropic_volume_ratio for record in self.records), default=0.0),
            "adaptive_k_mean": (sum(adaptive_k_values) / len(adaptive_k_values)) if adaptive_k_values else 0.0,
            "lattice": self.lattice.stats(),
            "hyperbolic_octree": self.hyperbolic_octree.stats(),
            "quasi_drive": self.quasi_drive.stats(),
        }

    def export_state(self) -> dict[str, Any]:
        return {
            "focus_phase_rad": self.focus_phase_rad,
            "focus_bandwidth": self.focus_bandwidth,
            "stats": self.stats(),
            "records": [
                {
                    "note_id": record.note_id,
                    "tongue": record.tongue,
                    "bundle_id": record.lattice_bundle_id,
                    "hyperbolic_realm": record.hyperbolic_realm,
                    "octree_point": list(record.octree_point),
                    "qc_coords": list(record.qc_coords),
                    "signed_intent": list(record.signed_intent),
                    "focus_delta": record.focus_delta,
                    "entropic_volume": record.entropic_volume,
                    "entropic_volume_ratio": record.entropic_volume_ratio,
                    "entropic_escape": record.entropic_escape,
                    "adaptive_k": record.adaptive_k,
                    "fold_applied": record.fold_applied,
                    "fold_target_octant": record.fold_target_octant,
                    "metadata": record.metadata,
                }
                for record in self.records
            ],
        }
