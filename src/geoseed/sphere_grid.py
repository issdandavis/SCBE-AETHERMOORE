"""
Cl(6,0) Icosahedral Sphere Grid — Sacred Tongue Origin Nodes
=============================================================

Each Sacred Tongue maps to a basis vector in Cl(6,0) Clifford algebra:
    KO → e1    AV → e2    RU → e3    CA → e4    UM → e5    DR → e6

The algebra has 2^6 = 64 components:
    1 scalar, 6 vectors, 15 bivectors, 20 trivectors,
    15 quadvectors, 6 pentavectors, 1 pseudoscalar

Each tongue gets an icosahedral sphere grid (resolution 3 = 642 vertices).
Intra-sphere: graph convolution along icosahedral edges.
Cross-sphere: Möbius addition weighted by bivector interaction strength.

@layer L5, L6, L9
@component GeoSeed.SphereGrid
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio


# ---------------------------------------------------------------------------
# Cl(6,0) Clifford Algebra
# ---------------------------------------------------------------------------

# Grade dimensions for Cl(6,0): C(6,k) for k=0..6
GRADE_DIMS = [1, 6, 15, 20, 15, 6, 1]  # Total = 64

# Sacred Tongue → basis vector index (e1..e6)
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Tongue phase offsets (radians) — canonical from geoseal.py
TONGUE_PHASES = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

# LWS weights (metric cost scale)
LWS_WEIGHTS = {"KO": 1.000, "AV": 1.125, "RU": 1.250, "CA": 1.375, "UM": 1.500, "DR": 1.667}

# Phi weights (Sacred Eggs genesis scale)
PHI_WEIGHTS = {"KO": 1.000, "AV": PHI, "RU": PHI**2, "CA": PHI**3, "UM": PHI**4, "DR": PHI**5}


class CliffordAlgebra:
    """Cl(6,0) Clifford algebra with 64-dimensional multivector space.

    Basis vectors e1..e6 satisfy e_i * e_j + e_j * e_i = 2 * delta_{ij}.
    Bivectors e_ij = e_i ^ e_j encode pairwise tongue interactions.
    """

    def __init__(self):
        self.dim = 6
        self.total_components = 64
        self.grade_dims = GRADE_DIMS

        # Build basis vector indices within the 64-component multivector
        # Grade 0 (scalar): index 0
        # Grade 1 (vectors): indices 1-6
        # Grade 2 (bivectors): indices 7-21
        # Grade 3 (trivectors): indices 22-41
        # Grade 4 (quadvectors): indices 42-56
        # Grade 5 (pentavectors): indices 57-62
        # Grade 6 (pseudoscalar): index 63
        self._grade_offsets = []
        offset = 0
        for g in GRADE_DIMS:
            self._grade_offsets.append(offset)
            offset += g

        # Precompute bivector index map: (i,j) → flat index in multivector
        self._bivector_map: Dict[Tuple[int, int], int] = {}
        bv_idx = self._grade_offsets[2]
        for i in range(6):
            for j in range(i + 1, 6):
                self._bivector_map[(i, j)] = bv_idx
                bv_idx += 1

    def basis_vector(self, index: int) -> np.ndarray:
        """Return the e_i basis vector as a 64-component multivector."""
        mv = np.zeros(self.total_components)
        mv[self._grade_offsets[1] + index] = 1.0
        return mv

    def bivector(self, i: int, j: int) -> np.ndarray:
        """Return e_i ^ e_j as a 64-component multivector."""
        if i > j:
            return -self.bivector(j, i)
        mv = np.zeros(self.total_components)
        mv[self._bivector_map[(i, j)]] = 1.0
        return mv

    def geometric_product(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Simplified geometric product for grade-1 vectors.

        For two grade-1 vectors: a * b = a . b + a ^ b
        where a . b is scalar (inner) and a ^ b is bivector (outer).
        """
        # Extract grade-1 components
        a_vec = a[self._grade_offsets[1] : self._grade_offsets[1] + 6]
        b_vec = b[self._grade_offsets[1] : self._grade_offsets[1] + 6]

        result = np.zeros(self.total_components)

        # Scalar part (inner product): sum(a_i * b_i)
        result[0] = np.dot(a_vec, b_vec)

        # Bivector part (outer product): a_i * b_j - a_j * b_i
        for i in range(6):
            for j in range(i + 1, 6):
                result[self._bivector_map[(i, j)]] = a_vec[i] * b_vec[j] - a_vec[j] * b_vec[i]

        return result

    def bivector_strength(self, tongue_a: str, tongue_b: str) -> float:
        """Interaction strength between two tongues via their bivector.

        Strength = phi_weight_a * phi_weight_b * cos(phase_a - phase_b).
        """
        phase_diff = TONGUE_PHASES[tongue_a] - TONGUE_PHASES[tongue_b]
        return PHI_WEIGHTS[tongue_a] * PHI_WEIGHTS[tongue_b] * math.cos(phase_diff)

    def tongue_bivector_index(self, tongue_a: str, tongue_b: str) -> int:
        """Get the flat multivector index for the bivector of two tongues."""
        i = TONGUE_NAMES.index(tongue_a)
        j = TONGUE_NAMES.index(tongue_b)
        if i > j:
            i, j = j, i
        return self._bivector_map[(i, j)]


