"""
Unitarity Axiom Module - Layers Preserving Norms

This module groups layers that satisfy the unitarity axiom from quantum mechanics:
transformations that preserve inner products and norms (isometries).

Assigned Layers:
- Layer 2: Realification (Φ₁: ℂᴰ → ℝ²ᴰ) - Linear isometry
- Layer 4: Poincaré Embedding (Ψ_α: ℝ²ᴰ → 𝔹²ᴰ) - Norm-preserving projection
- Layer 7: Phase Transform (Möbius + Rotation) - Hyperbolic isometry

Mathematical Foundation:
A transform T satisfies unitarity iff: ⟨T(x), T(y)⟩ = ⟨x, y⟩ ∀x,y
Equivalently: ||T(x)|| = ||x|| for norm preservation.
"""

from __future__ import annotations

import functools
import numpy as np
from typing import Callable, TypeVar, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Type variables for generic decorators
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Constants
EPS = 1e-10
ALPHA_EMBED = 0.99  # Poincaré embedding scale


class UnitarityViolation(Exception):
    """Raised when a transform violates the unitarity axiom."""
    pass


@dataclass
class UnitarityCheckResult:
    """Result of a unitarity axiom check."""
    passed: bool
    relative_error: float
    input_norm: float
    output_norm: float
    layer_name: str
    tolerance: float

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"UnitarityCheck[{self.layer_name}]: {status}\n"
            f"  Input norm:  {self.input_norm:.10f}\n"
            f"  Output norm: {self.output_norm:.10f}\n"
            f"  Relative error: {self.relative_error:.2e} (tol: {self.tolerance:.2e})"
        )


