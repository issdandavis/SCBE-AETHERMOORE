"""Storage Bridge Lab — Experimental Multi-Surface Comparison
=============================================================

Feeds the same NoteRecord through all four SCBE storage surfaces:

  1. HyperbolicOctree   (3D Poincare ball, realm coloring, spectral voxels)
  2. HyperbolicLattice25D (2.5D cyclic lattice, tongue/phase bundles)
  3. QuasiCrystalVoxelDrive (6D tensor, Chladni access control)
  4. ScatteredAttentionSphere (holographic routing, band-of-focus)

Plus optional negative-vector fold: when any intent component goes
negative the 3D coordinate is mirrored across that axis in the octree,
storing the "shadow" of the note alongside the "light" version.

Comparison metrics per surface:
  - node_explosion   : total allocated nodes / cells per record
  - overlap_heat     : fraction of records sharing a storage cell
  - compaction_score : records / storage_units
  - governance_trace : can we query back from stored -> source id?
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from hydra.lattice25d_ops import (
    NoteRecord,
    intent_from_metrics,
    text_metrics,
)
from hydra.octree_sphere_grid import HyperbolicLattice25D
from src.crypto.octree import HyperbolicOctree
from src.kernel.scattered_sphere import ScatteredAttentionSphere
from src.knowledge.quasicrystal_voxel_drive import (
    QuasiCrystalVoxelDrive,
    TONGUE_NAMES,
    TONGUE_WEIGHTS as QC_TONGUE_WEIGHTS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "system_audit" / "storage_bridge_lab"

# --------------------------------------------------------------------------- #
#  Hypothesis Deck
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HypothesisCard:
    """One tunable knob in the experiment deck."""

    knob: str
    surface: str
    purpose: str
    expected_effect: str
    metric_to_watch: str
    fail_condition: str
    sweep_values: tuple


HYPOTHESIS_DECK: tuple[HypothesisCard, ...] = (
    HypothesisCard(
        knob="max_depth",
        surface="octree",
        purpose="Control voxel granularity in Poincare ball",
        expected_effect="Lower depth => fewer nodes, better compaction; too low => collision",
        metric_to_watch="compaction_score",
        fail_condition="compaction_score < 0.3 or query_miss_rate > 0.1",
        sweep_values=(3, 4, 5, 6),
    ),
    HypothesisCard(
        knob="cell_size",
        surface="lattice25d",
        purpose="Set grid cell width in 2D plane",
        expected_effect="Larger cells => more overlap, fewer cells; too large => hot cells",
        metric_to_watch="overlap_heat",
        fail_condition="overlap_heat > 0.8 (nearly all records share one cell)",
        sweep_values=(0.2, 0.25, 0.333, 0.5),
    ),
    HypothesisCard(
        knob="quadtree_capacity",
        surface="lattice25d",
        purpose="Max bundles per quadtree leaf before split",
        expected_effect="Higher capacity => fewer nodes; too high => linear scan in leaf",
        metric_to_watch="node_explosion",
        fail_condition="node_explosion > 5.0 (5 nodes per record)",
        sweep_values=(2, 4, 8, 12),
    ),
    HypothesisCard(
        knob="sparsity_threshold",
        surface="sphere",
        purpose="Filter near-zero values before scattering",
        expected_effect="Higher threshold => fewer points, faster sweep; too high => data loss",
        metric_to_watch="compaction_score",
        fail_condition="reconstruct() RMSE > 0.01 (lost signal)",
        sweep_values=(0.001, 0.01, 0.05, 0.1),
    ),
    HypothesisCard(
        knob="resolution",
        surface="qc_drive",
        purpose="6D tensor grid resolution",
        expected_effect="Higher resolution => more address space; too high => wasted memory",
        metric_to_watch="node_explosion",
        fail_condition="total_cells / records < 0.5 (half the records vanish)",
        sweep_values=(16, 32, 64, 128),
    ),
    HypothesisCard(
        knob="phi_wall",
        surface="sphere",
        purpose="Band-of-focus phase angle for routing queries",
        expected_effect="Tuning phi_wall selects which tongue cluster responds to queries",
        metric_to_watch="tongue_distribution evenness",
        fail_condition="One tongue owns >80% of resonant points (degenerate focus)",
        sweep_values=(-1.0, -0.5, 0.0, 0.5, 1.0),
    ),
    HypothesisCard(
        knob="negative_fold",
        surface="octree",
        purpose="Mirror 3D coords across axes where intent < 0",
        expected_effect="Doubles shadow-realm coverage; should separate positive/negative intent",
        metric_to_watch="polarity cluster separation",
        fail_condition="Light and shadow clusters overlap >50%",
        sweep_values=(False, True),
    ),
)


def get_hypothesis_deck() -> list[dict[str, Any]]:
    """Return the deck as plain dicts for JSON serialization."""
    return [
        {
            "knob": card.knob,
            "surface": card.surface,
            "purpose": card.purpose,
            "expected_effect": card.expected_effect,
            "metric_to_watch": card.metric_to_watch,
            "fail_condition": card.fail_condition,
            "sweep_values": list(card.sweep_values),
        }
        for card in HYPOTHESIS_DECK
    ]


# --------------------------------------------------------------------------- #
#  Shared geometry derivation
# --------------------------------------------------------------------------- #


def _blake2_unit(seed: str) -> float:
    """Deterministic hash → [0, 1)."""
    digest = hashlib.blake2s(seed.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False) / float((1 << 64) - 1)


def _note_to_geometry(note: NoteRecord, index: int) -> dict[str, Any]:
    """Derive all shared geometry from a single NoteRecord.

    Returns a dict with keys usable by every surface:
      - coord_3d     : np.ndarray shape (3,) in Poincare ball
      - x, y         : 2D position for lattice
      - phase_rad    : cyclic phase angle
      - tongue_coords: list[float] length 6, for QC drive
      - intent_vector: list[float] length 3
      - realm        : 'light_realm' | 'shadow_realm' | 'path'
      - tongue       : str (one of KO/AV/RU/CA/UM/DR)
      - content_bytes: bytes for QC drive storage
      - metrics      : dict from text_metrics()
    """
    text = note.text or ""
    metrics = text_metrics(text)
    intent = intent_from_metrics(metrics)

    # 2D position (deterministic from note_id)
    note_id = note.note_id or f"note-{index}"
    angle = 2.0 * math.pi * _blake2_unit(f"{note_id}|angle")
    radial = 0.05 + 0.67 * _blake2_unit(f"{note_id}|radius")
    x = math.cos(angle) * radial
    y = math.sin(angle) * radial

    # Phase
    if note.phase_rad is not None:
        phase = note.phase_rad
    else:
        phase = 2.0 * math.pi * _blake2_unit(f"{note_id}|phase")

    # 3D Poincare ball coordinate: (x, y, tanh(phase_norm))
    z_raw = math.tanh(phase / (2.0 * math.pi))
    norm = math.sqrt(x * x + y * y + z_raw * z_raw)
    if norm > 0.93:
        scale = 0.93 / max(norm, 1e-9)
        coord_3d = np.array([x * scale, y * scale, z_raw * scale])
    else:
        coord_3d = np.array([x, y, z_raw])

    # 6D tongue coordinates from intent + text metrics
    # KO=governance, AV=transport (word density), RU=policy (unique ratio),
    # CA=compute (digit ratio), UM=redaction (uppercase ratio), DR=integrity (punctuation)
    tongue_coords = [
        float(np.clip(intent[0], 0, 1)),  # KO
        float(np.clip(metrics["word_count"] / 600.0, 0, 1)),  # AV
        float(np.clip(metrics["unique_ratio"], 0, 1)),  # RU
        float(np.clip(metrics["digit_ratio"] * 10, 0, 1)),  # CA
        float(np.clip(metrics["uppercase_ratio"] * 5, 0, 1)),  # UM
        float(np.clip(metrics["punctuation_ratio"] * 8, 0, 1)),  # DR
    ]

    # Realm classification from intent balance
    governance, research, cohesion = intent
    if governance > 0.6:
        realm = "light_realm"
    elif research > governance + 0.15:
        realm = "shadow_realm"
    else:
        realm = "path"

    tongue = note.tongue if note.tongue in {"KO", "AV", "RU", "CA", "UM", "DR"} else "KO"

    return {
        "note_id": note_id,
        "coord_3d": coord_3d,
        "x": x,
        "y": y,
        "phase_rad": phase,
        "tongue_coords": tongue_coords,
        "intent_vector": intent,
        "realm": realm,
        "tongue": tongue,
        "content_bytes": text.encode("utf-8")[:4096],
        "metrics": metrics,
    }


def _mirror_coord(coord_3d: np.ndarray, intent: list[float]) -> Optional[np.ndarray]:
    """If any intent component is negative, mirror across those axes.

    Returns None if no negative components (no fold needed).
    """
    signs = [1.0 if v >= 0 else -1.0 for v in intent[:3]]
    if all(s >= 0 for s in signs):
        return None
    mirrored = coord_3d.copy()
    # Mirror across axes corresponding to negative intent
    # intent[0] → x, intent[1] → y, intent[2] → z
    for axis, sign in enumerate(signs):
        if sign < 0 and axis < 3:
            mirrored[axis] = -mirrored[axis]
    norm = np.linalg.norm(mirrored)
    if norm > 0.93:
        mirrored = mirrored / max(norm, 1e-9) * 0.93
    return mirrored


# --------------------------------------------------------------------------- #
#  Storage Bridge Lab
# --------------------------------------------------------------------------- #


@dataclass
class SurfaceReceipt:
    """What one surface returned for one record."""

    surface: str
    note_id: str
    stored: bool
    elapsed_us: int  # microseconds
    extra: dict = field(default_factory=dict)


@dataclass
class BridgeConfig:
    """Tunable knobs for the bridge lab."""

    # Octree
    octree_max_depth: int = 3
    octree_grid_size: int = 64
    # Lattice25D
    lattice_cell_size: float = 0.5
    lattice_index_mode: str = "hybrid"
    lattice_quadtree_capacity: int = 12
    lattice_max_depth: int = 6
    # QC Drive
    qc_resolution: int = 64
    # Sphere
    sphere_sparsity: float = 0.01
    # Fold
    negative_fold: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "octree_max_depth": self.octree_max_depth,
            "octree_grid_size": self.octree_grid_size,
            "lattice_cell_size": self.lattice_cell_size,
            "lattice_index_mode": self.lattice_index_mode,
            "lattice_quadtree_capacity": self.lattice_quadtree_capacity,
            "lattice_max_depth": self.lattice_max_depth,
            "qc_resolution": self.qc_resolution,
            "sphere_sparsity": self.sphere_sparsity,
            "negative_fold": self.negative_fold,
        }


class StorageBridgeLab:
    """Experimental multi-surface storage bridge.

    One NoteRecord → shared geometry → fan out to all 4 surfaces → collect metrics.
    """

    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()

        self.octree = HyperbolicOctree(
            grid_size=self.config.octree_grid_size,
            max_depth=self.config.octree_max_depth,
        )
        self.lattice = HyperbolicLattice25D(
            cell_size=self.config.lattice_cell_size,
            max_depth=self.config.lattice_max_depth,
            index_mode=self.config.lattice_index_mode,
            quadtree_capacity=self.config.lattice_quadtree_capacity,
        )
        self.qc_drive = QuasiCrystalVoxelDrive(
            resolution=self.config.qc_resolution,
        )
        self.sphere = ScatteredAttentionSphere(
            sparsity_threshold=self.config.sphere_sparsity,
        )

        self._ingested: list[dict[str, Any]] = []
        self._receipts: list[SurfaceReceipt] = []
        self._fold_count = 0
        self._feature_rows: list[list[float]] = []  # for sphere batch scatter

    @property
    def record_count(self) -> int:
        return len(self._ingested)

    def ingest(self, note: NoteRecord) -> list[SurfaceReceipt]:
        """Feed one NoteRecord into all four surfaces.

        Returns one SurfaceReceipt per surface (4, or 5 if fold fires).
        """
        index = len(self._ingested)
        geo = _note_to_geometry(note, index)
        self._ingested.append(geo)
        receipts: list[SurfaceReceipt] = []

        # ---- 1. HyperbolicOctree ----
        t0 = time.perf_counter_ns()
        self.octree.insert(geo["coord_3d"], geo["realm"])
        elapsed = (time.perf_counter_ns() - t0) // 1000
        receipts.append(
            SurfaceReceipt(
                surface="octree",
                note_id=geo["note_id"],
                stored=True,
                elapsed_us=elapsed,
                extra={"realm": geo["realm"], "coord_3d": geo["coord_3d"].tolist()},
            )
        )

        # Optional negative-vector fold
        if self.config.negative_fold:
            mirrored = _mirror_coord(geo["coord_3d"], geo["intent_vector"])
            if mirrored is not None:
                t0 = time.perf_counter_ns()
                self.octree.insert(mirrored, "shadow_realm")
                elapsed_fold = (time.perf_counter_ns() - t0) // 1000
                self._fold_count += 1
                receipts.append(
                    SurfaceReceipt(
                        surface="octree_fold",
                        note_id=geo["note_id"],
                        stored=True,
                        elapsed_us=elapsed_fold,
                        extra={"mirrored_coord": mirrored.tolist()},
                    )
                )

        # ---- 2. HyperbolicLattice25D ----
        t0 = time.perf_counter_ns()
        bundle = self.lattice.insert_bundle(
            x=geo["x"],
            y=geo["y"],
            phase_rad=geo["phase_rad"],
            tongue=geo["tongue"],
            authority=note.authority or "public",
            intent_vector=list(geo["intent_vector"]),
            intent_label=geo["note_id"][:48],
            bundle_id=f"bridge_{index:04d}",
            wavelength_nm=550.0,
        )
        elapsed = (time.perf_counter_ns() - t0) // 1000
        receipts.append(
            SurfaceReceipt(
                surface="lattice25d",
                note_id=geo["note_id"],
                stored=True,
                elapsed_us=elapsed,
                extra={"bundle_id": bundle.bundle_id, "tongue": bundle.tongue},
            )
        )

        # ---- 3. QuasiCrystalVoxelDrive ----
        t0 = time.perf_counter_ns()
        cell = self.qc_drive.store(
            chunk_id=f"bridge_{index:04d}",
            content=geo["content_bytes"],
            tongue_coords=geo["tongue_coords"],
            category=geo["realm"],
        )
        elapsed = (time.perf_counter_ns() - t0) // 1000
        receipts.append(
            SurfaceReceipt(
                surface="qc_drive",
                note_id=geo["note_id"],
                stored=True,
                elapsed_us=elapsed,
                extra={
                    "cell_id": cell.cell_id,
                    "chladni_mode": list(cell.chladni_mode),
                    "phase": cell.phase,
                },
            )
        )

        # ---- 4. ScatteredAttentionSphere (accumulate feature row) ----
        # The sphere takes 2D matrices. We accumulate a feature row per note
        # and scatter the batch when compare() is called.
        feature_row = list(geo["tongue_coords"]) + list(geo["intent_vector"])
        self._feature_rows.append(feature_row)
        receipts.append(
            SurfaceReceipt(
                surface="sphere",
                note_id=geo["note_id"],
                stored=True,
                elapsed_us=0,  # deferred until scatter
                extra={"feature_dim": len(feature_row)},
            )
        )

        self._receipts.extend(receipts)
        return receipts

    def ingest_batch(self, notes: Sequence[NoteRecord]) -> int:
        """Ingest a batch of notes. Returns count ingested."""
        for note in notes:
            self.ingest(note)
        return len(notes)

    def _flush_sphere(self) -> dict[str, Any]:
        """Scatter accumulated feature rows into the sphere."""
        if not self._feature_rows:
            return {"total_points": 0, "layers": []}

        matrix = np.array(self._feature_rows, dtype=float)
        t0 = time.perf_counter_ns()
        count = self.sphere.scatter(matrix, layer_name="bridge_notes", layer_radius=1.0)
        elapsed_us = (time.perf_counter_ns() - t0) // 1000
        return {
            "scattered_points": count,
            "matrix_shape": list(matrix.shape),
            "scatter_elapsed_us": elapsed_us,
            **self.sphere.stats(),
        }

    def compare(self) -> dict[str, Any]:
        """Collect stats from all 4 surfaces and compute comparison metrics."""
        n = max(1, self.record_count)

        # Flush sphere
        sphere_stats = self._flush_sphere()

        # Octree stats
        oct_stats = self.octree.stats()
        oct_nodes = oct_stats["node_count"] + oct_stats["leaf_count"]

        # Lattice stats
        lat_stats = self.lattice.stats()
        lat_nodes = lat_stats["occupied_cells"] + lat_stats["octree_voxel_count"]
        qt = lat_stats.get("quadtree", {})
        lat_nodes += qt.get("node_count", 0)

        # QC drive stats
        qc_stats = self.qc_drive.stats()

        # Overlap heat: fraction of lattice cells with >1 bundle
        overlap_cells = self.lattice.overlapping_cells()
        total_occupied = max(1, lat_stats["occupied_cells"])
        overlap_heat = len(overlap_cells) / total_occupied

        # Governance trace: can we look up a random ingested record in each surface?
        trace_hits = {"octree": 0, "lattice25d": 0, "qc_drive": 0}
        for geo in self._ingested[: min(20, n)]:
            if self.octree.query(geo["coord_3d"]) is not None:
                trace_hits["octree"] += 1
            # Lattice: query_nearest returns results if stored
            nearest = self.lattice.query_nearest(
                geo["x"],
                geo["y"],
                geo["phase_rad"],
                intent_vector=list(geo["intent_vector"]),
                tongue=geo["tongue"],
                top_k=1,
            )
            if nearest:
                trace_hits["lattice25d"] += 1
            # QC: check cell exists
            idx = self._ingested.index(geo)
            cid = f"bridge_{idx:04d}"
            if cid in self.qc_drive.cells:
                trace_hits["qc_drive"] += 1

        trace_sample = min(20, n)
        trace_rate = {surface: hits / max(1, trace_sample) for surface, hits in trace_hits.items()}

        # Sphere: band sweep for tongue distribution
        sweep_results = self.sphere.sweep(steps=6) if sphere_stats.get("total_points", 0) > 0 else []
        tongue_evenness = 0.0
        if sweep_results:
            # Average across sweeps: how evenly distributed are tongues?
            for band in sweep_results:
                dist = band.tongue_distribution
                if dist:
                    values = list(dist.values())
                    total = sum(values)
                    if total > 0:
                        probs = [v / total for v in values]
                        # Normalized entropy (0 = degenerate, 1 = perfectly even)
                        entropy = -sum(p * math.log(p + 1e-12) for p in probs)
                        max_entropy = math.log(max(1, len(probs)))
                        tongue_evenness += entropy / max(max_entropy, 1e-9)
            tongue_evenness /= max(1, len(sweep_results))

        return {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "config": self.config.to_dict(),
            "record_count": n,
            "fold_count": self._fold_count,
            "surfaces": {
                "octree": {
                    "node_count": oct_nodes,
                    "point_count": oct_stats["point_count"],
                    "occupied_voxels": oct_stats["occupied_voxels"],
                    "node_explosion": round(oct_nodes / n, 4),
                    "compaction_score": round(oct_stats["point_count"] / max(1, oct_nodes), 6),
                },
                "lattice25d": {
                    "node_count": lat_nodes,
                    "bundle_count": lat_stats["bundle_count"],
                    "occupied_cells": lat_stats["occupied_cells"],
                    "overlap_heat": round(overlap_heat, 4),
                    "node_explosion": round(lat_nodes / n, 4),
                    "compaction_score": round(lat_stats["bundle_count"] / max(1, lat_nodes), 6),
                },
                "qc_drive": {
                    "total_cells": qc_stats["total_cells"],
                    "total_bytes": qc_stats["total_content_bytes"],
                    "node_explosion": round(qc_stats["total_cells"] / n, 4),
                    "compaction_score": round(n / max(1, qc_stats["total_cells"]), 6),
                },
                "sphere": {
                    "total_points": sphere_stats.get("total_points", 0),
                    "scattered_points": sphere_stats.get("scattered_points", 0),
                    "tongue_evenness": round(tongue_evenness, 4),
                    "node_explosion": round(sphere_stats.get("total_points", 0) / n, 4),
                },
            },
            "governance_trace_rate": trace_rate,
            "summary": {
                "best_compaction": max(
                    ("octree", oct_stats["point_count"] / max(1, oct_nodes)),
                    ("lattice25d", lat_stats["bundle_count"] / max(1, lat_nodes)),
                    ("qc_drive", n / max(1, qc_stats["total_cells"])),
                    key=lambda pair: pair[1],
                )[0],
                "lowest_node_explosion": min(
                    ("octree", oct_nodes / n),
                    ("lattice25d", lat_nodes / n),
                    ("qc_drive", qc_stats["total_cells"] / n),
                    ("sphere", sphere_stats.get("total_points", 0) / n),
                    key=lambda pair: pair[1],
                )[0],
                "best_governance_trace": max(trace_rate.items(), key=lambda pair: pair[1])[0] if trace_rate else "none",
            },
        }

    def export(self, path: Optional[str] = None) -> str:
        """Export comparison results to JSON artifact."""
        report = self.compare()
        report["hypothesis_deck"] = get_hypothesis_deck()

        if path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            out_path = ARTIFACT_DIR / f"{ts}-bridge-comparison.json"
        else:
            out_path = Path(path)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        return str(out_path)


# --------------------------------------------------------------------------- #
#  Workload generators
# --------------------------------------------------------------------------- #


def build_bridge_workload(
    seed: int = 42,
    count: int = 24,
) -> list[NoteRecord]:
    """Create a deterministic workload that exercises all realms and tongues."""
    import random

    rng = random.Random(seed)
    tongues = ("KO", "AV", "RU", "CA", "UM", "DR")
    authorities = ("public", "sealed", "pilot")
    templates = [
        "Swarm navigation checkpoint with decimal drift residual.",
        "Council review notes with multi-model vote deltas and risk tags.",
        "Research summary with arXiv citations and geometric routing constraints.",
        "Deployment lane notes for n8n callback integrity and queue throughput.",
        "Negative intent probe with adversarial token patterns for shadow routing.",
        "Sacred Tongue resonance test with phi-weighted harmonic alignment.",
        "Storage compaction hypothesis: octree depth vs cell size tradeoff.",
        "Governance audit trail for multi-agent consensus on sealed resources.",
    ]

    notes: list[NoteRecord] = []
    for idx in range(count):
        text = f"{templates[idx % len(templates)]} Record {idx} seed {seed}."
        # Add some variance in text length and content
        if idx % 3 == 0:
            text += " Extended content with additional detail. " * rng.randint(1, 5)
        if idx % 5 == 0:
            text += f" URL: https://example.com/note/{idx}"
        if idx % 7 == 0:
            text += f" NUMERIC DATA: {rng.random():.6f} {rng.randint(100, 999)}"

        notes.append(
            NoteRecord(
                note_id=f"bridge-{seed}-{idx:04d}",
                text=text,
                tags=("bridge-lab", f"batch-{seed}"),
                source="bridge-lab",
                authority=authorities[idx % len(authorities)],
                tongue=tongues[idx % len(tongues)],
                phase_rad=(idx * 0.52) % (2.0 * math.pi),
            )
        )

    return notes


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run multi-surface storage bridge comparison.")
    parser.add_argument("--count", type=int, default=24, help="Number of notes to ingest")
    parser.add_argument("--seed", type=int, default=42, help="Workload seed")
    parser.add_argument("--no-fold", action="store_true", help="Disable negative-vector fold")
    parser.add_argument("--output-json", default="", help="Explicit output path")
    args = parser.parse_args(argv)

    config = BridgeConfig(negative_fold=not args.no_fold)
    lab = StorageBridgeLab(config)

    notes = build_bridge_workload(seed=args.seed, count=args.count)
    lab.ingest_batch(notes)

    path = lab.export(args.output_json or None)
    print(f"Exported: {path}")

    report = lab.compare()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