# Singleton
CL6 = CliffordAlgebra()

# Tongue → basis multivector mapping
TONGUE_BASIS: Dict[str, np.ndarray] = {
    name: CL6.basis_vector(i) for i, name in enumerate(TONGUE_NAMES)
}


# ---------------------------------------------------------------------------
# Icosahedral Sphere Grid
# ---------------------------------------------------------------------------


def _icosahedron_base_vertices() -> np.ndarray:
    """12 vertices of a regular icosahedron on the unit sphere."""
    verts = []
    # North pole
    verts.append([0, 0, 1.0])
    # Upper ring (5 vertices at latitude arctan(0.5))
    lat_upper = math.atan(0.5)
    for k in range(5):
        lon = 2 * math.pi * k / 5
        verts.append([
            math.cos(lat_upper) * math.cos(lon),
            math.cos(lat_upper) * math.sin(lon),
            math.sin(lat_upper),
        ])
    # Lower ring (5 vertices, offset by pi/5)
    lat_lower = -math.atan(0.5)
    for k in range(5):
        lon = 2 * math.pi * k / 5 + math.pi / 5
        verts.append([
            math.cos(lat_lower) * math.cos(lon),
            math.cos(lat_lower) * math.sin(lon),
            math.sin(lat_lower),
        ])
    # South pole
    verts.append([0, 0, -1.0])
    arr = np.array(verts)
    # Normalize to unit sphere
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / norms


def _icosahedron_base_faces() -> List[Tuple[int, int, int]]:
    """20 triangular faces of the icosahedron."""
    return [
        # Top cap
        (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 1),
        # Upper middle band
        (1, 6, 2), (2, 7, 3), (3, 8, 4), (4, 9, 5), (5, 10, 1),
        # Lower middle band
        (6, 7, 2), (7, 8, 3), (8, 9, 4), (9, 10, 5), (10, 6, 1),
        # Bottom cap
        (11, 7, 6), (11, 8, 7), (11, 9, 8), (11, 10, 9), (11, 6, 10),
    ]


def icosahedral_subdivide(resolution: int = 3) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
    """Subdivide icosahedron to given resolution, project to unit sphere.

    Resolution 0: 12 vertices, 30 edges
    Resolution 1: 42 vertices, 120 edges
    Resolution 2: 162 vertices, 480 edges
    Resolution 3: 642 vertices, 1920 edges

    Returns:
        vertices: (N, 3) array of unit-sphere positions
        edges: list of (i, j) index pairs for adjacency
    """
    base_verts = _icosahedron_base_vertices()
    base_faces = _icosahedron_base_faces()

    # Use dict to deduplicate midpoints
    vertex_list = list(base_verts)
    vertex_key_to_idx: Dict[Tuple[float, ...], int] = {}
    for i, v in enumerate(vertex_list):
        vertex_key_to_idx[tuple(np.round(v, 8))] = i

    faces = list(base_faces)

    def midpoint_index(i: int, j: int) -> int:
        mid = (vertex_list[i] + vertex_list[j]) / 2.0
        mid = mid / np.linalg.norm(mid)  # Project to sphere
        key = tuple(np.round(mid, 8))
        if key not in vertex_key_to_idx:
            vertex_key_to_idx[key] = len(vertex_list)
            vertex_list.append(mid)
        return vertex_key_to_idx[key]

    for _level in range(resolution):
        new_faces = []
        for a, b, c in faces:
            ab = midpoint_index(a, b)
            bc = midpoint_index(b, c)
            ca = midpoint_index(c, a)
            new_faces.extend([
                (a, ab, ca),
                (ab, b, bc),
                (ca, bc, c),
                (ab, bc, ca),
            ])
        faces = new_faces

    vertices = np.array(vertex_list)

    # Extract unique edges from faces
    edge_set: set = set()
    for a, b, c in faces:
        for u, v in [(a, b), (b, c), (c, a)]:
            edge_set.add((min(u, v), max(u, v)))
    edges = sorted(edge_set)

    return vertices, edges


