"""
Locality Axiom Module - Spatially-Bounded Operations

This module groups layers that satisfy the locality axiom from quantum field theory:
operations that act on bounded spatial regions with finite propagation speed.

Assigned Layers:
- Layer 3: Weighted Transform (Langues Metric) - Local metric weighting
- Layer 8: Multi-Well Realms - Local potential wells / governance regions

Mathematical Foundation:
A transform T satisfies locality iff:
    supp(T(f)) ⊆ neighborhood(supp(f))

Meaning the output only depends on a bounded neighborhood of the input.
In discrete settings, this corresponds to sparse/banded operations.
"""

from __future__ import annotations

import functools
import numpy as np
from typing import Callable, TypeVar, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

# Type variables for generic decorators
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Constants
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618
EPS = 1e-10
N_REALMS = 5


class LocalityViolation(Exception):
    """Raised when an operation violates the locality axiom."""
    pass


@dataclass
class LocalityCheckResult:
    """Result of a locality axiom check."""
    passed: bool
    effective_radius: float  # How far the operation spreads
    sparsity: float  # Fraction of zero entries in operator matrix
    bandwidth: Optional[int]  # For banded matrices
    layer_name: str
    max_radius: float  # Maximum allowed locality radius

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"LocalityCheck[{self.layer_name}]: {status}\n"
            f"  Effective radius: {self.effective_radius:.4f} (max: {self.max_radius:.4f})\n"
            f"  Sparsity: {self.sparsity:.2%}\n"
            f"  Bandwidth: {self.bandwidth}"
        )


def locality_check(
    max_radius: float = 1.0,
    require_sparse: bool = False,
    max_bandwidth: Optional[int] = None
) -> Callable[[F], F]:
    """
    Decorator that verifies an operation satisfies locality constraints.

    For transformations represented by matrices, locality means:
    1. The matrix is sparse or banded (limited interaction range)
    2. Output components only depend on nearby input components

    Args:
        max_radius: Maximum allowed interaction radius
        require_sparse: If True, require sparse representation
        max_bandwidth: Maximum allowed matrix bandwidth (None = no limit)

    Returns:
        Decorated function with locality verification
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Compute locality metrics if the function has an associated matrix
            if hasattr(wrapper, '_operator_matrix'):
                matrix = wrapper._operator_matrix
                radius, sparsity, bandwidth = _analyze_locality(matrix)
            else:
                # For general functions, use output bounds as proxy
                output = result[0] if isinstance(result, tuple) else result
                radius = float(np.max(np.abs(output))) if isinstance(output, np.ndarray) else 0
                sparsity = 0.0
                bandwidth = None

            passed = radius <= max_radius
            if max_bandwidth is not None and bandwidth is not None:
                passed = passed and bandwidth <= max_bandwidth

            check_result = LocalityCheckResult(
                passed=passed,
                effective_radius=radius,
                sparsity=sparsity,
                bandwidth=bandwidth,
                layer_name=func.__name__,
                max_radius=max_radius
            )

            wrapper.last_check = check_result
            return result

        wrapper.last_check = None
        wrapper.axiom = "locality"
        wrapper._operator_matrix = None
        return wrapper
    return decorator


def _analyze_locality(matrix: np.ndarray) -> Tuple[float, float, Optional[int]]:
    """
    Analyze locality properties of an operator matrix.

    Args:
        matrix: Operator matrix to analyze

    Returns:
        Tuple of (effective_radius, sparsity, bandwidth)
    """
    n = matrix.shape[0]

    # Sparsity: fraction of near-zero entries
    sparsity = np.mean(np.abs(matrix) < EPS)

    # Bandwidth: distance from diagonal to furthest non-zero
    bandwidth = 0
    for i in range(n):
        for j in range(n):
            if abs(matrix[i, j]) > EPS:
                bandwidth = max(bandwidth, abs(i - j))

    # Effective radius: based on off-diagonal decay
    if n > 1:
        off_diag_weight = 0.0
        total_weight = np.sum(np.abs(matrix))
        for i in range(n):
            for j in range(n):
                if i != j:
                    off_diag_weight += abs(i - j) * abs(matrix[i, j])
        effective_radius = off_diag_weight / (total_weight + EPS)
    else:
        effective_radius = 0.0

    return effective_radius, sparsity, bandwidth


# ============================================================================
# Layer 3: Weighted Transform (Langues Metric Tensor)
# ============================================================================

def build_langues_metric(dim: int, phi_decay: float = PHI) -> np.ndarray:
    """
    Build the Langues Metric Tensor G.

    The metric encodes the "sacred tongues" weighting where each dimension
    has different geometric significance based on golden ratio decay.

    G_ij = δ_ij · φ^(-|i-j|/2)

    Properties:
        - Diagonal (local - each dimension weighted independently)
        - Positive definite
        - Decay controlled by golden ratio

    Args:
        dim: Dimension of the metric tensor
        phi_decay: Base of exponential decay (default: φ)

    Returns:
        Diagonal metric tensor G
    """
    # Compute diagonal weights with phi-based decay from center
    center = dim / 2
    weights = np.array([
        phi_decay ** (-abs(i - center) / 2)
        for i in range(dim)
    ])

    return np.diag(weights)


def langues_metric_sqrt(G: np.ndarray) -> np.ndarray:
    """
    Compute G^(1/2) for the weighted transform.

    Since G is diagonal with positive entries, G^(1/2) is just sqrt of diagonal.
    """
    return np.diag(np.sqrt(np.diag(G)))


@locality_check(max_radius=1.0)
def layer_3_weighted(x: np.ndarray, G: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Layer 3: Weighted Transform

    x' = G^(1/2) x

    Applies the Langues Metric Tensor to weight dimensions according
    to their geometric significance.

    Locality Property:
        G is diagonal, so each output component depends only on the
        corresponding input component (perfect locality).

    Args:
        x: Input vector in ℝ²ᴰ
        G: Metric tensor (computed if not provided)

    Returns:
        Weighted vector in Langues metric space
    """
    dim = len(x)

    if G is None:
        G = build_langues_metric(dim)

    G_sqrt = langues_metric_sqrt(G)

    # Store operator matrix for locality analysis
    layer_3_weighted._operator_matrix = G_sqrt

    return G_sqrt @ x


