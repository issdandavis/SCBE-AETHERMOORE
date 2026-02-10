"""
Cymatic Voxel Neural Network (Python Reference)
================================================

6D Chladni-based voxel neural network with nodal/negative-space storage
and auto-propagation along nodal contours.

Architecture:
  6D Chladni Equation (3 paired-dimension terms):
    C(x, s) = Sum_i [cos(s_2i*pi*x_2i)*cos(s_2i+1*pi*x_2i+1)
                    - cos(s_2i+1*pi*x_2i)*cos(s_2i*pi*x_2i+1)]

  Storage Topology:
    Nodal (|C| < eps):       Visible, directly addressable voxels
    Negative Space (|C| >= eps): Hidden, encrypted voxels (anti-nodal)
    Implied Boundary:        Soft contours where C transitions sign

  Neural Propagation:
    Neurons at nodal points connect via implied boundaries.
    Activation propagates along Chladni zero-sets, modulated by
    harmonic scaling and Poincare hyperbolic distance.

@module ai_brain/cymatic_voxel_net
@layer Layer 5, Layer 8, Layer 12, Layer 14
@version 1.0.0
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

from .unified_state import BRAIN_EPSILON, PHI
from .tri_manifold_lattice import harmonic_scale, HARMONIC_R

# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

SACRED_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
"""The six Sacred Tongues (semantic encoding layers)."""

TONGUE_DIMENSION_MAP = {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5}
"""Tongue-to-dimension mapping (each tongue governs one coordinate)."""

REALM_CENTERS = {
    "KO": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "AV": [0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
    "RU": [0.0, 0.4, 0.2, 0.0, 0.0, 0.0],
    "CA": [-0.2, -0.3, 0.4, 0.1, 0.0, 0.0],
    "UM": [0.0, 0.0, -0.5, 0.3, 0.2, 0.0],
    "DR": [0.1, -0.2, 0.0, -0.4, 0.3, 0.1],
}
"""Realm centers in 6D Poincare ball (one per tongue)."""

NODAL_THRESHOLD = 1e-3
"""Default Chladni nodal threshold."""

VOXEL_DIMS = 6
"""Voxel spatial dimensions."""

VoxelZone = Literal["nodal", "negative_space", "implied_boundary"]


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class CymaticVoxel:
    """A single voxel in the cymatic lattice."""

    coords: List[float]
    chladni_value: float
    chladni_abs: float
    zone: str
    tongue: str
    embedded: List[float]
    realm_distance: float
    payload: Optional[bytes] = None


@dataclass
class VoxelActivation:
    """Neural activation at a voxel node."""

    voxel_index: int
    strength: float
    tongue: str
    generation: int
    harmonic_cost: float


@dataclass
class NetSnapshot:
    """Network statistics snapshot."""

    total_voxels: int
    nodal_count: int
    negative_space_count: int
    boundary_count: int
    nodal_fraction: float
    negative_space_fraction: float
    mean_chladni_abs: float
    storage_capacity: Dict[str, int]


# ═══════════════════════════════════════════════════════════════
# 6D Chladni Equation
# ═══════════════════════════════════════════════════════════════


def chladni_6d(coords: List[float], state: List[float]) -> float:
    """6D Chladni equation: generalization of the 2D Chladni plate pattern.

    C(x, s) = Sum_{i=0}^{2} [cos(s_{2i}*pi*x_{2i})*cos(s_{2i+1}*pi*x_{2i+1})
                             - cos(s_{2i+1}*pi*x_{2i})*cos(s_{2i}*pi*x_{2i+1})]

    Args:
        coords: 6D voxel coordinates [x_0..x_5].
        state: 6D mode parameters [s_0..s_5].

    Returns:
        Chladni field value (0 at nodal lines).
    """
    total = 0.0
    for i in range(3):
        s2i = state[2 * i] if 2 * i < len(state) else 1.0
        s2i1 = state[2 * i + 1] if 2 * i + 1 < len(state) else 1.0
        x2i = coords[2 * i] if 2 * i < len(coords) else 0.0
        x2i1 = coords[2 * i + 1] if 2 * i + 1 < len(coords) else 0.0

        total += (
            math.cos(s2i * math.pi * x2i) * math.cos(s2i1 * math.pi * x2i1)
            - math.cos(s2i1 * math.pi * x2i) * math.cos(s2i * math.pi * x2i1)
        )
    return total


def classify_zone(
    chladni_value: float,
    nodal_threshold: float = NODAL_THRESHOLD,
    boundary_width: float = 0.05,
) -> str:
    """Classify a coordinate based on its Chladni field value."""
    abs_val = abs(chladni_value)
    if abs_val < nodal_threshold:
        return "nodal"
    if abs_val < nodal_threshold + boundary_width:
        return "implied_boundary"
    return "negative_space"


def dominant_tongue(coords: List[float]) -> str:
    """Determine which Sacred Tongue governs a given 6D coordinate.

    The tongue is assigned by the dimension with the largest absolute value.
    """
    max_idx = 0
    max_val = 0.0
    for i in range(min(len(coords), 6)):
        abs_val = abs(coords[i])
        if abs_val > max_val:
            max_val = abs_val
            max_idx = i
    return SACRED_TONGUES[max_idx]


def estimate_nodal_density(
    state: List[float],
    samples: int = 10000,
    threshold: float = NODAL_THRESHOLD,
) -> float:
    """Estimate the fraction of coordinates that fall on nodal lines."""
    nodal = 0
    for _ in range(samples):
        coords = [random.random() * 2 - 1 for _ in range(6)]
        if abs(chladni_6d(coords, state)) < threshold:
            nodal += 1
    return nodal / samples


# ═══════════════════════════════════════════════════════════════
# Poincare Helpers (6D)
# ═══════════════════════════════════════════════════════════════


def _poincare_embed_6d(v: List[float]) -> List[float]:
    """Embed a 6D vector into the Poincare ball using tanh normalization.

    embed(v) = tanh(||v||/2) * v/||v||, clamped to max norm 0.999.
    """
    norm = math.sqrt(sum(x * x for x in v))
    if norm < BRAIN_EPSILON:
        return list(v)
    max_norm = 0.999
    target_norm = min(math.tanh(norm / 2), max_norm)
    scale = target_norm / norm
    return [x * scale for x in v]


def _hyperbolic_dist_6d(u: List[float], v: List[float]) -> float:
    """Hyperbolic distance in 6D Poincare ball.

    d_H(u, v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    """
    diff_sq = sum((ui - (v[i] if i < len(v) else 0)) ** 2 for i, ui in enumerate(u))
    u_norm_sq = sum(x * x for x in u)
    v_norm_sq = sum(x * x for x in v)
    denom = (1 - u_norm_sq) * (1 - v_norm_sq)
    if denom <= 0:
        return float("inf")
    arg = 1 + (2 * diff_sq) / denom
    if arg < 1:
        return 0.0
    return math.acosh(arg)


# ═══════════════════════════════════════════════════════════════
# Cymatic Voxel Network
# ═══════════════════════════════════════════════════════════════


class CymaticVoxelNet:
    """Auto-propagational neural network on a 6D Chladni lattice.

    Usage:
        net = CymaticVoxelNet()
        voxel = net.probe([0.5, 0.3, -0.2, 0.1, 0.0, 0.4])
        print(voxel.zone)  # 'nodal' | 'negative_space' | 'implied_boundary'

        net.store(coords, payload)
        activations = net.propagate(start_coords, max_hops=5)
    """

    def __init__(
        self,
        initial_state: Optional[List[float]] = None,
        initial_position: Optional[List[float]] = None,
        *,
        nodal_threshold: float = NODAL_THRESHOLD,
        boundary_width: float = 0.05,
        harmonic_r: float = HARMONIC_R,
        coherence_decay: float = 0.85,
        max_hops: int = 10,
    ):
        self._state = list(initial_state) if initial_state else [1, 2, 3, 2, 1, 3]
        self._position = list(initial_position) if initial_position else [0, 0, 0, 0, 0, 0]
        self._nodal_threshold = nodal_threshold
        self._boundary_width = boundary_width
        self._harmonic_r = harmonic_r
        self._coherence_decay = coherence_decay
        self._max_hops = max_hops
        self._voxels: Dict[str, CymaticVoxel] = {}
        self._propagation_log: List[VoxelActivation] = []

    def probe(self, coords: List[float]) -> CymaticVoxel:
        """Probe a 6D coordinate: classify it and compute all metrics."""
        c6 = _pad6(coords)
        chladni_value = chladni_6d(c6, self._state)
        chladni_abs = abs(chladni_value)
        zone = classify_zone(chladni_value, self._nodal_threshold, self._boundary_width)
        tongue = dominant_tongue(c6)
        embedded = _poincare_embed_6d(c6)
        realm_center = REALM_CENTERS[tongue]
        realm_distance = _hyperbolic_dist_6d(embedded, realm_center)

        return CymaticVoxel(
            coords=c6,
            chladni_value=chladni_value,
            chladni_abs=chladni_abs,
            zone=zone,
            tongue=tongue,
            embedded=embedded,
            realm_distance=realm_distance,
        )

    def store(self, coords: List[float], payload: bytes) -> CymaticVoxel:
        """Store data at a 6D coordinate."""
        voxel = self.probe(coords)
        voxel.payload = payload
        self._voxels[_coord_key(voxel.coords)] = voxel
        return voxel

    def retrieve(
        self,
        coords: List[float],
        requester_position: List[float],
        max_distance: float = 2.0,
    ) -> Optional[CymaticVoxel]:
        """Retrieve data, gated by semantic coherence (hyperbolic distance)."""
        key = _coord_key(_pad6(coords))
        voxel = self._voxels.get(key)
        if voxel is None:
            return None

        req_embedded = _poincare_embed_6d(requester_position)
        dist = _hyperbolic_dist_6d(req_embedded, voxel.embedded)

        effective_max = max_distance * 0.5 if voxel.zone == "negative_space" else max_distance
        if dist > effective_max:
            return None
        return voxel

    def propagate(
        self,
        start_coords: List[float],
        max_hops: Optional[int] = None,
        step_size: float = 0.1,
    ) -> List[VoxelActivation]:
        """Auto-propagate activation from start along nodal contours."""
        hops = max_hops if max_hops is not None else self._max_hops
        activations: List[VoxelActivation] = []
        coords = _pad6(start_coords)
        strength = 1.0

        for gen in range(hops):
            if strength < BRAIN_EPSILON:
                break

            voxel = self.probe(coords)
            if voxel.zone == "negative_space" and gen > 0:
                break

            tongue = voxel.tongue
            h_cost = harmonic_scale(gen + 1, self._harmonic_r)

            activations.append(
                VoxelActivation(
                    voxel_index=gen,
                    strength=strength,
                    tongue=tongue,
                    generation=gen,
                    harmonic_cost=strength * h_cost,
                )
            )

            strength *= self._coherence_decay
            coords = self._step_toward_nodal(coords, step_size)

        self._propagation_log = activations
        return activations

    def _step_toward_nodal(self, coords: List[float], step_size: float) -> List[float]:
        """Gradient descent on |C(x, s)| to step toward nodal lines."""
        eps = 1e-6
        c_val = abs(chladni_6d(coords, self._state))
        gradient = [0.0] * 6

        for i in range(6):
            perturbed = list(coords)
            perturbed[i] += eps
            c_perturbed = abs(chladni_6d(perturbed, self._state))
            gradient[i] = (c_perturbed - c_val) / eps

        g_norm = math.sqrt(sum(g * g for g in gradient))
        if g_norm < BRAIN_EPSILON:
            return [c + math.sin((i + 1) * PHI) * step_size * 0.1 for i, c in enumerate(coords)]

        return [c - (gradient[i] / g_norm) * step_size for i, c in enumerate(coords)]

    # ═══════════════════════════════════════════════════════════
    # State Management
    # ═══════════════════════════════════════════════════════════

    def set_state(self, state: List[float]) -> None:
        self._state = list(state[:6])

    def set_position(self, position: List[float]) -> None:
        self._position = list(position[:6])

    def get_state(self) -> List[float]:
        return list(self._state)

    def get_position(self) -> List[float]:
        return list(self._position)

    def stored_count(self) -> int:
        return len(self._voxels)

    def last_propagation(self) -> List[VoxelActivation]:
        return list(self._propagation_log)

    def snapshot(self) -> NetSnapshot:
        """Network statistics snapshot."""
        nodal = neg = boundary = 0
        chladni_sum = 0.0

        for voxel in self._voxels.values():
            chladni_sum += voxel.chladni_abs
            if voxel.zone == "nodal":
                nodal += 1
            elif voxel.zone == "negative_space":
                neg += 1
            else:
                boundary += 1

        total = len(self._voxels) or 1
        return NetSnapshot(
            total_voxels=len(self._voxels),
            nodal_count=nodal,
            negative_space_count=neg,
            boundary_count=boundary,
            nodal_fraction=nodal / total,
            negative_space_fraction=neg / total,
            mean_chladni_abs=chladni_sum / total,
            storage_capacity={"nodal": nodal, "negative_space": neg, "total": len(self._voxels)},
        )

    def clear(self) -> None:
        self._voxels.clear()
        self._propagation_log = []


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _pad6(coords: List[float]) -> List[float]:
    """Ensure 6D coordinate."""
    if len(coords) >= 6:
        return list(coords[:6])
    return list(coords) + [0.0] * (6 - len(coords))


def _coord_key(coords: List[float]) -> str:
    """Coordinate key for the voxel map."""
    return ",".join(f"{c:.6f}" for c in coords)
