"""
Four-State Governance Symbol (FSGS) — Hybrid Dynamical System
==============================================================

@file fsgs.py
@module ai_brain/fsgs
@layer Layer 12, Layer 13
@component Hybrid automaton with 4-symbol control alphabet
@version 1.0.0

Defines a hybrid dynamical system (x, q) where:
  x ∈ R^21  = continuous brain state
  q ∈ {RUN, HOLD, QUAR, ROLLBACK} = discrete governance mode

The control alphabet Σ = {+1, -1, +0, -0} is encoded as two bits:
  σ = (m, s) ∈ {0,1}²
  m = magnitude bit (1 = active impulse, 0 = no impulse)
  s = sign bit (1 = positive posture, 0 = negative posture)

Update rule:
  x⁺ = Π_T( x + m · α(x) · η(s) · d(x) )
  q⁺ = δ(q, σ, x)

The key insight: ±0 doesn't move the continuous state, but the sign
bit can still force different governance behavior:
  +0: idle, continue in current mode
  -0: idle, but enter HOLD/QUAR and run re-anchoring/invariants

This avoids IEEE-754 signed-zero dependence while preserving the
"zero with attitude" semantics.

Integration:
- governance_adapter.py: GovernanceVerdict → FSGS symbol mapping
- mirror_shift.py: refactor_align provides the tube projection Π_T
- detection.py: anomaly scores feed the gain function α(x)
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .unified_state import (
    BRAIN_DIMENSIONS,
    UnifiedBrainState,
    safe_poincare_embed,
)
from .mirror_shift import refactor_align, AlignmentResult

EPS = 1e-12


# ---------------------------------------------------------------------------
# 4-symbol control alphabet
# ---------------------------------------------------------------------------

class GovernanceSymbol(enum.Enum):
    """Four-state governance symbol (m, s) ∈ {0,1}².

    Avoids IEEE-754 signed-zero dependence by encoding
    as an explicit (magnitude, sign) pair.
    """
    PLUS_ONE = (1, 1)    # +1: forward impulse → RUN
    MINUS_ONE = (1, 0)   # -1: reverse impulse → ROLLBACK
    PLUS_ZERO = (0, 1)   # +0: no impulse, continue
    MINUS_ZERO = (0, 0)  # -0: no impulse, hold/quarantine + re-anchor

    @property
    def magnitude(self) -> int:
        return self.value[0]

    @property
    def sign_bit(self) -> int:
        return self.value[1]

    @property
    def sign(self) -> float:
        """η(s): +1.0 if s=1, -1.0 if s=0."""
        return 1.0 if self.sign_bit == 1 else -1.0

    @property
    def has_impulse(self) -> bool:
        return self.magnitude == 1

    @property
    def is_positive(self) -> bool:
        return self.sign_bit == 1

    def __repr__(self) -> str:
        labels = {
            (1, 1): "+1", (1, 0): "-1",
            (0, 1): "+0", (0, 0): "-0",
        }
        return f"GovernanceSymbol({labels[self.value]})"


def symbol_from_bits(m: int, s: int) -> GovernanceSymbol:
    """Construct GovernanceSymbol from magnitude and sign bits."""
    return GovernanceSymbol((m, s))


# ---------------------------------------------------------------------------
# Governance modes (discrete automaton states)
# ---------------------------------------------------------------------------

class GovernanceMode(enum.Enum):
    """Discrete governance mode in the hybrid automaton.

    RUN:      Normal forward execution
    HOLD:     Paused, re-anchoring invariants (triggered by -0)
    QUAR:     Quarantined, restricted operations
    ROLLBACK: Reverse thrust / audit mode (triggered by -1)
    """
    RUN = "RUN"
    HOLD = "HOLD"
    QUAR = "QUAR"
    ROLLBACK = "ROLLBACK"


# ---------------------------------------------------------------------------
# Hybrid state
# ---------------------------------------------------------------------------

@dataclass
class HybridState:
    """Combined continuous + discrete state of the hybrid automaton.

    Attributes:
        x: Continuous 21D brain state vector.
        q: Discrete governance mode.
        step: Current timestep.
    """
    x: np.ndarray
    q: GovernanceMode = GovernanceMode.RUN
    step: int = 0

    def copy(self) -> HybridState:
        return HybridState(x=self.x.copy(), q=self.q, step=self.step)


# ---------------------------------------------------------------------------
# Mode transition function δ(q, σ, x)
# ---------------------------------------------------------------------------

def mode_transition(
    q: GovernanceMode,
    sigma: GovernanceSymbol,
    x: np.ndarray,
    risk_score: float = 0.0,
) -> GovernanceMode:
    """Compute next governance mode: q⁺ = δ(q, σ, x).

    Transition rules:
      +1 → RUN (forward, normal operation)
      -1 → ROLLBACK (reverse thrust / audit)
      +0 → stay in current mode (idle continue)
      -0 → HOLD or QUAR (idle but re-anchor)

    The -0 → HOLD vs QUAR distinction uses risk_score:
      risk < 0.5: HOLD (light pause)
      risk >= 0.5: QUAR (full quarantine)

    Args:
        q: Current governance mode.
        sigma: Governance symbol being applied.
        x: Current continuous state (for context-dependent transitions).
        risk_score: Risk score from governance adapter [0, 1].

    Returns:
        Next governance mode.
    """
    if sigma == GovernanceSymbol.PLUS_ONE:
        return GovernanceMode.RUN
    elif sigma == GovernanceSymbol.MINUS_ONE:
        return GovernanceMode.ROLLBACK
    elif sigma == GovernanceSymbol.PLUS_ZERO:
        # Stay in current mode (or default to RUN if unset)
        return q if q != GovernanceMode.ROLLBACK else GovernanceMode.RUN
    else:  # MINUS_ZERO
        return GovernanceMode.QUAR if risk_score >= 0.5 else GovernanceMode.HOLD


# ---------------------------------------------------------------------------
# Direction field d(x) and gain α(x)
# ---------------------------------------------------------------------------

def default_direction_field(
    x: np.ndarray,
    safe_origin: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Default direction field: unit vector toward safe origin.

    d(x) = (x_safe - x) / ||x_safe - x||

    Args:
        x: Current state.
        safe_origin: Safe origin vector.

    Returns:
        Unit direction vector (21D).
    """
    if safe_origin is None:
        safe_origin = np.array(UnifiedBrainState.safe_origin().to_vector())
    diff = safe_origin - x
    norm = np.linalg.norm(diff)
    if norm < EPS:
        return np.zeros_like(x)
    return diff / norm


