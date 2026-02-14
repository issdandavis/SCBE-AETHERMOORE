"""
Mirror Shift + Refactor Align Adapter
======================================

@file mirror_shift.py
@module ai_brain/mirror_shift
@layer Layer 5, Layer 6, Layer 7, Layer 9
@component Dual-channel mirror analysis + constraint alignment for 21D brain state
@version 1.0.0

Implements:
1. Dual ternary quantization of 21D state deltas into parallel/perpendicular channels
2. Mirror shift operator (soft rotation between channels)
3. Refactor align (POCS-style projection onto constraint sets)
4. Mirror asymmetry score (detects one-channel compromise)
5. Complexity score via effective dimension of dual channel

The "dimensional analysis" approach from chemistry (tracking electrons/protons
through conversion factors) maps here: we track invariants (containment,
phase bounds, flux range, lattice consistency) through transformations and
catch violations when "the units don't cancel."

Integration points:
- Takes UnifiedBrainState or raw 21D vectors as input
- Produces dual ternary channels for Layer 14 spectral analysis
- Mirror asymmetry feeds Layer 13 risk decisions
- Refactor align enforces Layer 5 Poincaré containment + Layer 9 phase constraints
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .unified_state import (
    BRAIN_DIMENSIONS,
    BRAIN_EPSILON,
    POINCARE_MAX_NORM,
    UnifiedBrainState,
    safe_poincare_embed,
)

EPS = 1e-12

# ---------------------------------------------------------------------------
# 21D dimension layout
# ---------------------------------------------------------------------------

SCBE_DIMS = list(range(0, 6))       # SCBE Context
NAV_DIMS = list(range(6, 12))       # Dual Lattice Navigation
COG_DIMS = list(range(12, 15))      # PHDM Cognitive Position
SEM_DIMS = list(range(15, 18))      # Sacred Tongues Semantic Phase
SWARM_DIMS = list(range(18, 21))    # Swarm Coordination

# "Parallel" channel: structure/geometry (Navigation + Cognitive)
PARALLEL_DIMS = NAV_DIMS + COG_DIMS   # 9D
# "Perpendicular" channel: intent/governance (SCBE + Semantic + Swarm)
PERP_DIMS = SCBE_DIMS + SEM_DIMS + SWARM_DIMS  # 12D


# ---------------------------------------------------------------------------
# Ternary quantization
# ---------------------------------------------------------------------------

def quantize_ternary(
    z: np.ndarray, epsilon: float = 0.01
) -> np.ndarray:
    """
    Quantize continuous deltas to ternary {-1, 0, +1}.

    Q(z_i) = +1 if z_i > epsilon
             0  if |z_i| <= epsilon
            -1  if z_i < -epsilon

    Args:
        z: Continuous delta vector.
        epsilon: Dead zone threshold.

    Returns:
        Ternary vector of same shape.
    """
    result = np.zeros_like(z, dtype=np.int8)
    result[z > epsilon] = 1
    result[z < -epsilon] = -1
    return result


def compute_dual_ternary(
    x_curr: np.ndarray,
    x_prev: np.ndarray,
    epsilon: float = 0.01,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute dual ternary channels from consecutive 21D states.

    Parallel channel: quantized delta of structure/geometry dims
    Perpendicular channel: quantized delta of intent/governance dims

    Args:
        x_curr: Current 21D state vector.
        x_prev: Previous 21D state vector.
        epsilon: Quantization threshold.

    Returns:
        (parallel_ternary, perpendicular_ternary) — both int8 arrays.
    """
    x_curr = np.asarray(x_curr, dtype=float)
    x_prev = np.asarray(x_prev, dtype=float)
    delta = x_curr - x_prev

    parallel = quantize_ternary(delta[PARALLEL_DIMS], epsilon)
    perp = quantize_ternary(delta[PERP_DIMS], epsilon)
    return parallel, perp


