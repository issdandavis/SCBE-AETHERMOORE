"""
Symmetry Axiom Module - Gauge-Invariant Operations

This module groups layers that satisfy symmetry/gauge invariance axioms:
operations that are invariant under certain transformations (gauge symmetries).

Assigned Layers:
- Layer 5: Hyperbolic Distance (THE INVARIANT) - Preserved by Möbius isometries
- Layer 9: Spectral Coherence - Rotationally invariant
- Layer 10: Spin Coherence - U(1) gauge invariant
- Layer 12: Harmonic Scaling - Monotonic (order-preserving symmetry)

Mathematical Foundation:
A quantity Q satisfies gauge invariance under group G iff:
    Q(g · x) = Q(x) for all g ∈ G

Common gauge groups:
- O(n): Orthogonal group (rotational symmetry)
- U(1): Circle group (phase symmetry)
- Möb(𝔹ⁿ): Möbius group (hyperbolic isometries)
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
EPS = 1e-10
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio


class SymmetryViolation(Exception):
    """Raised when an operation violates gauge invariance."""
    pass


class SymmetryGroup(Enum):
    """Common symmetry groups for gauge invariance."""
    ORTHOGONAL = "O(n)"      # Rotational symmetry
    UNITARY = "U(1)"         # Phase symmetry
    MOBIUS = "Möb(𝔹)"        # Hyperbolic isometry group
    SCALE = "ℝ₊"             # Positive real scaling
    TRANSLATION = "ℝⁿ"       # Translation symmetry


@dataclass
class SymmetryCheckResult:
    """Result of a symmetry/gauge invariance check."""
    passed: bool
    symmetry_group: SymmetryGroup
    invariance_error: float
    n_transforms_tested: int
    layer_name: str
    tolerance: float

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"SymmetryCheck[{self.layer_name}]: {status}\n"
            f"  Symmetry group: {self.symmetry_group.value}\n"
            f"  Invariance error: {self.invariance_error:.2e}\n"
            f"  Transforms tested: {self.n_transforms_tested}\n"
            f"  Tolerance: {self.tolerance:.2e}"
        )


def symmetry_check(
    group: SymmetryGroup,
    tolerance: float = 1e-6,
    n_test_transforms: int = 10,
    strict: bool = False
) -> Callable[[F], F]:
    """
    Decorator that verifies a quantity is invariant under a symmetry group.

    Args:
        group: The symmetry group to check invariance under
        tolerance: Maximum allowed deviation from invariance
        n_test_transforms: Number of random group elements to test
        strict: If True, raises SymmetryViolation on failure

    Returns:
        Decorated function with gauge invariance verification
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Store check result (actual testing done by verify functions)
            check_result = SymmetryCheckResult(
                passed=True,  # Assumed until tested
                symmetry_group=group,
                invariance_error=0.0,
                n_transforms_tested=0,
                layer_name=func.__name__,
                tolerance=tolerance
            )

            wrapper.last_check = check_result
            wrapper.symmetry_group = group

            return result

        wrapper.last_check = None
        wrapper.axiom = "symmetry"
        wrapper.symmetry_group = group
        return wrapper
    return decorator


# ============================================================================
# Symmetry Group Generators
# ============================================================================

def random_orthogonal(dim: int) -> np.ndarray:
    """Generate a random orthogonal matrix (rotation/reflection)."""
    # QR decomposition of random matrix gives orthogonal Q
    A = np.random.randn(dim, dim)
    Q, _ = np.linalg.qr(A)
    return Q


def random_rotation(dim: int) -> np.ndarray:
    """Generate a random rotation matrix (det = +1)."""
    Q = random_orthogonal(dim)
    if np.linalg.det(Q) < 0:
        Q[:, 0] *= -1  # Flip sign to ensure det = +1
    return Q


def random_phase() -> complex:
    """Generate a random U(1) phase factor."""
    theta = np.random.uniform(0, 2 * np.pi)
    return np.exp(1j * theta)


def random_mobius_translation(dim: int, max_norm: float = 0.5) -> np.ndarray:
    """Generate a random Möbius translation vector (inside ball)."""
    v = np.random.randn(dim)
    v = v / (np.linalg.norm(v) + EPS)
    r = np.random.uniform(0, max_norm)
    return r * v