def layer_3_inverse(x_weighted: np.ndarray, G: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Inverse of Layer 3: Remove weighting.

    x = G^(-1/2) x'
    """
    dim = len(x_weighted)

    if G is None:
        G = build_langues_metric(dim)

    G_sqrt_inv = np.diag(1.0 / np.sqrt(np.diag(G)))

    return G_sqrt_inv @ x_weighted


# ============================================================================
# Layer 8: Multi-Well Realms
# ============================================================================

@dataclass
class RealmInfo:
    """Information about a governance realm."""
    index: int
    center: np.ndarray
    radius: float
    weight: float  # Governance sensitivity multiplier
    name: str


def generate_realm_centers(dim: int, n_realms: int = N_REALMS) -> List[RealmInfo]:
    """
    Generate realm centers distributed in the Poincaré ball.

    Realms represent distinct governance regions with different
    sensitivity weights and properties.

    Args:
        dim: Dimension of the space
        n_realms: Number of realms to generate

    Returns:
        List of RealmInfo objects
    """
    realms = []
    realm_names = ["CORE", "TRUST", "CAUTION", "BOUNDARY", "EDGE"]

    for k in range(n_realms):
        # Radius from center (0.3 to 0.7)
        r = 0.3 + 0.4 * k / (n_realms - 1) if n_realms > 1 else 0.5

        # Angle for positioning (spread around circle)
        theta = 2 * np.pi * k / n_realms

        # Create center point (first two dimensions determine position)
        center = np.zeros(dim)
        if dim >= 2:
            center[0] = r * np.cos(theta)
            center[1] = r * np.sin(theta)
        else:
            center[0] = r * (1 if k % 2 == 0 else -1)

        # Realm weight (sensitivity multiplier)
        weights = [0.8, 1.0, 1.2, 1.4, 1.5]
        weight = weights[k] if k < len(weights) else 1.0

        realms.append(RealmInfo(
            index=k,
            center=center,
            radius=0.2,  # Realm influence radius
            weight=weight,
            name=realm_names[k] if k < len(realm_names) else f"REALM_{k}"
        ))

    return realms


def hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    """
    Compute hyperbolic distance in the Poincaré ball.

    d_H(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
    """
    diff = u - v
    diff_sq = np.dot(diff, diff)
    u_sq = np.dot(u, u)
    v_sq = np.dot(v, v)

    # Clamp to avoid numerical issues
    u_sq = min(u_sq, 1.0 - EPS)
    v_sq = min(v_sq, 1.0 - EPS)

    denominator = (1 - u_sq) * (1 - v_sq)
    if denominator < EPS:
        return float('inf')

    arg = 1 + 2 * diff_sq / denominator
    arg = max(arg, 1.0)  # arcosh domain: [1, ∞)

    return float(np.arccosh(arg))


@locality_check(max_radius=5.0)
def layer_8_multi_well(
    u: np.ndarray,
    realms: Optional[List[RealmInfo]] = None
) -> Tuple[float, int, RealmInfo]:
    """
    Layer 8: Multi-Well Realm Detection

    d* = min_k d_H(u, μ_k)

    Determines which governance realm the state belongs to by finding
    the nearest realm center in hyperbolic distance.

    Locality Property:
        The realm assignment depends only on the local position in
        hyperbolic space. Each realm has a bounded region of influence.

    Args:
        u: Point in Poincaré ball
        realms: List of realm definitions (generated if not provided)

    Returns:
        Tuple of (minimum_distance, realm_index, realm_info)
    """
    dim = len(u)

    if realms is None:
        realms = generate_realm_centers(dim)

    min_distance = float('inf')
    nearest_realm_idx = 0
    nearest_realm = realms[0]

    for realm in realms:
        # Ensure realm center has correct dimension
        center = realm.center
        if len(center) != dim:
            center = np.zeros(dim)
            center[:min(len(realm.center), dim)] = realm.center[:min(len(realm.center), dim)]

        distance = hyperbolic_distance(u, center)

        if distance < min_distance:
            min_distance = distance
            nearest_realm_idx = realm.index
            nearest_realm = realm

    return min_distance, nearest_realm_idx, nearest_realm


def layer_8_potential(
    u: np.ndarray,
    realms: Optional[List[RealmInfo]] = None,
    well_depth: float = 1.0
) -> float:
    """
    Compute the multi-well potential at a point.

    V(u) = -Σ_k w_k · exp(-d_H(u, μ_k)² / (2σ²))

    Each realm creates a Gaussian potential well centered at μ_k.

    Args:
        u: Point in Poincaré ball
        realms: List of realm definitions
        well_depth: Depth scaling factor

    Returns:
        Potential energy at the point
    """
    dim = len(u)

    if realms is None:
        realms = generate_realm_centers(dim)

    sigma_sq = 0.5  # Well width parameter
    potential = 0.0

    for realm in realms:
        center = realm.center
        if len(center) != dim:
            center = np.zeros(dim)
            center[:min(len(realm.center), dim)] = realm.center[:min(len(realm.center), dim)]

        d = hyperbolic_distance(u, center)
        potential -= well_depth * realm.weight * np.exp(-d**2 / (2 * sigma_sq))

    return potential


# ============================================================================
# Lattice Embedding for Locality
# ============================================================================

@dataclass
class LatticePoint:
    """A point on the spatial lattice."""
    coords: Tuple[int, ...]
    value: complex
    neighbors: List[Tuple[int, ...]]


def create_lattice(shape: Tuple[int, ...]) -> dict:
    """
    Create a lattice structure for spatial embedding.

    The lattice enforces locality by explicitly defining
    neighbor relationships.

    Args:
        shape: Shape of the lattice (e.g., (8, 8) for 2D)

    Returns:
        Dictionary mapping coordinates to LatticePoint objects
    """
    from itertools import product

    lattice = {}
    dims = len(shape)

    for coords in product(*[range(s) for s in shape]):
        # Find neighbors (Manhattan distance 1)
        neighbors = []
        for d in range(dims):
            for delta in [-1, 1]:
                neighbor = list(coords)
                neighbor[d] += delta
                if 0 <= neighbor[d] < shape[d]:
                    neighbors.append(tuple(neighbor))

        lattice[coords] = LatticePoint(
            coords=coords,
            value=0j,
            neighbors=neighbors
        )

    return lattice


def lattice_embed(
    x: np.ndarray,
    lattice_shape: Tuple[int, ...] = (4, 3)
) -> dict:
    """
    Embed a vector onto a spatial lattice.

    This enforces locality by distributing vector components
    across lattice sites with explicit neighbor structure.

    Args:
        x: Input vector
        lattice_shape: Shape of the target lattice

    Returns:
        Lattice with embedded values
    """
    lattice = create_lattice(lattice_shape)
    total_sites = np.prod(lattice_shape)

    # Pad or truncate x to match lattice size
    if len(x) < total_sites:
        x_padded = np.zeros(total_sites, dtype=complex)
        x_padded[:len(x)] = x
    else:
        x_padded = x[:total_sites]

    # Embed values onto lattice
    from itertools import product
    for i, coords in enumerate(product(*[range(s) for s in lattice_shape])):
        if i < len(x_padded):
            lattice[coords].value = x_padded[i]

    return lattice


# ============================================================================
# Locality Verification Utilities
# ============================================================================

def verify_layer_locality(
    layer_func: Callable,
    n_tests: int = 100,
    dim: int = 12,
    verbose: bool = False
) -> Tuple[bool, dict]:
    """
    Statistically verify that a layer satisfies locality.

    Args:
        layer_func: Layer function to test
        n_tests: Number of random tests
        dim: Dimension of test vectors
        verbose: Print detailed results

    Returns:
        Tuple of (all_passed, statistics)
    """
    all_passed = True
    max_radius = 0.0
    avg_sparsity = 0.0

    for i in range(n_tests):
        # Generate random point in Poincaré ball
        x = np.random.randn(dim)
        x = 0.5 * x / (np.linalg.norm(x) + EPS)

        # Apply layer
        if layer_func.__name__ == "layer_3_weighted":
            _ = layer_func(x)
        else:
            _ = layer_func(x)

        # Check result
        check = getattr(layer_func, 'last_check', None)
        if check:
            max_radius = max(max_radius, check.effective_radius)
            avg_sparsity += check.sparsity
            if not check.passed:
                all_passed = False
                if verbose:
                    print(f"Test {i}: {check}")

    avg_sparsity /= n_tests

    return all_passed, {
        "max_radius": max_radius,
        "avg_sparsity": avg_sparsity
    }


# ============================================================================
# Axiom Layer Registry
# ============================================================================

LOCALITY_LAYERS = {
    3: {
        "name": "Weighted Transform",
        "function": layer_3_weighted,
        "inverse": layer_3_inverse,
        "description": "Langues Metric: G^(1/2)x - diagonal (perfectly local)",
        "is_diagonal": True,
    },
    8: {
        "name": "Multi-Well Realms",
        "function": layer_8_multi_well,
        "inverse": None,  # Detection is not invertible
        "description": "Realm detection: min_k d_H(u, μ_k) - bounded interaction",
        "is_diagonal": False,
    },
}


def get_locality_layer(layer_num: int) -> dict:
    """Get layer info by number."""
    if layer_num not in LOCALITY_LAYERS:
        raise ValueError(f"Layer {layer_num} is not a locality layer")
    return LOCALITY_LAYERS[layer_num]


def list_locality_layers() -> list:
    """List all layers satisfying the locality axiom."""
    return list(LOCALITY_LAYERS.keys())
