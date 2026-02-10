"""
GeoSeal - Context Vectors + Hyperbolic Geometry Core
====================================================

Provisions 2 & 3:
- Context vectors freely use negative floats
- Operates in hyperbolic space (negative curvature)
- Hyperbolic distance is always non-negative (failable by design if negative)

Integration with Dual Lattice:
- Context vectors map to the 10D lattice space
- Hyperbolic distance feeds into trust score calculation
- Negative curvature amplifies adversarial drift cost
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SecurityPosture(str, Enum):
    """Security postures based on flux state (from ADVANCED_CONCEPTS.md)."""
    DEMI = "demi"        # Containment: 0 < v < 0.5, minimal trust
    QUASI = "quasi"      # Adaptive: 0.5 <= v < 0.9, conditional trust
    POLLY = "polly"      # Permissive: v >= 0.9, high trust
    COLLAPSED = "collapsed"  # Dormant: v ~ 0, no activity


@dataclass
class ContextVector:
    """
    6+ dimensional agent state vector.
    Components can be negative (position, velocity, priority, security level).
    Example from docs: supports values like -9.9, -2.0

    Dimensions (default interpretation):
    - [0]: Position X (can be negative for left/opposing)
    - [1]: Position Y (can be negative for below/shadow)
    - [2]: Velocity/momentum
    - [3]: Priority/urgency
    - [4]: Security level (negative = restricted)
    - [5]: Trust baseline
    - [6+]: Extended dimensions (intent, phase, etc.)
    """
    components: np.ndarray

    def __init__(self, components: List[float]):
        self.components = np.array(components, dtype=np.float64)
        if len(self.components) < 6:
            raise ValueError("ContextVector must have at least 6 dimensions")

    def __repr__(self):
        return f"ContextVector({self.components.tolist()})"

    def __len__(self):
        return len(self.components)

    @property
    def position(self) -> np.ndarray:
        """First 2 components as position."""
        return self.components[:2]

    @property
    def has_negative(self) -> bool:
        """Check if any component is negative."""
        return np.any(self.components < 0)

    @property
    def negative_mask(self) -> np.ndarray:
        """Boolean mask of negative components."""
        return self.components < 0

    @property
    def signed_magnitude(self) -> float:
        """Magnitude preserving dominant sign."""
        positive_sum = np.sum(self.components[self.components > 0])
        negative_sum = np.sum(self.components[self.components < 0])
        if abs(positive_sum) > abs(negative_sum):
            return np.linalg.norm(self.components)
        else:
            return -np.linalg.norm(self.components)

    def to_poincare(self, scale: float = 0.9) -> np.ndarray:
        """
        Project into Poincare ball (||v|| < 1).

        Uses tanh normalization to map to open ball while preserving
        relative magnitudes and signs.
        """
        # Normalize each component independently using tanh
        return scale * np.tanh(self.components / 10.0)

    def to_lattice_10d(
        self,
        tongue_mapping: Dict[int, float] = None
    ) -> np.ndarray:
        """
        Map context vector to 10D dual lattice space.

        Mapping:
        - components[0:6] -> tongue dimensions (scaled)
        - If more components: [6]->time, [7]->intent, [8]->phase, [9]->flux
        """
        result = np.zeros(10)

        # Map first 6 components to tongue dimensions (scaled to [0,1])
        for i in range(min(6, len(self.components))):
            # Use sigmoid to map arbitrary floats to [0,1]
            # Negative values map below 0.5, positive above
            result[i] = 1 / (1 + np.exp(-self.components[i]))

        # Map additional dimensions if present
        if len(self.components) > 6:
            result[6] = 1 / (1 + np.exp(-self.components[6]))  # time
        if len(self.components) > 7:
            result[7] = 1 / (1 + np.exp(-self.components[7]))  # intent
        if len(self.components) > 8:
            result[8] = (self.components[8] % 360) / 360.0  # phase (normalized)
        if len(self.components) > 9:
            result[9] = 1 / (1 + np.exp(-self.components[9]))  # flux

        return result


def bytes_to_signed_signal(byte_data: bytes) -> np.ndarray:
    """
    Convert 0-255 bytes to float32 signal in [-1.0, 1.0].

    This is essential for FFT analysis where DC offset (unsigned values)
    would corrupt frequency analysis.
    """
    arr = np.frombuffer(byte_data, dtype=np.uint8)
    return (arr.astype(np.float32) - 127.5) / 127.5


def signed_signal_to_bytes(signal: np.ndarray) -> bytes:
    """Convert signed [-1.0, 1.0] signal back to 0-255 bytes."""
    arr = ((signal * 127.5) + 127.5).clip(0, 255).astype(np.uint8)
    return arr.tobytes()


# =============================================================================
# Hyperbolic Geometry (Poincare Ball Model)
# =============================================================================

def hyperbolic_distance(
    x: np.ndarray,
    y: np.ndarray,
    curvature: float = -1.0,
    eps: float = 1e-8
) -> float:
    """
    Poincare ball hyperbolic distance.

    Always >= 0 for valid points inside the ball (||x|| < 1, ||y|| < 1).
    Negative distance is mathematically impossible -> rejected.

    Formula: d(x,y) = arcosh(1 + 2||x-y||^2 / ((1-||x||^2)(1-||y||^2)))

    Args:
        x, y: Points in the Poincare ball (||v|| < 1)
        curvature: Curvature constant (default -1 for standard hyperbolic)
        eps: Small epsilon for numerical stability
    """
    nx = np.dot(x, x)
    ny = np.dot(y, y)

    if nx >= 1.0 or ny >= 1.0:
        raise ValueError("Points must lie strictly inside the Poincare ball (||v|| < 1)")

    diff_norm_sq = np.dot(x - y, x - y)
    denominator = (1 - nx) * (1 - ny)
    arg = 1 + 2 * diff_norm_sq / (denominator + eps)

    if arg < 1.0:
        # This should never happen for valid points, but we enforce the constraint
        raise ValueError("Invalid hyperbolic argument < 1 -> negative/complex distance impossible")

    # Scale by curvature
    c = abs(curvature)
    return np.arccosh(arg) / np.sqrt(c)


def hyperbolic_midpoint(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    Compute midpoint on hyperbolic geodesic between x and y.

    Uses Mobius addition formula for Poincare ball.
    """
    # Mobius addition: x (+) y = ((1 + 2<x,y> + ||y||^2)x + (1 - ||x||^2)y) /
    #                           (1 + 2<x,y> + ||x||^2||y||^2)
    xy = np.dot(x, y)
    nx = np.dot(x, x)
    ny = np.dot(y, y)

    # Midpoint is (x (+) y) / 2 in Mobius sense
    # Simplified: scale the Euclidean midpoint back into the ball
    euclidean_mid = (x + y) / 2
    scale = 1 - np.dot(euclidean_mid, euclidean_mid)

    if scale <= 0:
        # Midpoint would be outside ball, project back
        return euclidean_mid / (np.linalg.norm(euclidean_mid) + 0.01) * 0.9

    return euclidean_mid