# ---------------------------------------------------------------------------
# Poincaré Ball Utilities
# ---------------------------------------------------------------------------


def poincare_project(euclidean: np.ndarray, curvature: float = 1.0) -> np.ndarray:
    """Project Euclidean point into the Poincaré ball via exponential map at origin."""
    norm = np.linalg.norm(euclidean)
    if norm < 1e-12:
        return euclidean.copy()
    c = abs(curvature)
    t = np.tanh(math.sqrt(c) * norm / 2)
    # Clamp strictly inside ball  # A4: Clamping
    t = min(t, 1.0 - 1e-7)
    return t * euclidean / (math.sqrt(c) * norm)


def mobius_add(x: np.ndarray, y: np.ndarray, c: float = 1.0) -> np.ndarray:
    """Möbius addition in the Poincaré ball model.

    x ⊕_c y = ((1 + 2c<x,y> + c||y||²)x + (1 - c||x||²)y) /
               (1 + 2c<x,y> + c²||x||²||y||²)
    """
    x_sq = float(np.dot(x, x))
    y_sq = float(np.dot(y, y))
    xy = float(np.dot(x, y))

    num = (1 + 2 * c * xy + c * y_sq) * x + (1 - c * x_sq) * y
    den = 1 + 2 * c * xy + c * c * x_sq * y_sq

    result = num / max(den, 1e-12)

    # Clamp to ball boundary  # A4: Clamping
    norm = np.linalg.norm(result)
    max_norm = (1.0 / math.sqrt(c)) - 1e-5
    if norm > max_norm:
        result = result * (max_norm / norm)

    return result


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, c: float = 1.0) -> float:
    """Hyperbolic distance in Poincaré ball.  # L5 invariant

    d_H(u,v) = (2/sqrt(c)) * arctanh(sqrt(c) * ||(-u) ⊕_c v||)
    """
    neg_u = -u
    diff = mobius_add(neg_u, v, c)
    diff_norm = float(np.linalg.norm(diff))
    sqrt_c = math.sqrt(c)
    return (2.0 / sqrt_c) * math.atanh(min(sqrt_c * diff_norm, 1 - 1e-7))


# ---------------------------------------------------------------------------
# Sphere Grid
# ---------------------------------------------------------------------------