def poincare_gain(
    x: np.ndarray,
    base_alpha: float = 0.1,
    risk_amplify: float = 1.0,
) -> float:
    """Gain function α(x) that scales with Poincaré distance from boundary.

    Closer to boundary → smaller steps (more caution).
    Uses the harmonic wall principle: cost increases near boundary.

    α(x) = base_alpha * (1 - ||embed(x)||) * risk_amplify

    Args:
        x: Current 21D state.
        base_alpha: Base step size.
        risk_amplify: Risk amplification factor.

    Returns:
        Step size α ≥ 0.
    """
    embedded = np.array(safe_poincare_embed(x.tolist()))
    poinc_radius = float(np.linalg.norm(embedded))
    boundary_margin = max(EPS, 1.0 - poinc_radius)
    return base_alpha * boundary_margin * risk_amplify


# ---------------------------------------------------------------------------
# Trust tube projection Π_T
# ---------------------------------------------------------------------------

def tube_project(
    x: np.ndarray,
    poincare_max: float = 0.95,
) -> Tuple[np.ndarray, AlignmentResult]:
    """Project state onto the trust tube via POCS constraint enforcement.

    Π_T(x) = refactor_align(x)

    The trust tube T ⊂ R^21 is the set of states satisfying:
    - Poincaré containment (||embed(x)|| < poincare_max)
    - SCBE trust bounds [0, 1]
    - Navigation/priority bounds
    - Tongue index integer constraint
    - Phase angle wrapping [0, 2π)
    - Flux/trust bounds

    Args:
        x: State to project.
        poincare_max: Maximum Poincaré radius.

    Returns:
        (projected_state, alignment_result).
    """
    result = refactor_align(x, poincare_max)
    return result.aligned_state, result


# ---------------------------------------------------------------------------
# Hybrid step: the core update rule
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StepResult:
    """Result of a single hybrid step."""
    state: HybridState
    symbol: GovernanceSymbol
    prev_mode: GovernanceMode
    impulse_magnitude: float
    alignment_corrections: int
    re_anchored: bool