def hyperbolic_angle(a: float, b: float, c: float) -> float:
    """
    Hyperbolic law of cosines for angle opposite side c.

    In hyperbolic space, triangle angle sum < 180 degrees.
    """
    cosh_c = np.cosh(c)
    cosh_a = np.cosh(a)
    cosh_b = np.cosh(b)
    sinh_a = np.sinh(a)
    sinh_b = np.sinh(b)

    if sinh_a == 0 or sinh_b == 0:
        return 0.0

    cos_angle = (cosh_a * cosh_b - cosh_c) / (sinh_a * sinh_b)
    # Clamp to valid range for arccosh
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    return np.arccos(cos_angle)


def compute_triangle_deficit(a: float, b: float, c: float) -> float:
    """
    Compute angular deficit of hyperbolic triangle.

    Returns: 180 - (sum of angles in degrees)
    Positive deficit confirms negative curvature.
    """
    angle_A = hyperbolic_angle(b, c, a)
    angle_B = hyperbolic_angle(a, c, b)
    angle_C = hyperbolic_angle(a, b, c)

    sum_degrees = np.degrees(angle_A + angle_B + angle_C)
    return 180.0 - sum_degrees


# =============================================================================
# Harmonic Wall Integration
# =============================================================================

def harmonic_wall_cost(
    distance: float,
    radius: float = 1.0,
    base: float = 2.718281828  # e
) -> float:
    """
    Compute harmonic wall cost: H(d) = base^(d^2).

    As distance approaches the Poincare ball boundary,
    cost approaches infinity exponentially.
    """
    # Normalize distance by radius
    normalized = distance / radius
    return base ** (normalized ** 2)


