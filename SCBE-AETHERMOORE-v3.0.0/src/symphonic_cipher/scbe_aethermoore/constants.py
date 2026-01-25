"""
AETHERMOORE Constants - Single Source of Truth
===============================================
Cross-domain constant registry for the AETHERMOORE framework.

All modules MUST import constants from this registry to ensure consistency.

Document ID: AETHER-SPEC-2026-001
Version: 1.0.0
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Any


# =============================================================================
# UNIVERSAL MATHEMATICAL CONSTANTS
# =============================================================================

PI = math.pi                          # 3.141592653589793
E = math.e                            # 2.718281828459045
PHI = (1 + math.sqrt(5)) / 2          # 1.618033988749895 (Golden Ratio)
SQRT2 = math.sqrt(2)                  # 1.4142135623730951
SQRT5 = math.sqrt(5)                  # 2.23606797749979


# =============================================================================
# HARMONIC RATIO CONSTANTS (Music Theory Derived)
# =============================================================================

R_FIFTH = 1.5                         # 3:2 - Perfect Fifth (Primary)
R_FOURTH = 4 / 3                      # 4:3 - Perfect Fourth
R_THIRD = 1.25                        # 5:4 - Major Third
R_SIXTH = 1.6                         # 8:5 - Minor Sixth
R_OCTAVE = 2.0                        # 2:1 - Octave
R_PHI = PHI                           # φ:1 - Golden Ratio


# =============================================================================
# AETHERMOORE CONSTANTS (Isaac Davis Discoveries)
# =============================================================================

# Aether Constant: φ^(1/R₅) = φ^(2/3)
PHI_AETHER = PHI ** (1 / R_FIFTH)     # 1.3782407725...

# Isaac Lambda: R₅ × φ²
LAMBDA_ISAAC = R_FIFTH * (PHI ** 2)   # 3.9270509831...

# Spiral Omega: 2π / φ³
OMEGA_SPIRAL = (2 * PI) / (PHI ** 3)  # 1.4832588477...

# ABH Alpha: φ + R₅
ALPHA_ABH = PHI + R_FIFTH             # 3.1180339887...


# =============================================================================
# PHYSICAL CONSTANTS (Reference)
# =============================================================================

C_LIGHT = 299792458                   # Speed of light (m/s)
PLANCK_LENGTH = 1.616255e-35          # Planck length (m)
PLANCK_TIME = 5.391247e-44            # Planck time (s)
PLANCK_CONSTANT = 6.62607015e-34      # Planck constant (J·s)


# =============================================================================
# DEFAULT PARAMETERS
# =============================================================================

DEFAULT_R = R_FIFTH                   # Default harmonic ratio
DEFAULT_D_MAX = 6                     # Maximum dimension count
DEFAULT_L = 100.0                     # Default characteristic length
DEFAULT_TOLERANCE = 0.01              # Default resonance tolerance
DEFAULT_BASE_BITS = 128               # Default security bits (AES-128)


# =============================================================================
# HARMONIC SCALING FUNCTION H(d, R)
# =============================================================================

def harmonic_scale(d: int, R: float = DEFAULT_R) -> float:
    """
    Compute the Harmonic Scaling value H(d, R) = R^(d²).

    This is the core AETHERMOORE formula providing super-exponential growth.

    Args:
        d: Dimension count (positive integer, typically 1-6)
        R: Harmonic ratio (positive real, default 1.5)

    Returns:
        The harmonic scaling multiplier

    Raises:
        ValueError: If d < 1 or R <= 0

    Examples:
        >>> harmonic_scale(6, 1.5)
        2184164.40625
        >>> harmonic_scale(3)
        38.443359375
    """
    if d < 1:
        raise ValueError(f"Dimension d must be >= 1, got {d}")
    if R <= 0:
        raise ValueError(f"Harmonic ratio R must be > 0, got {R}")

    return R ** (d * d)


def security_bits(base_bits: int, d: int, R: float = DEFAULT_R) -> float:
    """
    Compute effective security bits after harmonic scaling.

    S_bits(d, R, B_bits) = B_bits + d² × log₂(R)

    Args:
        base_bits: Base security level in bits (e.g., 128 for AES-128)
        d: Dimension count
        R: Harmonic ratio (default 1.5)

    Returns:
        Effective security bits

    Examples:
        >>> security_bits(128, 6, 1.5)
        149.058...  # AES-128 → ~AES-149 effective
    """
    return base_bits + (d * d) * math.log2(R)


def security_level(base: float, d: int, R: float = DEFAULT_R) -> float:
    """
    Compute full security level S = B × R^(d²).

    Args:
        base: Base security constant (e.g., 2^128)
        d: Dimension count
        R: Harmonic ratio (default 1.5)

    Returns:
        Enhanced security level
    """
    return base * harmonic_scale(d, R)


# =============================================================================
# HARMONIC DISTANCE IN V₆
# =============================================================================

def harmonic_distance(u: tuple, v: tuple, R: float = DEFAULT_R) -> float:
    """
    Compute harmonic distance in 6D harmonic vector space V₆.

    Uses the harmonic metric tensor:
        g_H = diag(1, 1, 1, R₅, R₅², R₅³)

    Args:
        u: First 6D vector (x, y, z, velocity, priority, security)
        v: Second 6D vector
        R: Harmonic ratio for metric weighting

    Returns:
        Harmonic distance between vectors
    """
    if len(u) != 6 or len(v) != 6:
        raise ValueError("Vectors must be 6-dimensional")

    # Metric weights: (1, 1, 1, R, R², R³)
    weights = [1, 1, 1, R, R**2, R**3]

    dist_sq = sum(w * (ui - vi)**2 for w, ui, vi in zip(weights, u, v))
    return math.sqrt(dist_sq)


def octave_transpose(freq: float, octaves: int) -> float:
    """
    Transpose frequency by n octaves.

    Args:
        freq: Original frequency
        octaves: Number of octaves to transpose (can be negative)

    Returns:
        Transposed frequency
    """
    return freq * (R_OCTAVE ** octaves)


# =============================================================================
# CONSOLIDATED CONSTANTS DICT
# =============================================================================

CONSTANTS: Dict[str, Any] = {
    # Mathematical
    'PI': PI,
    'E': E,
    'PHI': PHI,
    'SQRT2': SQRT2,
    'SQRT5': SQRT5,

    # Harmonic Ratios
    'R_FIFTH': R_FIFTH,
    'R_FOURTH': R_FOURTH,
    'R_THIRD': R_THIRD,
    'R_SIXTH': R_SIXTH,
    'R_OCTAVE': R_OCTAVE,
    'R_PHI': R_PHI,

    # AETHERMOORE
    'PHI_AETHER': PHI_AETHER,
    'LAMBDA_ISAAC': LAMBDA_ISAAC,
    'OMEGA_SPIRAL': OMEGA_SPIRAL,
    'ALPHA_ABH': ALPHA_ABH,

    # Physical
    'C_LIGHT': C_LIGHT,
    'PLANCK_LENGTH': PLANCK_LENGTH,
    'PLANCK_TIME': PLANCK_TIME,
    'PLANCK_CONSTANT': PLANCK_CONSTANT,

    # Defaults
    'DEFAULT_R': DEFAULT_R,
    'DEFAULT_D_MAX': DEFAULT_D_MAX,
    'DEFAULT_L': DEFAULT_L,
    'DEFAULT_TOLERANCE': DEFAULT_TOLERANCE,
    'DEFAULT_BASE_BITS': DEFAULT_BASE_BITS,
}


@dataclass(frozen=True)
class AethermooreDimension:
    """A dimension in the 6D harmonic vector space."""
    index: int          # 0-5
    name: str           # e.g., "x", "velocity", "security"
    unit: str           # e.g., "m", "m/s", "count"
    metric_weight: float  # Weight in harmonic metric


# Define the 6 dimensions
DIMENSIONS = (
    AethermooreDimension(0, "x", "m", 1.0),
    AethermooreDimension(1, "y", "m", 1.0),
    AethermooreDimension(2, "z", "m", 1.0),
    AethermooreDimension(3, "velocity", "m/s", R_FIFTH),
    AethermooreDimension(4, "priority", "scalar", R_FIFTH**2),
    AethermooreDimension(5, "security", "dimensions", R_FIFTH**3),
)


# =============================================================================
# REFERENCE TABLE
# =============================================================================

def get_harmonic_scale_table(max_d: int = 6, R: float = DEFAULT_R) -> list:
    """
    Generate reference table for H(d, R) values.

    Args:
        max_d: Maximum dimension to compute
        R: Harmonic ratio

    Returns:
        List of dicts with d, d², H(d,R), log₂(H), and AES equivalent
    """
    table = []
    for d in range(1, max_d + 1):
        h = harmonic_scale(d, R)
        log2_h = math.log2(h)
        aes_equiv = 128 + int(log2_h)

        table.append({
            'd': d,
            'd_squared': d * d,
            'H': h,
            'log2_H': log2_h,
            'aes_equivalent': f"AES-{aes_equiv}"
        })

    return table


# Precomputed table for R = 1.5
HARMONIC_SCALE_TABLE = get_harmonic_scale_table(6, R_FIFTH)