def hybrid_step(
    state: HybridState,
    sigma: GovernanceSymbol,
    direction_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    base_alpha: float = 0.1,
    risk_score: float = 0.0,
    poincare_max: float = 0.95,
) -> StepResult:
    """Execute one step of the hybrid dynamical system.

    (x, q) → (x⁺, q⁺)

    Update rule:
      x' = x + m · α(x) · η(s) · d(x)     (tentative)
      x⁺ = Π_T(x')                          (project onto trust tube)
      q⁺ = δ(q, σ, x)                       (mode transition)

    Special case for -0:
      x doesn't move, but Π_T is still applied (re-anchoring)
      and mode transitions to HOLD/QUAR.

    Args:
        state: Current hybrid state (x, q).
        sigma: Governance symbol to apply.
        direction_fn: Direction field d(x). Default: toward safe origin.
        base_alpha: Base step size for gain function.
        risk_score: Risk score for mode transition context.
        poincare_max: Maximum Poincaré radius for tube projection.

    Returns:
        StepResult with new state and diagnostics.
    """
    x = state.x.copy()
    prev_mode = state.q

    # Direction field
    if direction_fn is None:
        d = default_direction_field(x)
    else:
        d = direction_fn(x)

    # Gain
    alpha = poincare_gain(x, base_alpha)

    # Tentative update: x' = x + m · α · η(s) · d(x)
    impulse = sigma.magnitude * alpha * sigma.sign
    x_prime = x + impulse * d

    # Tube projection: x⁺ = Π_T(x')
    x_plus, align_result = tube_project(x_prime, poincare_max)

    # Re-anchoring for -0: force projection even without movement
    re_anchored = False
    if sigma == GovernanceSymbol.MINUS_ZERO:
        # Re-project the ORIGINAL state (not the tentative, since m=0)
        x_plus, align_result = tube_project(x, poincare_max)
        re_anchored = True

    # Mode transition: q⁺ = δ(q, σ, x)
    q_plus = mode_transition(prev_mode, sigma, x, risk_score)

    new_state = HybridState(
        x=x_plus,
        q=q_plus,
        step=state.step + 1,
    )

    return StepResult(
        state=new_state,
        symbol=sigma,
        prev_mode=prev_mode,
        impulse_magnitude=abs(impulse),
        alignment_corrections=align_result.corrections_applied,
        re_anchored=re_anchored,
    )


# ---------------------------------------------------------------------------
# Verdict → symbol mapping
# ---------------------------------------------------------------------------

def verdict_to_symbol(decision: str, combined_score: float = 0.0) -> GovernanceSymbol:
    """Map L13 governance decision to FSGS symbol.

    ALLOW      → +1 (forward impulse, RUN)
    QUARANTINE → -0 (no impulse, re-anchor, HOLD/QUAR)
    ESCALATE   → -0 (no impulse, stronger re-anchor)
    DENY       → -1 (reverse impulse, ROLLBACK)

    Args:
        decision: L13 decision string.
        combined_score: Combined risk score for context.

    Returns:
        GovernanceSymbol.
    """
    mapping = {
        "ALLOW": GovernanceSymbol.PLUS_ONE,
        "QUARANTINE": GovernanceSymbol.MINUS_ZERO,
        "ESCALATE": GovernanceSymbol.MINUS_ZERO,
        "DENY": GovernanceSymbol.MINUS_ONE,
    }
    return mapping.get(decision, GovernanceSymbol.PLUS_ZERO)


# ---------------------------------------------------------------------------
# Control sequence analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ControlSequenceStats:
    """Statistics of a governance control sequence σ_t.

    Tracks mode dwell times, transition rates, and symbol
    distribution — the "spectral signature" of the control channel.
    """
    length: int
    symbol_counts: Dict[str, int]
    mode_dwell_times: Dict[str, List[int]]
    transition_count: int
    transition_rate: float
    hold_ratio: float
    rollback_ratio: float