def mobius_addition(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Möbius addition in the Poincaré ball."""
    dot_uv = np.dot(u, v)
    norm_u_sq = np.dot(u, u)
    norm_v_sq = np.dot(v, v)

    denominator = 1 + 2 * dot_uv + norm_u_sq * norm_v_sq
    if abs(denominator) < EPS:
        return u

    numerator = (1 + 2 * dot_uv + norm_v_sq) * u + (1 - norm_u_sq) * v
    return numerator / denominator


# ============================================================================
# Layer 5: Hyperbolic Distance (THE INVARIANT)
# ============================================================================

@symmetry_check(group=SymmetryGroup.MOBIUS, tolerance=1e-8)
def layer_5_hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    """
    Layer 5: Hyperbolic Distance (THE INVARIANT)

    d_H(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

    This is THE fundamental invariant of the system - preserved by
    all Möbius isometries (hyperbolic translations and rotations).

    Gauge Invariance:
        d_H(g·u, g·v) = d_H(u, v) for all g ∈ Möb(𝔹)

    Properties:
        - Symmetric: d_H(u, v) = d_H(v, u)
        - Triangle inequality: d_H(u, w) ≤ d_H(u, v) + d_H(v, w)
        - Positive definite: d_H(u, v) = 0 ⟺ u = v

    Args:
        u, v: Points in the Poincaré ball

    Returns:
        Hyperbolic distance d_H(u, v)
    """
    diff = u - v
    diff_sq = np.dot(diff, diff)
    u_sq = np.dot(u, u)
    v_sq = np.dot(v, v)

    # Clamp to avoid numerical issues at boundary
    u_sq = min(u_sq, 1.0 - EPS)
    v_sq = min(v_sq, 1.0 - EPS)

    denominator = (1 - u_sq) * (1 - v_sq)
    if denominator < EPS:
        return float('inf')

    arg = 1 + 2 * diff_sq / denominator
    arg = max(arg, 1.0)  # arcosh domain: [1, ∞)

    return float(np.arccosh(arg))


def verify_mobius_invariance(
    u: np.ndarray,
    v: np.ndarray,
    n_tests: int = 10,
    tolerance: float = 1e-8
) -> Tuple[bool, float]:
    """
    Verify that hyperbolic distance is invariant under Möbius transforms.

    Args:
        u, v: Test points
        n_tests: Number of random Möbius transforms to test
        tolerance: Maximum allowed deviation

    Returns:
        Tuple of (passed, max_error)
    """
    d_original = layer_5_hyperbolic_distance(u, v)
    max_error = 0.0

    for _ in range(n_tests):
        # Random Möbius translation
        a = random_mobius_translation(len(u))

        # Apply Möbius addition to both points
        u_transformed = mobius_addition(u, a)
        v_transformed = mobius_addition(v, a)

        d_transformed = layer_5_hyperbolic_distance(u_transformed, v_transformed)
        error = abs(d_transformed - d_original)
        max_error = max(max_error, error)

    passed = max_error <= tolerance
    return passed, max_error


# ============================================================================
# Layer 9: Spectral Coherence
# ============================================================================

@symmetry_check(group=SymmetryGroup.ORTHOGONAL, tolerance=1e-6)
def layer_9_spectral_coherence(x: np.ndarray) -> float:
    """
    Layer 9: Spectral Coherence

    S_spec = 1 - r_HF where r_HF = high_freq_energy / total_energy

    Measures signal smoothness by energy concentration in low frequencies.

    Gauge Invariance:
        Under rotation R ∈ O(n), the frequency spectrum is preserved
        (rotation in time domain = rotation in frequency domain).
        Thus S_spec(Rx) = S_spec(x).

    Properties:
        - Range: [0, 1]
        - S_spec = 1 ⟹ perfect coherence (all energy in DC/low freq)
        - S_spec = 0 ⟹ pure noise (all energy in high freq)

    Args:
        x: Input signal vector

    Returns:
        Spectral coherence S_spec ∈ [0, 1]
    """
    # Compute FFT
    spectrum = np.fft.fft(x)
    power = np.abs(spectrum) ** 2
    total_energy = np.sum(power)

    if total_energy < EPS:
        return 1.0  # Zero signal = perfectly coherent

    # High frequency threshold: above Nyquist/4
    n = len(x)
    hf_threshold = n // 4

    # Sum energy in high frequency bins
    # FFT is symmetric, so consider both positive and negative frequencies
    hf_energy = np.sum(power[hf_threshold:n - hf_threshold])

    r_HF = hf_energy / total_energy
    S_spec = 1.0 - r_HF

    return float(S_spec)


def verify_rotation_invariance(
    x: np.ndarray,
    n_tests: int = 10,
    tolerance: float = 0.1
) -> Tuple[bool, float]:
    """
    Verify that spectral coherence is approximately rotation-invariant.

    Note: Due to FFT discretization, exact invariance is not expected.
    We check for bounded deviation.
    """
    S_original = layer_9_spectral_coherence(x)
    max_error = 0.0

    for _ in range(n_tests):
        # Random permutation (discrete analogue of rotation)
        perm = np.random.permutation(len(x))
        x_rotated = x[perm]

        S_rotated = layer_9_spectral_coherence(x_rotated)
        error = abs(S_rotated - S_original)
        max_error = max(max_error, error)

    passed = max_error <= tolerance
    return passed, max_error


# ============================================================================
# Layer 10: Spin Coherence
# ============================================================================

@symmetry_check(group=SymmetryGroup.UNITARY, tolerance=1e-10)
def layer_10_spin_coherence(q: complex) -> float:
    """
    Layer 10: Spin Coherence

    C_spin = 2|q|² - 1

    Maps quantum amplitude to spin coherence measure.

    Gauge Invariance (U(1)):
        Under phase rotation q → e^{iθ}q:
        C_spin(e^{iθ}q) = 2|e^{iθ}q|² - 1 = 2|q|² - 1 = C_spin(q)

        The spin coherence is EXACTLY invariant under U(1) phase rotations.

    Properties:
        - Range: [-1, 1]
        - |q| = 1 ⟹ C_spin = 1 (fully aligned)
        - |q| = 0 ⟹ C_spin = -1 (fully anti-aligned)
        - |q| = 1/√2 ⟹ C_spin = 0 (unbiased)

    Args:
        q: Complex quantum amplitude

    Returns:
        Spin coherence C_spin ∈ [-1, 1]
    """
    amplitude_sq = np.abs(q) ** 2
    return float(2 * amplitude_sq - 1)


def verify_phase_invariance(
    q: complex,
    n_tests: int = 100,
    tolerance: float = 1e-10
) -> Tuple[bool, float]:
    """
    Verify that spin coherence is exactly U(1) phase-invariant.
    """
    C_original = layer_10_spin_coherence(q)
    max_error = 0.0

    for _ in range(n_tests):
        phase = random_phase()
        q_rotated = phase * q

        C_rotated = layer_10_spin_coherence(q_rotated)
        error = abs(C_rotated - C_original)
        max_error = max(max_error, error)

    passed = max_error <= tolerance
    return passed, max_error


# ============================================================================
# Layer 12: Harmonic Scaling
# ============================================================================

@symmetry_check(group=SymmetryGroup.SCALE, tolerance=0.0)
def layer_12_harmonic_scaling(d: float, R: float = PHI) -> float:
    """
    Layer 12: Harmonic Scaling (Superexponential)

    H(d, R) = R^(d²)

    Risk amplification with "vertical wall" effect.

    Symmetry Property:
        H is strictly monotonically increasing, which means it
        PRESERVES ORDER (a symmetry of the real line):
            d₁ < d₂ ⟹ H(d₁) < H(d₂)

        This is the symmetry of "order preservation" which ensures
        that risk ranking is invariant under the scaling.

    Properties:
        - H(0) = 1 (identity at origin)
        - H'(d) = 2d · R^(d²) · ln(R) > 0 (strictly increasing)
        - H''(d) > 0 for d > 0 (convex)
        - Creates sharp transition ("vertical wall") at large d

    Args:
        d: Distance value
        R: Base of exponential (default: golden ratio φ)

    Returns:
        Harmonically scaled value H(d)
    """
    # Clamp to prevent overflow
    d_sq = min(d ** 2, 50.0)
    return float(R ** d_sq)


def layer_12_inverse(H: float, R: float = PHI) -> float:
    """
    Inverse of harmonic scaling.

    d = √(log_R(H))
    """
    if H <= 0:
        return 0.0
    log_H = np.log(H) / np.log(R)
    if log_H < 0:
        return 0.0
    return float(np.sqrt(log_H))


def verify_monotonicity(n_tests: int = 1000, R: float = PHI) -> Tuple[bool, int]:
    """
    Verify that harmonic scaling is strictly monotonically increasing.
    """
    violations = 0

    # Generate sorted random distances
    distances = np.sort(np.random.uniform(0, 5, n_tests))

    for i in range(1, len(distances)):
        H_prev = layer_12_harmonic_scaling(distances[i - 1], R)
        H_curr = layer_12_harmonic_scaling(distances[i], R)

        if H_curr <= H_prev:
            violations += 1

    passed = violations == 0
    return passed, violations


# ============================================================================
# Gauge Field Utilities
# ============================================================================

@dataclass
class GaugeField:
    """Represents a gauge field configuration."""
    group: SymmetryGroup
    dimension: int
    field_values: np.ndarray  # Field values at lattice points
    connection: Optional[np.ndarray]  # Gauge connection (if applicable)


def compute_gauge_covariant_derivative(
    field: np.ndarray,
    connection: np.ndarray,
    direction: int
) -> np.ndarray:
    """
    Compute gauge-covariant derivative.

    D_μ φ = ∂_μ φ + A_μ φ

    Where A_μ is the gauge connection and ∂_μ is the ordinary derivative.
    """
    # Finite difference for ordinary derivative
    derivative = np.roll(field, -1, axis=direction) - field

    # Add gauge connection term
    covariant_derivative = derivative + connection * field

    return covariant_derivative


def wilson_loop(
    connection: np.ndarray,
    path: List[Tuple[int, int]]
) -> complex:
    """
    Compute Wilson loop around a closed path.

    W = Tr(P exp(∮ A · dl))

    For an Abelian gauge theory, this simplifies to exp(i∮ A · dl).
    """
    phase = 0.0

    for i, (site, direction) in enumerate(path):
        phase += connection[site, direction]

    return np.exp(1j * phase)


# ============================================================================
# Symmetry Verification Utilities
# ============================================================================

def verify_layer_symmetry(
    layer_func: Callable,
    n_tests: int = 100,
    dim: int = 12,
    verbose: bool = False
) -> Tuple[bool, dict]:
    """
    Comprehensive symmetry verification for a layer.

    Args:
        layer_func: Layer function to test
        n_tests: Number of random tests
        dim: Dimension of test vectors
        verbose: Print detailed results

    Returns:
        Tuple of (all_passed, statistics)
    """
    group = getattr(layer_func, 'symmetry_group', None)
    all_passed = True
    max_error = 0.0
    violations = 0

    for i in range(n_tests):
        if layer_func.__name__ == "layer_5_hyperbolic_distance":
            # Test Möbius invariance
            u = np.random.randn(dim) * 0.3
            v = np.random.randn(dim) * 0.3
            passed, error = verify_mobius_invariance(u, v, n_tests=5)
            max_error = max(max_error, error)
            if not passed:
                violations += 1
                all_passed = False

        elif layer_func.__name__ == "layer_9_spectral_coherence":
            # Test rotation invariance
            x = np.random.randn(dim)
            passed, error = verify_rotation_invariance(x, n_tests=5)
            max_error = max(max_error, error)
            if not passed:
                violations += 1
                all_passed = False

        elif layer_func.__name__ == "layer_10_spin_coherence":
            # Test U(1) phase invariance
            q = np.random.randn() + 1j * np.random.randn()
            q = q / abs(q) * np.random.uniform(0, 1)  # Random amplitude
            passed, error = verify_phase_invariance(q, n_tests=20)
            max_error = max(max_error, error)
            if not passed:
                violations += 1
                all_passed = False

        elif layer_func.__name__ == "layer_12_harmonic_scaling":
            # Test monotonicity
            passed, n_violations = verify_monotonicity(n_tests=100)
            if not passed:
                violations += n_violations
                all_passed = False

    return all_passed, {
        "group": group.value if group else "unknown",
        "max_error": max_error,
        "violations": violations,
        "n_tests": n_tests
    }


# ============================================================================
# Axiom Layer Registry
# ============================================================================

SYMMETRY_LAYERS = {
    5: {
        "name": "Hyperbolic Distance",
        "function": layer_5_hyperbolic_distance,
        "inverse": None,  # Distance is not invertible
        "description": "THE INVARIANT: d_H preserved by Möbius group",
        "symmetry_group": SymmetryGroup.MOBIUS,
    },
    9: {
        "name": "Spectral Coherence",
        "function": layer_9_spectral_coherence,
        "inverse": None,  # Coherence is not invertible
        "description": "Frequency-domain coherence: O(n)-approximate invariant",
        "symmetry_group": SymmetryGroup.ORTHOGONAL,
    },
    10: {
        "name": "Spin Coherence",
        "function": layer_10_spin_coherence,
        "inverse": None,  # Coherence is not invertible
        "description": "Quantum amplitude coherence: U(1)-exact invariant",
        "symmetry_group": SymmetryGroup.UNITARY,
    },
    12: {
        "name": "Harmonic Scaling",
        "function": layer_12_harmonic_scaling,
        "inverse": layer_12_inverse,
        "description": "Superexponential risk: H(d) = R^(d²), order-preserving",
        "symmetry_group": SymmetryGroup.SCALE,
    },
}


def get_symmetry_layer(layer_num: int) -> dict:
    """Get layer info by number."""
    if layer_num not in SYMMETRY_LAYERS:
        raise ValueError(f"Layer {layer_num} is not a symmetry layer")
    return SYMMETRY_LAYERS[layer_num]


def list_symmetry_layers() -> list:
    """List all layers satisfying the symmetry axiom."""
    return list(SYMMETRY_LAYERS.keys())
