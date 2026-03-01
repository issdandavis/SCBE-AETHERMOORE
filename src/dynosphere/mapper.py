"""
Dynosphere Mapper — 3D Sphere ↔ Sacred Tongues ↔ 21D Canonical State
=====================================================================

Maps dynosphere 3D coordinates through Sacred Tongue projections
into the 21D Unified Brain State, with round-trip fidelity.

The mapping chain:
  3D unit sphere → 6 phi-weighted tongue projections → 21D canonical lift

Each Sacred Tongue has a basis direction on the unit sphere:
  KO → (1, 0, 0)          AV → (cos60, sin60, 0)
  RU → (cos120, sin120, 0) CA → (-1, 0, 0)
  UM → (cos240, sin240, 0) DR → (cos300, sin300, 0)

Tongue projections use the dot product with these basis directions,
weighted by the golden ratio scale (PHI^i).

The 21D lift populates a UnifiedBrainState:
  - SCBE Context (6D): tongue projections normalized to [0,1]
  - Navigation (6D): 3D position + spherical angles + radius
  - Cognitive (3D): PHDM polyhedra centroid mapping
  - Semantic (3D): dominant tongue phase info
  - Swarm (3D): cross-tongue coherence metrics

@layer L5, L6, L9, L12
@component Dynosphere.Mapper
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

import sys
from pathlib import Path

# Add project root for imports
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.geoseed.sphere_grid import (
    TONGUE_NAMES,
    TONGUE_PHASES,
    PHI_WEIGHTS,
    PHI,
    SphereGrid,
    SphereGridNetwork,
    CL6,
    poincare_project,
    hyperbolic_distance,
)


# ---------------------------------------------------------------------------
# Tongue basis directions on the unit sphere (hexagonal arrangement in XY)
# ---------------------------------------------------------------------------

def _tongue_basis_directions() -> Dict[str, np.ndarray]:
    """Sacred Tongue basis directions on the 3D unit sphere.

    Arranged as a hexagon in the XY plane at angles matching TONGUE_PHASES.
    """
    directions = {}
    for tongue in TONGUE_NAMES:
        theta = TONGUE_PHASES[tongue]
        directions[tongue] = np.array([
            math.cos(theta),
            math.sin(theta),
            0.0,
        ])
    return directions


TONGUE_DIRECTIONS = _tongue_basis_directions()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TongueProjection:
    """Projection of a 3D point onto all 6 Sacred Tongue axes."""
    raw: Dict[str, float]       # dot products (can be negative)
    weighted: Dict[str, float]  # phi-weighted projections
    normalized: Dict[str, float]  # normalized to [0, 1]
    dominant: str               # tongue with highest weighted projection
    affinity_vector: np.ndarray  # 6D vector of normalized projections


@dataclass(frozen=True)
class CanonicalLift:
    """Result of lifting tongue projections to 21D canonical state."""
    state_21d: np.ndarray       # full 21D vector
    poincare_point: np.ndarray  # Poincaré ball embedding
    tongue_projection: TongueProjection
    source_3d: np.ndarray       # original 3D point
    braid_phase: Tuple[int, int]  # dual ternary phase state


@dataclass(frozen=True)
class DynospherePoint:
    """A point on the dynosphere surface with all coordinate representations."""
    position_3d: np.ndarray     # unit sphere position
    spherical: Tuple[float, float]  # (theta, phi) angles
    tongue_proj: TongueProjection
    canonical: CanonicalLift
    polyhedron_face: int        # PHDM polyhedra face index (0-15)


# ---------------------------------------------------------------------------
# PHDM Polyhedra Mapping (16 cognitive polyhedra → dynosphere faces)
# ---------------------------------------------------------------------------

# 16 PHDM polyhedra map to regions of the dynosphere.
# Each polyhedron corresponds to a cognitive archetype.
PHDM_POLYHEDRA = [
    "analyst", "strategist", "empath", "guardian",
    "creator", "mediator", "explorer", "catalyst",
    "sentinel", "harmonizer", "visionary", "architect",
    "sage", "challenger", "diplomat", "pioneer",
]

# Icosahedron has 20 faces; first 16 map to PHDM polyhedra.
# We assign faces by partitioning the sphere into 16 sectors.
def _polyhedra_centroids() -> np.ndarray:
    """Generate 16 evenly-distributed centroids on the sphere (Fibonacci lattice)."""
    n = 16
    centroids = np.zeros((n, 3))
    golden_angle = math.pi * (3 - math.sqrt(5))  # ~2.4 radians
    for i in range(n):
        y = 1 - (2 * i / (n - 1))
        radius = math.sqrt(1 - y * y)
        theta = golden_angle * i
        centroids[i] = [radius * math.cos(theta), radius * math.sin(theta), y]
    # Normalize
    norms = np.linalg.norm(centroids, axis=1, keepdims=True)
    return centroids / np.maximum(norms, 1e-12)


POLYHEDRA_CENTROIDS = _polyhedra_centroids()


def nearest_polyhedron(point_3d: np.ndarray) -> int:
    """Find the nearest PHDM polyhedron face for a 3D point."""
    point = point_3d / max(np.linalg.norm(point_3d), 1e-12)
    dots = POLYHEDRA_CENTROIDS @ point
    return int(np.argmax(dots))


# ---------------------------------------------------------------------------
# Core projection functions
# ---------------------------------------------------------------------------

def project_to_tongues(point_3d: np.ndarray) -> TongueProjection:
    """Project a 3D unit-sphere point onto all 6 Sacred Tongue axes.

    Each tongue has a basis direction. The projection is the dot product
    of the point with that direction, weighted by PHI^i.

    Args:
        point_3d: 3D position (will be normalized to unit sphere).

    Returns:
        TongueProjection with raw, weighted, and normalized projections.
    """
    point = np.asarray(point_3d, dtype=float)
    norm = np.linalg.norm(point)
    if norm > 1e-12:
        point = point / norm

    raw = {}
    weighted = {}
    for tongue in TONGUE_NAMES:
        dot = float(np.dot(point, TONGUE_DIRECTIONS[tongue]))
        raw[tongue] = dot
        weighted[tongue] = dot * PHI_WEIGHTS[tongue]

    # Normalize: shift [-max_weight, max_weight] to [0, 1]
    w_vals = list(weighted.values())
    w_min = min(w_vals)
    w_max = max(w_vals)
    w_range = w_max - w_min if (w_max - w_min) > 1e-12 else 1.0

    normalized = {}
    for tongue in TONGUE_NAMES:
        normalized[tongue] = (weighted[tongue] - w_min) / w_range

    dominant = max(weighted, key=weighted.get)
    affinity = np.array([normalized[t] for t in TONGUE_NAMES])

    return TongueProjection(
        raw=raw,
        weighted=weighted,
        normalized=normalized,
        dominant=dominant,
        affinity_vector=affinity,
    )


def _to_spherical(point_3d: np.ndarray) -> Tuple[float, float]:
    """Convert 3D unit-sphere point to spherical (theta, phi)."""
    x, y, z = point_3d
    theta = math.acos(max(-1.0, min(1.0, z)))  # polar angle [0, pi]
    phi = math.atan2(y, x)  # azimuthal [-pi, pi]
    return theta, phi


def _compute_braid_phase(tongue_proj: TongueProjection) -> Tuple[int, int]:
    """Derive dual ternary phase state from tongue projections.

    Parallel trit: net projection in the dominant tongue axis direction
    Perpendicular trit: cross-tongue spread (variance of projections)

    Returns:
        (parallel_trit, perp_trit) each in {-1, 0, +1}
    """
    vals = list(tongue_proj.normalized.values())
    mean_val = sum(vals) / len(vals)
    dom_val = tongue_proj.normalized[tongue_proj.dominant]

    # Parallel: dominant tongue direction
    if dom_val > 0.7:
        par = 1
    elif dom_val < 0.3:
        par = -1
    else:
        par = 0

    # Perpendicular: variance of projections (spread)
    variance = sum((v - mean_val) ** 2 for v in vals) / len(vals)
    if variance > 0.1:
        perp = 1   # high differentiation → advancing
    elif variance < 0.03:
        perp = -1  # low differentiation → contracting
    else:
        perp = 0

    return (par, perp)


def _cross_tongue_coherence(tongue_proj: TongueProjection) -> Tuple[float, float, float]:
    """Compute cross-tongue coherence metrics for the swarm coordination block.

    Returns:
        (trust_score, byzantine_votes, spectral_coherence)
    """
    vals = np.array([tongue_proj.normalized[t] for t in TONGUE_NAMES])
    # Trust: mean projection strength
    trust = float(np.mean(vals))
    # Byzantine: how many tongues disagree with the dominant
    dom_val = tongue_proj.normalized[tongue_proj.dominant]
    disagreement = sum(1 for v in vals if abs(v - dom_val) > 0.5) / 6.0
    # Spectral coherence: 1 - normalized entropy
    vals_safe = np.clip(vals, 1e-10, 1.0)
    vals_normed = vals_safe / vals_safe.sum()
    entropy = -float(np.sum(vals_normed * np.log(vals_normed)))
    max_entropy = math.log(6)
    coherence = 1.0 - (entropy / max_entropy)

    return (trust, disagreement, coherence)


def lift_to_21d(
    point_3d: np.ndarray,
    tongue_proj: Optional[TongueProjection] = None,
) -> CanonicalLift:
    """Lift a 3D dynosphere point to 21D canonical brain state.

    Populates the 21D vector as:
      [0:6]   SCBE Context = tongue projections (normalized to [0,1])
      [6:9]   Navigation position = 3D coordinates
      [9]     Navigation time = 0
      [10]    Navigation priority = dominant tongue weight
      [11]    Navigation confidence = max projection
      [12:15] Cognitive = PHDM polyhedron centroid (3D)
      [15]    Semantic: active tongue index (normalized to [0,1])
      [16]    Semantic: phase angle of dominant tongue
      [17]    Semantic: tongue weight of dominant
      [18:21] Swarm: cross-tongue coherence metrics

    Args:
        point_3d: 3D position on unit sphere.
        tongue_proj: Pre-computed tongue projection (computed if None).

    Returns:
        CanonicalLift with full 21D state.
    """
    point = np.asarray(point_3d, dtype=float)
    norm = np.linalg.norm(point)
    if norm > 1e-12:
        point = point / norm

    if tongue_proj is None:
        tongue_proj = project_to_tongues(point)

    braid_phase = _compute_braid_phase(tongue_proj)
    poly_idx = nearest_polyhedron(point)
    poly_centroid = POLYHEDRA_CENTROIDS[poly_idx]
    trust, byz, coherence = _cross_tongue_coherence(tongue_proj)

    dom_idx = TONGUE_NAMES.index(tongue_proj.dominant)
    dom_phase = TONGUE_PHASES[tongue_proj.dominant]
    dom_weight = PHI_WEIGHTS[tongue_proj.dominant]
    # Normalize weight to [0,1] range
    max_phi = PHI_WEIGHTS["DR"]
    dom_weight_norm = dom_weight / max_phi

    state = np.zeros(21)
    # SCBE Context (6D) — tongue projections
    for i, tongue in enumerate(TONGUE_NAMES):
        state[i] = tongue_proj.normalized[tongue]
    # Navigation (6D) — 3D position + time + priority + confidence
    state[6:9] = point
    state[9] = 0.0  # time
    state[10] = dom_weight_norm  # priority
    state[11] = max(tongue_proj.normalized.values())  # confidence
    # Cognitive (3D) — PHDM polyhedron centroid
    state[12:15] = poly_centroid
    # Semantic (3D) — tongue phase info
    state[15] = dom_idx / 5.0  # active tongue [0, 1]
    state[16] = dom_phase / (2 * math.pi)  # phase angle [0, 1]
    state[17] = dom_weight_norm  # tongue weight
    # Swarm (3D) — cross-tongue coherence
    state[18] = trust
    state[19] = byz
    state[20] = coherence

    # Poincaré embedding
    poincare = poincare_project(state)

    return CanonicalLift(
        state_21d=state,
        poincare_point=poincare,
        tongue_projection=tongue_proj,
        source_3d=point.copy(),
        braid_phase=braid_phase,
    )


# ---------------------------------------------------------------------------
# Round-trip reconstruction: 21D → 3D
# ---------------------------------------------------------------------------

def reconstruct_3d_from_21d(state_21d: np.ndarray) -> np.ndarray:
    """Reconstruct the 3D dynosphere position from 21D canonical state.

    The 3D position is stored directly in state[6:9] (navigation block).
    This provides exact reconstruction for the round-trip test.

    Args:
        state_21d: 21D canonical state vector.

    Returns:
        3D unit-sphere position.
    """
    state = np.asarray(state_21d, dtype=float)
    point = state[6:9].copy()
    norm = np.linalg.norm(point)
    if norm > 1e-12:
        point = point / norm
    return point


def reconstruct_tongue_proj_from_21d(state_21d: np.ndarray) -> Dict[str, float]:
    """Reconstruct tongue normalized projections from 21D state.

    The tongue projections are stored in state[0:6].

    Args:
        state_21d: 21D canonical state vector.

    Returns:
        Dict mapping tongue name to normalized projection value.
    """
    state = np.asarray(state_21d, dtype=float)
    return {tongue: float(state[i]) for i, tongue in enumerate(TONGUE_NAMES)}


def round_trip_3d(point_3d: np.ndarray) -> Tuple[np.ndarray, float]:
    """Full round-trip: 3D → tongue projection → 21D → 3D reconstruction.

    Tests the fidelity of the mapping chain.

    Args:
        point_3d: Original 3D unit-sphere point.

    Returns:
        (reconstructed_3d, error_norm) where error is the L2 distance.
    """
    point = np.asarray(point_3d, dtype=float)
    norm = np.linalg.norm(point)
    if norm > 1e-12:
        point = point / norm

    canonical = lift_to_21d(point)
    reconstructed = reconstruct_3d_from_21d(canonical.state_21d)
    error = float(np.linalg.norm(point - reconstructed))
    return reconstructed, error


# ---------------------------------------------------------------------------
# DynosphereMapper — Main orchestrator
# ---------------------------------------------------------------------------

class DynosphereMapper:
    """Maps between 3D sphere, Sacred Tongue projections, and 21D canonical state.

    Wraps a SphereGridNetwork for full grid-level operations and provides
    point-level mapping functions.

    Usage:
        mapper = DynosphereMapper()
        point = mapper.map_point(np.array([0.5, 0.3, 0.8]))
        # point.canonical.state_21d is the 21D vector
        # point.tongue_proj.dominant is the strongest tongue
        # point.polyhedron_face is the PHDM face index
    """

    def __init__(self, resolution: int = 3, signal_dim: int = 64):
        self.network = SphereGridNetwork(resolution=resolution, signal_dim=signal_dim)
        self.resolution = resolution
        self.signal_dim = signal_dim

    def map_point(self, point_3d: np.ndarray) -> DynospherePoint:
        """Map a single 3D point through the full pipeline.

        Args:
            point_3d: 3D position (normalized to unit sphere).

        Returns:
            DynospherePoint with all coordinate representations.
        """
        point = np.asarray(point_3d, dtype=float)
        norm = np.linalg.norm(point)
        if norm > 1e-12:
            point = point / norm

        tongue_proj = project_to_tongues(point)
        canonical = lift_to_21d(point, tongue_proj)
        theta, phi = _to_spherical(point)
        poly_face = nearest_polyhedron(point)

        return DynospherePoint(
            position_3d=point,
            spherical=(theta, phi),
            tongue_proj=tongue_proj,
            canonical=canonical,
            polyhedron_face=poly_face,
        )

    def map_grid_vertex(self, tongue: str, vertex_idx: int) -> DynospherePoint:
        """Map a specific grid vertex from one tongue's sphere.

        Args:
            tongue: Sacred Tongue name.
            vertex_idx: Vertex index in that tongue's grid.

        Returns:
            DynospherePoint for that vertex.
        """
        grid = self.network.grids[tongue]
        pos = grid.vertices[vertex_idx]
        return self.map_point(pos)

    def deposit_and_propagate(
        self,
        point_3d: np.ndarray,
        signal: np.ndarray,
        n_steps: int = 1,
    ) -> Dict[str, np.ndarray]:
        """Deposit a signal on the dynosphere and propagate through the network.

        The signal is placed on the tongue grid closest to the point's
        dominant tongue direction.

        Args:
            point_3d: 3D position on unit sphere.
            signal: Signal vector (must match signal_dim).
            n_steps: Number of propagation steps.

        Returns:
            Dict mapping tongue → signal arrays after propagation.
        """
        point = np.asarray(point_3d, dtype=float)
        norm = np.linalg.norm(point)
        if norm > 1e-12:
            point = point / norm

        tongue_proj = project_to_tongues(point)
        self.network.deposit(tongue_proj.dominant, point, signal)
        return self.network.forward(n_steps)

    def batch_map(self, points: np.ndarray) -> List[DynospherePoint]:
        """Map multiple 3D points through the pipeline.

        Args:
            points: (N, 3) array of 3D positions.

        Returns:
            List of DynospherePoint for each input.
        """
        return [self.map_point(p) for p in points]

    def global_state_21d(self) -> np.ndarray:
        """Read the full network state as a flattened 21D-compatible summary.

        Takes the 6*signal_dim global embedding and projects to 21D
        by averaging each tongue's mean signal into the corresponding
        SCBE Context dimension.

        Returns:
            21D summary vector.
        """
        global_embed = self.network.read_global_state()  # (6 * signal_dim,)
        state = np.zeros(21)
        # SCBE Context: mean of each tongue's signal norm
        for i, tongue in enumerate(TONGUE_NAMES):
            chunk = global_embed[i * self.signal_dim : (i + 1) * self.signal_dim]
            state[i] = float(np.linalg.norm(chunk)) / math.sqrt(self.signal_dim)
        # Remaining dims stay zero (network doesn't populate them)
        return state

    def diagnostics(self) -> Dict:
        """Return diagnostic info about the mapper state."""
        return {
            "resolution": self.resolution,
            "signal_dim": self.signal_dim,
            "total_nodes": self.network.total_nodes,
            "tongue_pairs": len(self.network.tongue_pairs),
            "polyhedra_count": len(PHDM_POLYHEDRA),
            "grids": {
                t: {
                    "vertices": g.n_vertices,
                    "edges": len(g.edges),
                    "signal_energy": float(np.sum(g.signals ** 2)),
                }
                for t, g in self.network.grids.items()
            },
        }
