"""Tri-Lattice Sphere Membrane — Three Lattices + Spherical Feedback
====================================================================

Experiment: wire the three existing lattice structures through a
shared spherical membrane and see what happens.

The three lattices:
  1. DualLatticeCrossStitch — intent-aware routing, light/shadow realms
  2. QuasicrystalLattice — 6D→3D+3D cut-and-project, acceptance window
  3. HyperbolicLattice25D — 2.5D cyclic phase bundles, overlap tracking

The sphere membrane:
  ScatteredAttentionSphere — inscribes all three, provides circular
  feedback path for information that doesn't fit any single lattice.

Intersection points:
  CrossStitch ↔ Quasicrystal: 6D tongue vectors shared
  CrossStitch ↔ Lattice25D: intent vectors + tongue assignment shared
  Quasicrystal ↔ Lattice25D: acceptance window = routing threshold

Circular feedback:
  Records that exit one lattice (rejected or overflow) feed back
  through the sphere membrane and re-enter via a different lattice.
  The sphere's band-of-focus determines which lattice receives
  the feedback packet.

Polyhedra fallback:
  When all three lattices reject a record (frustration), it falls
  through to the polyhedral path — a reliable, simple store that
  always accepts. Not fast, not clever, but never fails.

Method: mix everything → run → strip to bits → reassemble best version.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from hydra.octree_sphere_grid import HyperbolicLattice25D
from src.crypto.quasicrystal_lattice import (
    QuasicrystalLattice,
    LatticePoint as QCLatticePoint,
)
from src.kernel.scattered_sphere import ScatteredAttentionSphere, TONGUE_KEYS
from src.storage.langues_dispersal import (
    TONGUE_WEIGHTS,
    TONGUE_NAMES,
    quantize_spin,
    SpinVector,
    build_metric_tensor,
)

PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


# =========================================================================== #
#  Record types
# =========================================================================== #

@dataclass
class TriRecord:
    """A record flowing through the tri-lattice membrane."""
    record_id: str
    tongue_coords: List[float]  # 6D
    intent_vector: List[float]  # 3D
    tongue: str
    content: bytes
    # Routing metadata (filled during insert)
    accepted_by: str = ""           # which lattice accepted it
    rejected_by: List[str] = field(default_factory=list)
    feedback_hops: int = 0          # how many times it circled through membrane
    spin: Optional[SpinVector] = None
    qc_valid: Optional[bool] = None


@dataclass
class TriStats:
    """Stats from the tri-lattice membrane experiment."""
    total_records: int
    lattice25d_accepted: int
    quasicrystal_accepted: int
    sphere_feedback: int
    polyhedral_fallback: int
    rejection_count: int
    avg_feedback_hops: float
    frustration_count: int  # rejected by ALL lattices
    lattice25d_stats: Dict[str, Any]
    quasicrystal_stats: Dict[str, Any]
    sphere_stats: Dict[str, Any]
    spin_distribution: Dict[str, int]
    tongue_routing: Dict[str, int]


# =========================================================================== #
#  Polyhedral Fallback (always accepts, never fails)
# =========================================================================== #

class PolyhedralFallback:
    """Simple dict store. The reliable backup that always works."""

    def __init__(self):
        self.store: Dict[str, TriRecord] = {}

    def insert(self, record: TriRecord) -> None:
        self.store[record.record_id] = record

    def query(self, record_id: str) -> Optional[TriRecord]:
        return self.store.get(record_id)

    def stats(self) -> Dict[str, Any]:
        return {"type": "polyhedral_fallback", "count": len(self.store)}


# =========================================================================== #
#  Tri-Lattice Sphere Membrane
# =========================================================================== #

class TriLatticeMembrane:
    """Three lattices inscribed in a spherical membrane with circular feedback.

    Insert flow:
      1. Compute spin vector from tongue coords
      2. Try Lattice25D (phase/tongue bundles) — if spin is low magnitude
      3. Try QuasiCrystal (6D→3D acceptance window) — if QC accepts
      4. If both reject: sphere membrane circular feedback (re-route)
      5. If feedback fails: polyhedral fallback (always works)

    The sphere membrane provides non-linear routing between lattices.
    Information that doesn't fit lattice A can circle through the sphere
    and enter lattice B from a different angle.
    """

    def __init__(
        self,
        # Lattice25D params
        lattice_cell_size: float = 0.5,
        lattice_quadtree_capacity: int = 12,
        # QuasiCrystal params
        qc_acceptance_radius: float = 2.0,
        # Sphere params
        sphere_sparsity: float = 0.01,
        # Feedback
        max_feedback_hops: int = 2,
        # Leave these as variables — unsolved, adjustable
        membrane_permeability: float = 0.5,  # how easily records pass between lattices
        frustration_threshold: float = 0.7,  # when to give up and use fallback
    ):
        # The three lattices
        self.lattice25d = HyperbolicLattice25D(
            cell_size=lattice_cell_size,
            index_mode="hybrid",
            quadtree_capacity=lattice_quadtree_capacity,
        )
        self.quasicrystal = QuasicrystalLattice()
        self.sphere = ScatteredAttentionSphere(sparsity_threshold=sphere_sparsity)

        # Fallback
        self.fallback = PolyhedralFallback()

        # Config (variables, not constants — adjustable per experiment)
        self.max_feedback_hops = max_feedback_hops
        self.membrane_permeability = membrane_permeability
        self.frustration_threshold = frustration_threshold

        # State
        self._records: Dict[str, TriRecord] = {}
        self._centroid: Optional[List[float]] = None
        self._centroid_count = 0
        self._feature_rows: List[List[float]] = []
        self._sphere_scattered = False

        # Counters
        self._lattice25d_count = 0
        self._qc_count = 0
        self._feedback_count = 0
        self._fallback_count = 0
        self._frustration_count = 0
        self._rejection_count = 0
        self._tongue_routing: Dict[str, int] = {t: 0 for t in TONGUES}

    def _update_centroid(self, tongue_coords: List[float]) -> None:
        """Running centroid update."""
        tc = np.array(tongue_coords, dtype=float)
        if self._centroid is None:
            self._centroid = tc.tolist()
            self._centroid_count = 1
        else:
            n = self._centroid_count + 1
            self._centroid = [
                (c * self._centroid_count + t) / n
                for c, t in zip(self._centroid, tongue_coords)
            ]
            self._centroid_count = n

    def _try_lattice25d(self, record: TriRecord, index: int) -> bool:
        """Try inserting into Lattice25D. Returns True if accepted."""
        try:
            # Derive 2D position from tongue coords
            angle = 2.0 * math.pi * (hash(record.record_id) % 10000) / 10000
            radial = 0.05 + 0.67 * (hash(record.record_id + "r") % 10000) / 10000
            x = math.cos(angle) * radial
            y = math.sin(angle) * radial
            phase = sum(record.tongue_coords[:3]) % (2 * math.pi)

            self.lattice25d.insert_bundle(
                x=x, y=y, phase_rad=phase,
                tongue=record.tongue,
                authority="public",
                intent_vector=record.intent_vector,
                intent_label=record.record_id[:48],
                bundle_id=f"tri_{index:06d}",
                wavelength_nm=550.0,
            )
            return True
        except Exception:
            return False

    def _try_quasicrystal(self, record: TriRecord) -> bool:
        """Try the quasicrystal acceptance window. Returns True if valid."""
        try:
            # Convert float coords to integer gate vector (scale by 10)
            gate = [max(1, int(abs(c) * 10)) for c in record.tongue_coords]
            point = self.quasicrystal.project_point(gate)
            record.qc_valid = point.is_valid
            return point.is_valid
        except Exception:
            return False

    def _sphere_feedback(self, record: TriRecord) -> str:
        """Route through sphere membrane. Returns suggested target lattice."""
        # Accumulate feature row
        feature = record.tongue_coords + record.intent_vector
        self._feature_rows.append(feature)
        self._sphere_scattered = False

        # Use spin vector to determine routing
        if record.spin is None:
            centroid = self._centroid or [0.5] * 6
            record.spin = quantize_spin(record.tongue_coords, centroid, threshold=0.03)

        # Routing decision based on spin pattern
        magnitude = record.spin.magnitude
        if magnitude <= 2:
            return "lattice25d"  # low spin → structured lattice
        elif magnitude >= 5:
            return "quasicrystal"  # high spin → strict acceptance window
        else:
            # Middle ground: use dominant tongue to decide
            weighted = [abs(c) * w for c, w in zip(record.tongue_coords, TONGUE_WEIGHTS)]
            dom_idx = weighted.index(max(weighted))
            # Low-weight tongues (KO, AV, RU) → lattice25d
            # High-weight tongues (CA, UM, DR) → quasicrystal
            return "quasicrystal" if dom_idx >= 3 else "lattice25d"

    def insert(self, record: TriRecord) -> TriRecord:
        """Insert a record through the tri-lattice membrane.

        Flow: try lattice25d → try quasicrystal → sphere feedback → fallback
        """
        index = len(self._records)
        self._update_centroid(record.tongue_coords)

        # Compute spin
        centroid = self._centroid or [0.5] * 6
        record.spin = quantize_spin(record.tongue_coords, centroid, threshold=0.03)

        # Track tongue routing
        self._tongue_routing[record.tongue] = self._tongue_routing.get(record.tongue, 0) + 1

        # -----------------------------------------------------------
        # SPIN-BASED ROUTING (not try-and-fallback order)
        #
        # Spin magnitude determines which lattice gets first attempt:
        #   Low spin (0-2):  Lattice25D  (loose, overlap-tolerant)
        #   Mid spin (3-4):  Quasicrystal (structured, acceptance gated)
        #   High spin (5-6): Quasicrystal first, then Lattice25D
        #
        # This prevents Lattice25D from greedily eating everything.
        # -----------------------------------------------------------
        magnitude = record.spin.magnitude

        if magnitude <= 2:
            # Low spin: Lattice25D is the right home
            primary, secondary = "lattice25d", "quasicrystal"
        elif magnitude >= 5:
            # High spin: Quasicrystal's strict acceptance is appropriate
            primary, secondary = "quasicrystal", "lattice25d"
        else:
            # Mid spin: use dominant tongue weight to decide
            weighted = [abs(c) * w for c, w in zip(record.tongue_coords, TONGUE_WEIGHTS)]
            dom_idx = weighted.index(max(weighted))
            if dom_idx >= 3:  # CA, UM, DR → high-security tongues → quasicrystal
                primary, secondary = "quasicrystal", "lattice25d"
            else:
                primary, secondary = "lattice25d", "quasicrystal"

        # Attempt 1: Primary lattice
        if primary == "lattice25d" and self._try_lattice25d(record, index):
            record.accepted_by = "lattice25d"
            self._lattice25d_count += 1
            self._records[record.record_id] = record
            return record
        elif primary == "quasicrystal" and self._try_quasicrystal(record):
            record.accepted_by = "quasicrystal"
            self._qc_count += 1
            self._records[record.record_id] = record
            return record

        record.rejected_by.append(primary)
        self._rejection_count += 1

        # Attempt 2: Secondary lattice
        if secondary == "lattice25d" and self._try_lattice25d(record, index):
            record.accepted_by = "lattice25d"
            self._lattice25d_count += 1
            self._records[record.record_id] = record
            return record
        elif secondary == "quasicrystal" and self._try_quasicrystal(record):
            record.accepted_by = "quasicrystal"
            self._qc_count += 1
            self._records[record.record_id] = record
            return record

        record.rejected_by.append(secondary)
        self._rejection_count += 1

        # Attempt 3: Sphere membrane feedback loop
        for hop in range(self.max_feedback_hops):
            record.feedback_hops = hop + 1
            target = self._sphere_feedback(record)
            self._feedback_count += 1

            if target == "lattice25d" and self._try_lattice25d(record, index + hop + 1000):
                record.accepted_by = f"lattice25d_feedback_{hop+1}"
                self._lattice25d_count += 1
                self._records[record.record_id] = record
                return record

            if target == "quasicrystal" and self._try_quasicrystal(record):
                record.accepted_by = f"quasicrystal_feedback_{hop+1}"
                self._qc_count += 1
                self._records[record.record_id] = record
                return record

        # Attempt 4: Polyhedral fallback (always works)
        record.accepted_by = "polyhedral_fallback"
        self._fallback_count += 1
        self._frustration_count += 1
        self.fallback.insert(record)
        self._records[record.record_id] = record
        return record

    def insert_batch(self, records: List[TriRecord]) -> int:
        for r in records:
            self.insert(r)
        return len(records)

    def _flush_sphere(self) -> Dict[str, Any]:
        """Scatter accumulated features into sphere for analysis."""
        if not self._feature_rows or self._sphere_scattered:
            return self.sphere.stats()
        matrix = np.array(self._feature_rows, dtype=float)
        self.sphere.scatter(matrix, "tri_membrane", layer_radius=1.0)
        self._sphere_scattered = True
        return self.sphere.stats()

    def stats(self) -> TriStats:
        total = len(self._records)
        sphere_stats = self._flush_sphere()

        # Spin distribution
        spin_dist: Dict[str, int] = {}
        for r in self._records.values():
            if r.spin:
                code = r.spin.code
                spin_dist[code] = spin_dist.get(code, 0) + 1

        return TriStats(
            total_records=total,
            lattice25d_accepted=self._lattice25d_count,
            quasicrystal_accepted=self._qc_count,
            sphere_feedback=self._feedback_count,
            polyhedral_fallback=self._fallback_count,
            rejection_count=self._rejection_count,
            avg_feedback_hops=round(
                sum(r.feedback_hops for r in self._records.values()) / max(1, total), 2
            ),
            frustration_count=self._frustration_count,
            lattice25d_stats=self.lattice25d.stats(),
            quasicrystal_stats={"type": "quasicrystal", "points_tested": self._qc_count + self._rejection_count},
            sphere_stats=sphere_stats,
            spin_distribution=dict(sorted(spin_dist.items(), key=lambda x: -x[1])[:20]),
            tongue_routing=self._tongue_routing,
        )