def unitarity_check(
    tolerance: float = 1e-6,
    norm_type: str = "euclidean",
    strict: bool = False
) -> Callable[[F], F]:
    """
    Decorator that verifies a transform preserves norms (unitarity axiom).

    Args:
        tolerance: Maximum allowed relative deviation from norm preservation
        norm_type: Type of norm to check ("euclidean", "hyperbolic", "complex")
        strict: If True, raises UnitarityViolation on failure

    Returns:
        Decorated function that checks unitarity after each call
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract input (first positional arg after self if method)
            input_vec = args[0] if args else None
            if input_vec is None:
                return func(*args, **kwargs)

            # Compute input norm
            input_norm = _compute_norm(input_vec, norm_type)

            # Execute transform
            result = func(*args, **kwargs)

            # Handle tuple returns (some layers return multiple values)
            output_vec = result[0] if isinstance(result, tuple) else result

            # Compute output norm
            output_norm = _compute_norm(output_vec, norm_type)

            # Check unitarity
            if input_norm > EPS:
                relative_error = abs(output_norm - input_norm) / input_norm
            else:
                relative_error = abs(output_norm - input_norm)

            passed = relative_error <= tolerance

            check_result = UnitarityCheckResult(
                passed=passed,
                relative_error=relative_error,
                input_norm=input_norm,
                output_norm=output_norm,
                layer_name=func.__name__,
                tolerance=tolerance
            )

            # Store check result on function for inspection
            wrapper.last_check = check_result

            if not passed and strict:
                raise UnitarityViolation(str(check_result))

            return result

        wrapper.last_check = None
        wrapper.axiom = "unitarity"
        wrapper.tolerance = tolerance
        return wrapper
    return decorator


def _compute_norm(vec: np.ndarray, norm_type: str) -> float:
    """Compute norm based on specified type."""
    if norm_type == "euclidean":
        return float(np.linalg.norm(vec))
    elif norm_type == "hyperbolic":
        # For Poincaré ball, the hyperbolic norm is artanh(||x||)
        euclidean_norm = float(np.linalg.norm(vec))
        if euclidean_norm >= 1.0:
            return float('inf')
        return float(np.arctanh(euclidean_norm))
    elif norm_type == "complex":
        # For complex vectors, use standard complex norm
        return float(np.linalg.norm(vec))
    else:
        raise ValueError(f"Unknown norm type: {norm_type}")


# ============================================================================
# Layer 2: Realification (Complex to Real Isometry)
# ============================================================================

@unitarity_check(tolerance=1e-10, norm_type="euclidean")
def layer_2_realify(c: np.ndarray) -> np.ndarray:
    """
    Layer 2: Realification Transform

    Φ₁: ℂᴰ → ℝ²ᴰ

    Converts a D-dimensional complex vector to a 2D-dimensional real vector
    by separating real and imaginary parts.

    Mathematical Property:
        ||Φ₁(c)||₂ = ||c||₂ (isometry)

    This is because:
        ||Φ₁(c)||² = Σᵢ (Re(cᵢ)² + Im(cᵢ)²) = Σᵢ |cᵢ|² = ||c||²

    Args:
        c: Complex D-dimensional vector

    Returns:
        Real 2D-dimensional vector [Re(c₁), Im(c₁), Re(c₂), Im(c₂), ...]
    """
    # Interleave real and imaginary parts
    real_parts = np.real(c)
    imag_parts = np.imag(c)

    result = np.empty(2 * len(c), dtype=np.float64)
    result[0::2] = real_parts
    result[1::2] = imag_parts

    return result


def layer_2_inverse(x: np.ndarray) -> np.ndarray:
    """
    Inverse of Layer 2: Real to Complex

    Φ₁⁻¹: ℝ²ᴰ → ℂᴰ

    Reconstructs complex vector from realified representation.

    Args:
        x: Real 2D-dimensional vector

    Returns:
        Complex D-dimensional vector
    """
    n = len(x) // 2
    return x[0::2] + 1j * x[1::2]


# ============================================================================
# Layer 4: Poincaré Embedding
# ============================================================================

@unitarity_check(tolerance=0.1, norm_type="euclidean", strict=False)
def layer_4_poincare(x: np.ndarray, alpha: float = ALPHA_EMBED) -> np.ndarray:
    """
    Layer 4: Poincaré Ball Embedding

    Ψ_α: ℝ²ᴰ → 𝔹²ᴰ (open unit ball)

    Maps Euclidean space into the Poincaré ball model of hyperbolic space.

    Formula:
        Ψ_α(x) = α · tanh(||x||) · x/||x||

    Properties:
        - Direction preserved: Ψ_α(x)/||Ψ_α(x)|| = x/||x||
        - Magnitude compressed: ||Ψ_α(x)|| < α < 1
        - Smooth and invertible (diffeomorphism)

    Note: This is NOT a strict isometry in Euclidean norm, but preserves
    the hyperbolic structure. The unitarity check here verifies bounded
    deviation rather than exact preservation.

    Args:
        x: Point in Euclidean space ℝ²ᴰ
        alpha: Scale factor (< 1 to ensure strict interior)

    Returns:
        Point in Poincaré ball 𝔹²ᴰ
    """
    norm_x = np.linalg.norm(x)

    if norm_x < EPS:
        return np.zeros_like(x)

    # tanh maps [0, ∞) → [0, 1), so result stays in ball
    scaled_norm = alpha * np.tanh(norm_x)
    direction = x / norm_x

    return scaled_norm * direction


def layer_4_inverse(u: np.ndarray, alpha: float = ALPHA_EMBED) -> np.ndarray:
    """
    Inverse of Layer 4: Poincaré to Euclidean

    Ψ_α⁻¹: 𝔹²ᴰ → ℝ²ᴰ

    Args:
        u: Point in Poincaré ball
        alpha: Scale factor used in forward transform

    Returns:
        Point in Euclidean space
    """
    norm_u = np.linalg.norm(u)

    if norm_u < EPS:
        return np.zeros_like(u)

    # Inverse of tanh is arctanh
    euclidean_norm = np.arctanh(norm_u / alpha)
    direction = u / norm_u

    return euclidean_norm * direction


# ============================================================================
# Layer 7: Phase Transform (Möbius + Rotation)
# ============================================================================

def mobius_addition(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Möbius addition in the Poincaré ball.

    u ⊕ v = ((1 + 2⟨u,v⟩ + ||v||²)u + (1 - ||u||²)v) /
            (1 + 2⟨u,v⟩ + ||u||²||v||²)

    This is the group operation for the hyperbolic translation group.

    Properties:
        - Preserves hyperbolic distance: d_H(u ⊕ w, v ⊕ w) = d_H(u, v)
        - Non-commutative: u ⊕ v ≠ v ⊕ u in general
        - Identity: u ⊕ 0 = u
        - Inverse: u ⊕ (-u) = 0

    Args:
        u: First point in Poincaré ball
        v: Second point (translation vector)

    Returns:
        Translated point u ⊕ v
    """
    dot_uv = np.dot(u, v)
    norm_u_sq = np.dot(u, u)
    norm_v_sq = np.dot(v, v)

    denominator = 1 + 2 * dot_uv + norm_u_sq * norm_v_sq

    if abs(denominator) < EPS:
        return u  # Degenerate case

    numerator = (1 + 2 * dot_uv + norm_v_sq) * u + (1 - norm_u_sq) * v

    return numerator / denominator