@dataclass
class SphereGrid:
    """Icosahedral sphere grid for a single Sacred Tongue.

    Each grid lives on S² with 642 vertices (resolution 3).
    Associated with a Cl(6,0) basis vector.

    Attributes:
        tongue: Sacred Tongue name (KO/AV/RU/CA/UM/DR)
        resolution: Icosahedral subdivision level (3 → 642 vertices)
        vertices: (N, 3) unit-sphere positions
        edges: adjacency list as (i, j) pairs
        basis_index: index 0-5 for e1..e6 in Cl(6,0)
        signals: (N, signal_dim) per-vertex signal (initialized zero)
    """

    tongue: str
    resolution: int = 3
    signal_dim: int = 64  # Match Cl(6,0) multivector dimension
    vertices: np.ndarray = field(default_factory=lambda: np.empty(0))
    edges: List[Tuple[int, int]] = field(default_factory=list)
    basis_index: int = 0
    signals: np.ndarray = field(default_factory=lambda: np.empty(0))
    _adjacency: Optional[Dict[int, List[int]]] = field(default=None, repr=False)

    def __post_init__(self):
        if self.vertices.size == 0:
            self.vertices, self.edges = icosahedral_subdivide(self.resolution)
        self.basis_index = TONGUE_NAMES.index(self.tongue)
        n_verts = len(self.vertices)
        if self.signals.size == 0:
            self.signals = np.zeros((n_verts, self.signal_dim))
        self._adjacency = None

    @property
    def n_vertices(self) -> int:
        return len(self.vertices)

    @property
    def adjacency(self) -> Dict[int, List[int]]:
        """Lazy-built adjacency dict from edge list."""
        if self._adjacency is None:
            adj: Dict[int, List[int]] = {i: [] for i in range(self.n_vertices)}
            for u, v in self.edges:
                adj[u].append(v)
                adj[v].append(u)
            self._adjacency = adj
        return self._adjacency

    @property
    def basis_vector(self) -> np.ndarray:
        """Cl(6,0) basis vector for this tongue."""
        return TONGUE_BASIS[self.tongue]

    @property
    def phase(self) -> float:
        return TONGUE_PHASES[self.tongue]

    def geodesic_weight(self, i: int, j: int) -> float:
        """Geodesic distance weight between two vertices on S²."""
        dot = float(np.clip(np.dot(self.vertices[i], self.vertices[j]), -1.0, 1.0))
        angle = math.acos(dot)
        # Exponential decay with distance — nearby vertices interact more
        return math.exp(-angle)

    def intra_convolve(self, signal: Optional[np.ndarray] = None) -> np.ndarray:
        """Graph convolution along icosahedral edges within this sphere.

        For each vertex v, aggregates neighbor signals weighted by geodesic distance:
            h_v = sigma(sum_{u in N(v)} w(v,u) * W * h_u + b)

        Uses stored signals if none provided.

        Returns:
            Updated (N, signal_dim) signal array.
        """
        if signal is not None:
            self.signals = signal

        n = self.n_vertices
        d = self.signal_dim
        output = np.zeros((n, d))

        for v in range(n):
            neighbors = self.adjacency[v]
            if not neighbors:
                output[v] = self.signals[v]
                continue

            weighted_sum = np.zeros(d)
            total_weight = 0.0
            for u in neighbors:
                w = self.geodesic_weight(v, u)
                weighted_sum += w * self.signals[u]
                total_weight += w

            if total_weight > 0:
                # Normalized aggregation + self-loop
                output[v] = 0.5 * self.signals[v] + 0.5 * weighted_sum / total_weight
            else:
                output[v] = self.signals[v]

        # ReLU activation
        output = np.maximum(output, 0)
        self.signals = output
        return output

    def deposit_signal(self, position_3d: np.ndarray, signal: np.ndarray):
        """Deposit a signal at the nearest vertex to a 3D unit-sphere position.

        Used by the dressing pipeline to place dressed bits on the grid.
        """
        # Normalize to unit sphere
        pos = position_3d / max(np.linalg.norm(position_3d), 1e-12)
        # Find nearest vertex
        dots = self.vertices @ pos
        nearest = int(np.argmax(dots))
        # Accumulate signal
        self.signals[nearest] += signal

    def read_signal(self, position_3d: np.ndarray) -> np.ndarray:
        """Read interpolated signal from the sphere at a 3D position."""
        pos = position_3d / max(np.linalg.norm(position_3d), 1e-12)
        dots = self.vertices @ pos
        # Top-3 nearest vertices for interpolation
        top3 = np.argsort(dots)[-3:]
        weights = np.array([max(dots[i], 0) for i in top3])
        w_sum = weights.sum()
        if w_sum < 1e-12:
            return np.zeros(self.signal_dim)
        weights /= w_sum
        return sum(weights[k] * self.signals[top3[k]] for k in range(3))

    def clear(self):
        """Reset all signals to zero."""
        self.signals = np.zeros((self.n_vertices, self.signal_dim))