def analyze_control_sequence(
    symbols: Sequence[GovernanceSymbol],
    modes: Optional[Sequence[GovernanceMode]] = None,
) -> ControlSequenceStats:
    """Analyze a sequence of governance symbols and modes.

    Computes:
    - Symbol distribution (how often each of the 4 symbols appears)
    - Mode dwell times (consecutive steps in each mode)
    - Transition rate (mode changes per step)
    - Hold/rollback ratios (fraction of time in defensive modes)

    Args:
        symbols: Sequence of GovernanceSymbols.
        modes: Optional sequence of modes (computed if not provided).

    Returns:
        ControlSequenceStats with all metrics.
    """
    n = len(symbols)
    if n == 0:
        return ControlSequenceStats(
            length=0,
            symbol_counts={"+1": 0, "-1": 0, "+0": 0, "-0": 0},
            mode_dwell_times={"RUN": [], "HOLD": [], "QUAR": [], "ROLLBACK": []},
            transition_count=0,
            transition_rate=0.0,
            hold_ratio=0.0,
            rollback_ratio=0.0,
        )

    # Symbol counts
    sym_labels = {
        GovernanceSymbol.PLUS_ONE: "+1",
        GovernanceSymbol.MINUS_ONE: "-1",
        GovernanceSymbol.PLUS_ZERO: "+0",
        GovernanceSymbol.MINUS_ZERO: "-0",
    }
    counts = {"+1": 0, "-1": 0, "+0": 0, "-0": 0}
    for s in symbols:
        counts[sym_labels[s]] += 1

    # Mode sequence (compute if not provided)
    if modes is None:
        mode_seq = []
        q = GovernanceMode.RUN
        for s in symbols:
            q = mode_transition(q, s, np.zeros(BRAIN_DIMENSIONS))
            mode_seq.append(q)
    else:
        mode_seq = list(modes)

    # Mode dwell times
    dwell_times: Dict[str, List[int]] = {
        "RUN": [], "HOLD": [], "QUAR": [], "ROLLBACK": [],
    }
    if mode_seq:
        current_mode = mode_seq[0]
        current_dwell = 1
        for i in range(1, len(mode_seq)):
            if mode_seq[i] == current_mode:
                current_dwell += 1
            else:
                dwell_times[current_mode.value].append(current_dwell)
                current_mode = mode_seq[i]
                current_dwell = 1
        dwell_times[current_mode.value].append(current_dwell)

    # Transition count
    transitions = sum(
        1 for i in range(1, len(mode_seq))
        if mode_seq[i] != mode_seq[i - 1]
    )

    # Mode ratios
    mode_counts = {m.value: 0 for m in GovernanceMode}
    for m in mode_seq:
        mode_counts[m.value] += 1

    total = max(len(mode_seq), 1)
    hold_ratio = (mode_counts["HOLD"] + mode_counts["QUAR"]) / total
    rollback_ratio = mode_counts["ROLLBACK"] / total

    return ControlSequenceStats(
        length=n,
        symbol_counts=counts,
        mode_dwell_times=dwell_times,
        transition_count=transitions,
        transition_rate=transitions / max(n - 1, 1),
        hold_ratio=hold_ratio,
        rollback_ratio=rollback_ratio,
    )


# ---------------------------------------------------------------------------
# Full trajectory simulation
# ---------------------------------------------------------------------------

@dataclass
class TrajectorySimulation:
    """Result of running FSGS over a full trajectory."""
    steps: List[StepResult]
    control_stats: ControlSequenceStats
    final_state: HybridState


def simulate_trajectory(
    initial_state: HybridState,
    symbols: Sequence[GovernanceSymbol],
    direction_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    base_alpha: float = 0.1,
    risk_scores: Optional[Sequence[float]] = None,
    poincare_max: float = 0.95,
) -> TrajectorySimulation:
    """Run the FSGS hybrid automaton over a sequence of governance symbols.

    Args:
        initial_state: Starting (x, q) state.
        symbols: Sequence of governance symbols to apply.
        direction_fn: Direction field d(x).
        base_alpha: Base step size.
        risk_scores: Per-step risk scores (default: all 0).
        poincare_max: Maximum Poincaré radius.

    Returns:
        TrajectorySimulation with all steps, control stats, and final state.
    """
    state = initial_state.copy()
    steps = []
    modes = []

    for i, sigma in enumerate(symbols):
        risk = risk_scores[i] if risk_scores else 0.0
        result = hybrid_step(
            state, sigma,
            direction_fn=direction_fn,
            base_alpha=base_alpha,
            risk_score=risk,
            poincare_max=poincare_max,
        )
        steps.append(result)
        modes.append(result.state.q)
        state = result.state

    control_stats = analyze_control_sequence(list(symbols), modes)

    return TrajectorySimulation(
        steps=steps,
        control_stats=control_stats,
        final_state=state,
    )