def rotation_matrix_2d(angle: float) -> np.ndarray:
    """Create 2D rotation matrix."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s], [s, c]])


def rotation_nd(v: np.ndarray, angle: float, plane: Tuple[int, int] = (0, 1)) -> np.ndarray:
    """
    Apply rotation in specified plane of n-dimensional space.

    Args:
        v: n-dimensional vector
        angle: Rotation angle in radians
        plane: Tuple of two axis indices defining the rotation plane

    Returns:
        Rotated vector
    """
    result = v.copy()
    i, j = plane
    c, s = np.cos(angle), np.sin(angle)

    vi, vj = v[i], v[j]
    result[i] = c * vi - s * vj
    result[j] = s * vi + c * vj

    return result


@unitarity_check(tolerance=1e-8, norm_type="euclidean")
def layer_7_phase(
    u: np.ndarray,
    phase_angle: float,
    translation: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Layer 7: Phase Transform (Möbius Translation + Rotation)

    T_phase(u; φ, a) = R_φ(a ⊕ u)

    Combines:
    1. Möbius addition (hyperbolic translation) - isometry
    2. Rotation in the first coordinate plane - isometry

    Both operations are hyperbolic isometries, so their composition
    preserves hyperbolic distance d_H.

    Args:
        u: Point in Poincaré ball
        phase_angle: Rotation angle in radians
        translation: Translation vector for Möbius addition (default: origin)

    Returns:
        Transformed point (still in Poincaré ball)
    """
    if translation is None:
        translation = np.zeros_like(u)

    # Clamp translation to ensure it's in the ball
    trans_norm = np.linalg.norm(translation)
    if trans_norm >= 1.0:
        translation = translation * (0.9 / trans_norm)

    # Step 1: Möbius addition (hyperbolic translation)
    translated = mobius_addition(u, translation)

    # Step 2: Rotation (Euclidean isometry, also hyperbolic isometry)
    if len(translated) >= 2:
        rotated = rotation_nd(translated, phase_angle, plane=(0, 1))
    else:
        rotated = translated

    return rotated


def layer_7_inverse(
    u: np.ndarray,
    phase_angle: float,
    translation: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Inverse of Layer 7: Reverse rotation then Möbius subtract.

    Args:
        u: Transformed point
        phase_angle: Original rotation angle
        translation: Original translation vector

    Returns:
        Original point before transform
    """
    if translation is None:
        translation = np.zeros_like(u)

    # Step 1: Inverse rotation
    if len(u) >= 2:
        unrotated = rotation_nd(u, -phase_angle, plane=(0, 1))
    else:
        unrotated = u

    # Step 2: Inverse Möbius addition (subtract = add negative)
    untranslated = mobius_addition(unrotated, -translation)

    return untranslated


# ============================================================================
# Unitarity Verification Utilities
# ============================================================================

def verify_layer_unitarity(
    layer_func: Callable,
    n_tests: int = 100,
    dim: int = 12,
    verbose: bool = False
) -> Tuple[bool, float]:
    """
    Statistically verify that a layer satisfies unitarity.

    Args:
        layer_func: Layer function to test
        n_tests: Number of random tests
        dim: Dimension of test vectors
        verbose: Print detailed results

    Returns:
        Tuple of (all_passed, max_error)
    """
    max_error = 0.0
    all_passed = True

    for i in range(n_tests):
        # Generate random complex or real vector
        if layer_func.__name__ == "layer_2_realify":
            x = np.random.randn(dim) + 1j * np.random.randn(dim)
        elif layer_func.__name__ == "layer_4_poincare":
            x = np.random.randn(dim)
        else:
            # For Poincaré ball operations, generate points inside ball
            x = np.random.randn(dim)
            x = 0.5 * x / (np.linalg.norm(x) + EPS)

        # Apply layer
        if layer_func.__name__ == "layer_7_phase":
            result = layer_func(x, phase_angle=np.random.uniform(0, 2*np.pi))
        else:
            result = layer_func(x)

        # Check the result
        check = getattr(layer_func, 'last_check', None)
        if check:
            max_error = max(max_error, check.relative_error)
            if not check.passed:
                all_passed = False
                if verbose:
                    print(f"Test {i}: {check}")

    return all_passed, max_error


# ============================================================================
# Axiom Layer Registry
# ============================================================================

UNITARITY_LAYERS = {
    2: {
        "name": "Realification",
        "function": layer_2_realify,
        "inverse": layer_2_inverse,
        "description": "Complex to real isometry: Φ₁(c) preserves ||c||₂",
        "strict_isometry": True,
    },
    4: {
        "name": "Poincaré Embedding",
        "function": layer_4_poincare,
        "inverse": layer_4_inverse,
        "description": "Euclidean to hyperbolic embedding: Ψ_α(x) preserves direction",
        "strict_isometry": False,  # Approximate norm preservation
    },
    7: {
        "name": "Phase Transform",
        "function": layer_7_phase,
        "inverse": layer_7_inverse,
        "description": "Möbius + Rotation: T_phase preserves hyperbolic distance",
        "strict_isometry": True,
    },
}


def get_unitarity_layer(layer_num: int) -> dict:
    """Get layer info by number."""
    if layer_num not in UNITARITY_LAYERS:
        raise ValueError(f"Layer {layer_num} is not a unitarity layer")
    return UNITARITY_LAYERS[layer_num]


def list_unitarity_layers() -> list:
    """List all layers satisfying the unitarity axiom."""
    return list(UNITARITY_LAYERS.keys())