def trust_from_position(
    point: np.ndarray,
    center: np.ndarray = None,
    radius: float = 0.9
) -> float:
    """
    Compute trust score from position in Poincare ball.

    - Center (origin) = maximum trust (1.0)
    - Boundary = minimum trust (0.0)

    Trust decays hyperbolically with distance from center.
    """
    if center is None:
        center = np.zeros_like(point)

    # Ensure point is inside ball
    point_norm = np.linalg.norm(point)
    if point_norm >= 1.0:
        # Project back inside ball
        point = point / (point_norm + 0.01) * 0.95

    center_norm = np.linalg.norm(center)
    if center_norm >= 1.0:
        center = center / (center_norm + 0.01) * 0.95

    try:
        d = hyperbolic_distance(point, center)
    except ValueError:
        # Fallback: use Euclidean distance
        d = np.linalg.norm(point - center)

    # Reference distance: from center to near boundary (in 2D subspace)
    # This avoids the multi-dimensional norm issue
    boundary_point = np.zeros_like(center)
    boundary_point[0] = radius * 0.98  # Single dimension near boundary

    try:
        max_d = hyperbolic_distance(boundary_point, center)
    except ValueError:
        max_d = 3.0  # Reasonable fallback

    # Hyperbolic decay
    trust = 1.0 / (1.0 + d / max_d)
    return float(trust)


# =============================================================================
# Tests (from documentation)
# =============================================================================

if __name__ == "__main__":
    # Test context vector with negative components
    test_ctx = ContextVector([0.2, -0.3, 0.7, 1.0, -2.0, 0.5, 3.1, -9.9, 0.0])
    print(f"[GEO] Test context vector: {test_ctx}")
    print(f"[GEO] Has negative components: {test_ctx.has_negative}")
    print(f"[GEO] Negative mask: {test_ctx.negative_mask}")
    print(f"[GEO] Signed magnitude: {test_ctx.signed_magnitude:.3f}")

    # Project to Poincare ball
    poincare_point = test_ctx.to_poincare()
    print(f"[GEO] Poincare projection: {poincare_point}")

    # Map to 10D lattice
    lattice_10d = test_ctx.to_lattice_10d()
    print(f"[GEO] 10D Lattice mapping: {lattice_10d}")

    # Test F10: negative hyperbolic distance impossible
    print("\n[TEST F10] Hyperbolic distance test...")
    x = np.array([0.1, -0.2])
    y = np.array([-0.3, 0.4])
    d = hyperbolic_distance(x, y)
    assert d >= 0.0
    print(f"[GEO] Valid distance: {d:.4f} (always positive)")

    # Test negative curvature: triangle angle sum < 180
    print("\n[TEST] Negative curvature verification...")
    a = b = c = 0.5  # equilateral-ish hyperbolic triangle
    deficit = compute_triangle_deficit(a, b, c)
    print(f"[GEO] Triangle angle deficit: {deficit:.2f}deg (positive = negative curvature)")

    # Test harmonic wall
    print("\n[TEST] Harmonic wall cost...")
    for d in [0.1, 0.5, 0.9, 0.99]:
        cost = harmonic_wall_cost(d)
        print(f"[GEO] d={d:.2f} -> H(d)={cost:.2f}")

    # Test trust from position
    print("\n[TEST] Trust from position...")
    for pos in [[0.0, 0.0], [0.3, 0.3], [0.6, 0.6], [0.85, 0.0]]:
        trust = trust_from_position(np.array(pos))
        print(f"[GEO] pos={pos} -> trust={trust:.3f}")