def cross_tongue_convolve(
    grid_a: SphereGrid,
    grid_b: SphereGrid,
    algebra: CliffordAlgebra = CL6,
) -> Tuple[np.ndarray, np.ndarray]:
    """Cross-tongue interaction via bivector-weighted Möbius addition.

    The bivector e_a ^ e_b encodes the interaction channel between
    tongue_a and tongue_b. Signals propagate across tongues through
    this channel, weighted by bivector strength.

    Returns:
        Updated signals for (grid_a, grid_b).
    """
    strength = algebra.bivector_strength(grid_a.tongue, grid_b.tongue)

    # Global mean signals as cross-tongue message
    mean_a = grid_a.signals.mean(axis=0)
    mean_b = grid_b.signals.mean(axis=0)

    # Poincaré-project the mean signals, then Möbius-add the cross-tongue message
    proj_a = poincare_project(mean_a)
    proj_b = poincare_project(mean_b)

    # Cross-tongue message: Möbius addition weighted by bivector strength
    msg_to_a = strength * proj_b
    msg_to_b = strength * proj_a

    # Clamp messages to ball
    for msg in [msg_to_a, msg_to_b]:
        norm = np.linalg.norm(msg)
        if norm > 0.95:
            msg *= 0.95 / norm

    # Update each vertex with the cross-tongue message (broadcast)
    grid_a.signals += msg_to_a[np.newaxis, :]
    grid_b.signals += msg_to_b[np.newaxis, :]

    return grid_a.signals, grid_b.signals


# ---------------------------------------------------------------------------
# Multi-Grid Network (6 interconnected spheres)
# ---------------------------------------------------------------------------


class SphereGridNetwork:
    """6 interconnected icosahedral sphere grids — one per Sacred Tongue.

    The network forms a (S² x Cl(6,0))^6 product manifold where:
    - Intra-sphere: graph convolution along icosahedral edges
    - Cross-sphere: bivector-weighted Möbius addition (15 channels for C(6,2) pairs)

    Total nodes: 6 x 642 = 3,852
    Total bivector channels: 15
    """

    def __init__(self, resolution: int = 3, signal_dim: int = 64):
        self.resolution = resolution
        self.signal_dim = signal_dim
        self.algebra = CL6

        # Initialize 6 sphere grids
        self.grids: Dict[str, SphereGrid] = {}
        for tongue in TONGUE_NAMES:
            self.grids[tongue] = SphereGrid(
                tongue=tongue,
                resolution=resolution,
                signal_dim=signal_dim,
            )

        # Precompute all 15 bivector pairs
        self.tongue_pairs: List[Tuple[str, str]] = []
        for i, t1 in enumerate(TONGUE_NAMES):
            for t2 in TONGUE_NAMES[i + 1 :]:
                self.tongue_pairs.append((t1, t2))

    @property
    def total_nodes(self) -> int:
        return sum(g.n_vertices for g in self.grids.values())

    def forward(self, n_steps: int = 1) -> Dict[str, np.ndarray]:
        """Run n_steps of propagation across the network.

        Each step:
        1. Intra-sphere convolution (all 6 grids)
        2. Cross-sphere interaction (all 15 bivector channels)

        Returns:
            Dict mapping tongue name to final signal array.
        """
        for _step in range(n_steps):
            # Phase 1: Intra-sphere convolution
            for tongue, grid in self.grids.items():
                grid.intra_convolve()

            # Phase 2: Cross-sphere bivector interactions
            for t1, t2 in self.tongue_pairs:
                cross_tongue_convolve(self.grids[t1], self.grids[t2], self.algebra)

        return {t: g.signals.copy() for t, g in self.grids.items()}

    def deposit(self, tongue: str, position: np.ndarray, signal: np.ndarray):
        """Deposit a signal on a specific tongue's sphere grid."""
        self.grids[tongue].deposit_signal(position, signal)

    def read_global_state(self) -> np.ndarray:
        """Read the global state as concatenation of all grid mean signals.

        Returns (6 * signal_dim,) vector — the network's summary embedding.
        """
        means = [self.grids[t].signals.mean(axis=0) for t in TONGUE_NAMES]
        return np.concatenate(means)

    def clear_all(self):
        """Reset all grids."""
        for grid in self.grids.values():
            grid.clear()