def dual_ternary_trajectory(
    trajectory: np.ndarray,
    epsilon: float = 0.01,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute dual ternary channels for an entire trajectory.

    Args:
        trajectory: (T, 21) array of brain states.
        epsilon: Quantization threshold.

    Returns:
        (parallel_stream, perp_stream) — (T-1, 9) and (T-1, 12) int8 arrays.
    """
    trajectory = np.asarray(trajectory, dtype=float)
    if trajectory.ndim != 2 or trajectory.shape[1] < BRAIN_DIMENSIONS:
        raise ValueError(
            f"Expected (T, {BRAIN_DIMENSIONS}) trajectory, "
            f"got shape {trajectory.shape}."
        )

    T = len(trajectory)
    par_list = []
    perp_list = []
    for t in range(1, T):
        p, q = compute_dual_ternary(trajectory[t], trajectory[t - 1], epsilon)
        par_list.append(p)
        perp_list.append(q)
    return np.array(par_list, dtype=np.int8), np.array(perp_list, dtype=np.int8)


# ---------------------------------------------------------------------------
# Mirror shift operator
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MirrorShiftResult:
    """Result of applying the mirror shift operator."""
    shifted_parallel: np.ndarray
    shifted_perp: np.ndarray
    asymmetry_score: float
    mixing_angle: float


def mirror_shift(
    parallel: np.ndarray,
    perp: np.ndarray,
    phi: float = 0.0,
) -> MirrorShiftResult:
    """
    Apply soft mirror shift between parallel and perpendicular channels.

    The mixing operator rotates between channels:
        [a'] = [cos(phi)  sin(phi)] [a]
        [b']   [sin(phi)  cos(phi)] [b]

    At phi=0: identity (no mixing).
    At phi=pi/4: maximum mixing.
    At phi=pi/2: full swap (hard mirror).

    Args:
        parallel: Parallel channel vector (continuous or ternary).
        perp: Perpendicular channel vector.
        phi: Mixing angle in radians.

    Returns:
        MirrorShiftResult with shifted channels and asymmetry score.
    """
    parallel = np.asarray(parallel, dtype=float)
    perp = np.asarray(perp, dtype=float)

    # Pad shorter channel to match lengths for mixing
    max_len = max(len(parallel), len(perp))
    a = np.zeros(max_len)
    b = np.zeros(max_len)
    a[: len(parallel)] = parallel
    b[: len(perp)] = perp

    c = math.cos(phi)
    s = math.sin(phi)
    a_shifted = c * a + s * b
    b_shifted = s * a + c * b

    # Asymmetry: normalized difference in energy between channels
    e_a = float(np.sum(a_shifted**2))
    e_b = float(np.sum(b_shifted**2))
    total_e = e_a + e_b + EPS
    asymmetry = abs(e_a - e_b) / total_e

    return MirrorShiftResult(
        shifted_parallel=a_shifted[: len(parallel)],
        shifted_perp=b_shifted[: len(perp)],
        asymmetry_score=asymmetry,
        mixing_angle=phi,
    )


def mirror_asymmetry_score(
    parallel_stream: np.ndarray,
    perp_stream: np.ndarray,
) -> float:
    """
    Compute mirror asymmetry score for a trajectory's dual ternary streams.

    Measures the normalized energy imbalance between parallel and perpendicular
    channels across the entire stream. High asymmetry indicates one-side
    compromise.

    Args:
        parallel_stream: (T, D_par) ternary stream.
        perp_stream: (T, D_perp) ternary stream.

    Returns:
        Asymmetry score in [0, 1]. 0 = perfectly balanced, 1 = fully one-sided.
    """
    parallel_stream = np.asarray(parallel_stream, dtype=float)
    perp_stream = np.asarray(perp_stream, dtype=float)

    e_par = float(np.sum(parallel_stream**2))
    e_perp = float(np.sum(perp_stream**2))
    total = e_par + e_perp + EPS
    return abs(e_par - e_perp) / total


# ---------------------------------------------------------------------------
# Refactor align (POCS-style constraint projection)
# ---------------------------------------------------------------------------

# Constraint bounds for 21D brain state
# Format: (dimension_index, min_value, max_value)
CONSTRAINT_BOUNDS: List[Tuple[int, float, float]] = [
    # SCBE Context: all [0, 1]
    (0, 0.0, 1.0),   # device_trust
    (1, 0.0, 1.0),   # location_trust
    (2, 0.0, 1.0),   # network_trust
    (3, 0.0, 1.0),   # behavior_score
    (4, 0.0, 1.0),   # time_of_day
    (5, 0.0, 1.0),   # intent_alignment
    # Navigation: x, y, z unconstrained; time >= 0; priority, confidence [0, 1]
    (10, 0.0, 1.0),  # priority
    (11, 0.0, 1.0),  # confidence
    # Semantic Phase
    (15, 0.0, 5.0),  # active_tongue index [0..5]
    (16, 0.0, 2.0 * math.pi),  # phase_angle [0, 2pi)
    (17, 0.0, 20.0),  # tongue_weight (positive)
    # Swarm Coordination
    (18, 0.0, 1.0),  # trust_score
    (19, 0.0, 100.0),  # byzantine_votes (non-negative)
    (20, 0.0, 1.0),  # spectral_coherence
]


def _clamp_bounds(x: np.ndarray) -> np.ndarray:
    """Clamp 21D vector to constraint bounds."""
    x = x.copy()
    for dim, lo, hi in CONSTRAINT_BOUNDS:
        if dim < len(x):
            x[dim] = np.clip(x[dim], lo, hi)
    return x


def _snap_tongue_index(x: np.ndarray) -> np.ndarray:
    """Snap active_tongue (dim 15) to nearest integer in [0, 5]."""
    x = x.copy()
    if len(x) > 15:
        x[15] = float(int(np.clip(np.round(x[15]), 0, 5)))
    return x


def _wrap_phase(x: np.ndarray) -> np.ndarray:
    """Wrap phase_angle (dim 16) to [0, 2*pi)."""
    x = x.copy()
    if len(x) > 16:
        x[16] = x[16] % (2 * math.pi)
    return x


def _clamp_flux(x: np.ndarray) -> np.ndarray:
    """Clamp flux/trust dimensions to valid range."""
    x = x.copy()
    # Already handled by bounds, but explicit for clarity
    for dim in [18, 20]:  # trust_score, spectral_coherence
        if dim < len(x):
            x[dim] = np.clip(x[dim], 0.0, 1.0)
    return x


def _poincare_containment(x: np.ndarray, max_norm: float = 0.95) -> np.ndarray:
    """
    Project the Poincaré-embedded version back if needed.

    This doesn't modify the raw state directly but checks that
    the embedded point is inside the ball.

    Args:
        x: Raw 21D state vector.
        max_norm: Maximum allowed Poincaré radius.

    Returns:
        State vector (potentially scaled) that embeds inside the ball.
    """
    embedded = np.array(safe_poincare_embed(x.tolist()))
    norm = float(np.linalg.norm(embedded))
    if norm >= max_norm:
        # Scale down the raw state to reduce Poincaré radius
        # Since embed uses tanh(||x||/2), we need to reduce ||x||
        target_norm = max_norm * 0.95
        # tanh(||x||/2) = target_norm -> ||x|| = 2*atanh(target_norm)
        if target_norm < 1.0:
            target_raw_norm = 2 * math.atanh(target_norm)
            raw_norm = float(np.linalg.norm(x))
            if raw_norm > EPS:
                x = x * (target_raw_norm / raw_norm)
    return x


@dataclass(frozen=True)
class AlignmentResult:
    """Result of refactor alignment."""
    aligned_state: np.ndarray
    corrections_applied: int
    max_correction: float
    poincare_radius: float


def refactor_align(
    x: np.ndarray,
    poincare_max: float = 0.95,
) -> AlignmentResult:
    """
    POCS-style constraint projection for 21D brain state.

    Applies sequential projections onto constraint sets:
    1. Ensure Poincaré containment (global scaling if needed)
    2. Clamp bounds (SCBE trust scores, navigation bounds, etc.)
    3. Clamp flux/trust to [0, 1]
    4. Snap tongue index to nearest integer
    5. Wrap phase angle to [0, 2*pi)

    This is the "charge conservation" enforcement — every invariant
    must hold after transformation, just like electrons/protons must
    balance across a reaction.

    Args:
        x: Raw 21D state vector.
        poincare_max: Maximum Poincaré ball radius.

    Returns:
        AlignmentResult with corrected state and diagnostics.
    """
    x = np.asarray(x, dtype=float).copy()
    if len(x) != BRAIN_DIMENSIONS:
        raise ValueError(
            f"Expected {BRAIN_DIMENSIONS}D vector, got {len(x)}D."
        )

    original = x.copy()
    corrections = 0
    max_corr = 0.0

    # Step 1: Poincaré containment (global scaling — must come first
    # so discrete constraints applied later aren't broken by rescaling)
    x_poinc = _poincare_containment(x, poincare_max)
    diff = np.abs(x_poinc - x)
    if float(diff.max()) > EPS:
        corrections += 1
        max_corr = max(max_corr, float(diff.max()))
    x = x_poinc

    # Step 2: Clamp bounds
    x_clamped = _clamp_bounds(x)
    diff = np.abs(x_clamped - x)
    changed = diff > EPS
    corrections += int(changed.sum())
    max_corr = max(max_corr, float(diff.max()))
    x = x_clamped

    # Step 3: Clamp flux
    x_flux = _clamp_flux(x)
    diff = np.abs(x_flux - x)
    changed = diff > EPS
    corrections += int(changed.sum())
    max_corr = max(max_corr, float(diff.max()))
    x = x_flux

    # Step 4: Snap tongue index (after Poincaré so integer isn't broken)
    x_snapped = _snap_tongue_index(x)
    d = abs(x_snapped[15] - x[15]) if len(x) > 15 else 0
    if d > EPS:
        corrections += 1
        max_corr = max(max_corr, d)
    x = x_snapped

    # Step 5: Wrap phase
    x_wrapped = _wrap_phase(x)
    d = abs(x_wrapped[16] - x[16]) if len(x) > 16 else 0
    if d > EPS:
        corrections += 1
        max_corr = max(max_corr, d)
    x = x_wrapped

    # Compute final Poincaré radius
    embedded = np.array(safe_poincare_embed(x.tolist()))
    poinc_r = float(np.linalg.norm(embedded))

    return AlignmentResult(
        aligned_state=x,
        corrections_applied=corrections,
        max_correction=max_corr,
        poincare_radius=poinc_r,
    )


# ---------------------------------------------------------------------------
# Combined adapter: state -> dual ternary + scores
# ---------------------------------------------------------------------------

@dataclass
class MirrorAnalysis:
    """Complete mirror shift analysis of a state transition."""
    parallel_ternary: np.ndarray
    perp_ternary: np.ndarray
    asymmetry_score: float
    complexity_score: float
    aligned_state: np.ndarray
    corrections: int


def analyze_transition(
    x_curr: np.ndarray,
    x_prev: np.ndarray,
    epsilon: float = 0.01,
    align: bool = True,
) -> MirrorAnalysis:
    """
    Full mirror shift analysis of a single state transition.

    1. Align current state (if requested)
    2. Compute dual ternary channels
    3. Compute mirror asymmetry
    4. Estimate complexity from ternary channels

    Args:
        x_curr: Current 21D state.
        x_prev: Previous 21D state.
        epsilon: Ternary quantization threshold.
        align: Whether to refactor-align the current state first.

    Returns:
        MirrorAnalysis with channels, scores, and aligned state.
    """
    x_curr = np.asarray(x_curr, dtype=float)
    x_prev = np.asarray(x_prev, dtype=float)

    # Optionally align
    corrections = 0
    if align:
        result = refactor_align(x_curr)
        x_curr = result.aligned_state
        corrections = result.corrections_applied

    # Dual ternary
    par, perp = compute_dual_ternary(x_curr, x_prev, epsilon)

    # Asymmetry
    asym = mirror_asymmetry_score(
        par.reshape(1, -1), perp.reshape(1, -1)
    )

    # Complexity: ratio of nonzero entries to total
    total_entries = len(par) + len(perp)
    nonzero = int(np.count_nonzero(par)) + int(np.count_nonzero(perp))
    complexity = nonzero / max(total_entries, 1)

    return MirrorAnalysis(
        parallel_ternary=par,
        perp_ternary=perp,
        asymmetry_score=asym,
        complexity_score=complexity,
        aligned_state=x_curr,
        corrections=corrections,
    )
