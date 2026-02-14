"""
PQ Cymatic Governance Adapter
==============================

@file governance_adapter.py
@module ai_brain/governance_adapter
@layer Layer 12, Layer 13
@component Mirror-asymmetry governance with 6-state dual propagation
@version 1.0.0

Implements:
1. 6-state micro-state alphabet (chemistry-inspired dual ternary)
2. Persistent asymmetry detection (sliding window)
3. Flux contraction (pull state toward safe origin when asymmetry persists)
4. L13 risk decisions: ALLOW / QUARANTINE / ESCALATE / DENY

The chemistry analogy (from periodic table dimensional analysis):
- Proton / Neutron / Electron  =  3 ternary states per channel
- Matter / Anti-matter          =  Parallel / Perpendicular channels
- 6 "particle types"            =  the complete micro-state vocabulary
- Charge conservation            =  sum constraints on micro-states
- Valence rules                  =  allowed combination patterns
- Neutral atom                   =  balanced dual-channel state (safe)
- Ionized atom                   =  asymmetric channels (suspicious)
- Persistent ionization          =  energy being pumped in (attack)

Just as in chemistry you can build complex structures from 3 particle
types with compositional rules, here 6 micro-states with charge-balance
constraints yield the full governance vocabulary.

Integration:
- Consumes: mirror_shift analysis, multiscale_spectrum anomaly scores
- Produces: GovernanceVerdict with risk decision + updated state
- Feeds: Layer 13 risk pipeline, Layer 14 audio telemetry
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .unified_state import (
    BRAIN_DIMENSIONS,
    UnifiedBrainState,
    safe_poincare_embed,
)
from .mirror_shift import (
    PARALLEL_DIMS,
    PERP_DIMS,
    compute_dual_ternary,
    mirror_asymmetry_score,
    refactor_align,
    AlignmentResult,
)
from .multiscale_spectrum import (
    analyze_trajectory,
    MultiscaleReport,
)

EPS = 1e-12


# ---------------------------------------------------------------------------
# 6-state micro-state alphabet
# ---------------------------------------------------------------------------

class MicroStateType(enum.Enum):
    """Six particle types for dual-channel governance.

    Chemistry mapping:
        PAR_ACTIVATE  = "proton"       — positive structural change
        PAR_NEUTRAL   = "neutron"      — structural hold
        PAR_INHIBIT   = "electron"     — negative structural change
        PERP_ACTIVATE = "anti-proton"  — positive governance change
        PERP_NEUTRAL  = "anti-neutron" — governance hold
        PERP_INHIBIT  = "anti-electron"— negative governance change
    """
    PAR_ACTIVATE = "par+"
    PAR_NEUTRAL = "par0"
    PAR_INHIBIT = "par-"
    PERP_ACTIVATE = "perp+"
    PERP_NEUTRAL = "perp0"
    PERP_INHIBIT = "perp-"


@dataclass(frozen=True)
class MicroStateCensus:
    """Count of each micro-state type in a transition.

    Like an element's composition (protons, neutrons, electrons),
    this describes the "atomic number" of a state transition.
    """
    par_activate: int = 0
    par_neutral: int = 0
    par_inhibit: int = 0
    perp_activate: int = 0
    perp_neutral: int = 0
    perp_inhibit: int = 0

    @property
    def parallel_charge(self) -> int:
        """Net parallel charge: activations - inhibitions."""
        return self.par_activate - self.par_inhibit

    @property
    def perp_charge(self) -> int:
        """Net perpendicular charge."""
        return self.perp_activate - self.perp_inhibit

    @property
    def total_charge(self) -> int:
        """Total net charge across both channels."""
        return self.parallel_charge + self.perp_charge

    @property
    def is_neutral(self) -> bool:
        """True if total charge is zero (balanced like a neutral atom)."""
        return self.total_charge == 0

    @property
    def active_count(self) -> int:
        """Total non-neutral micro-states (like counting charged particles)."""
        return (self.par_activate + self.par_inhibit
                + self.perp_activate + self.perp_inhibit)

    @property
    def charge_imbalance(self) -> float:
        """Normalized charge imbalance between channels.

        0.0 = perfectly balanced (neutral atom)
        1.0 = fully one-sided (completely ionized)
        """
        denom = max(self.active_count, 1)
        return abs(self.parallel_charge - self.perp_charge) / denom

    @property
    def ionization_level(self) -> float:
        """How "ionized" the transition is (total |charge| / active particles).

        0.0 = all charges cancel (noble gas)
        1.0 = all charges same sign (plasma)
        """
        denom = max(self.active_count, 1)
        return abs(self.total_charge) / denom

    def to_dict(self) -> Dict[str, int]:
        """Serialize to dict."""
        return {
            "par+": self.par_activate,
            "par0": self.par_neutral,
            "par-": self.par_inhibit,
            "perp+": self.perp_activate,
            "perp0": self.perp_neutral,
            "perp-": self.perp_inhibit,
        }


def census_from_ternary(
    parallel: np.ndarray, perp: np.ndarray
) -> MicroStateCensus:
    """Build a MicroStateCensus from ternary channel vectors.

    Args:
        parallel: Ternary vector for parallel channel (int8).
        perp: Ternary vector for perpendicular channel (int8).

    Returns:
        MicroStateCensus with counts of each particle type.
    """
    parallel = np.asarray(parallel, dtype=int)
    perp = np.asarray(perp, dtype=int)

    return MicroStateCensus(
        par_activate=int(np.sum(parallel == 1)),
        par_neutral=int(np.sum(parallel == 0)),
        par_inhibit=int(np.sum(parallel == -1)),
        perp_activate=int(np.sum(perp == 1)),
        perp_neutral=int(np.sum(perp == 0)),
        perp_inhibit=int(np.sum(perp == -1)),
    )


# ---------------------------------------------------------------------------
# Valence rules (allowed combination patterns)
# ---------------------------------------------------------------------------

def check_valence(census: MicroStateCensus) -> Tuple[bool, List[str]]:
    """Check if a micro-state census satisfies valence rules.

    Like chemistry's octet rule: certain configurations are stable,
    others indicate an unstable / dangerous state.

    Rules:
    1. Charge neutrality: |total_charge| should be small
    2. Channel balance: parallel and perpendicular charges shouldn't diverge
    3. Activity bound: too many active particles = chaotic probing
    4. Minimum activity: zero activity on both channels = replay/static

    Args:
        census: The micro-state census to check.

    Returns:
        (is_valid, list_of_violations).
    """
    violations = []

    # Rule 1: Charge neutrality (like net charge = 0 for stable atom)
    if abs(census.total_charge) > max(census.active_count // 2, 2):
        violations.append("charge_excess")

    # Rule 2: Channel balance (like electron/proton balance)
    if census.charge_imbalance > 0.8:
        violations.append("channel_imbalance")

    # Rule 3: Too many active particles = unstable / chaotic
    total_dims = len(PARALLEL_DIMS) + len(PERP_DIMS)
    if census.active_count > int(total_dims * 0.85):
        violations.append("overactive")

    # Rule 4: Zero activity = replay / static attack
    if census.active_count == 0:
        violations.append("static")

    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Asymmetry persistence tracker
# ---------------------------------------------------------------------------

class AsymmetryTracker:
    """Tracks mirror asymmetry over a sliding window.

    Chemistry analogy: like tracking ionization state over time.
    A briefly ionized atom may recombine (normal fluctuation).
    A persistently ionized one means energy is being pumped in (attack).

    Args:
        window_size: Number of readings to track.
        threshold: Asymmetry level that counts as "ionized".
    """

    def __init__(self, window_size: int = 8, threshold: float = 0.3):
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.threshold = threshold
        self._history: List[float] = []

    def record(self, asymmetry: float) -> None:
        """Record a new asymmetry measurement."""
        self._history.append(asymmetry)
        if len(self._history) > self.window_size:
            self._history = self._history[-self.window_size:]

    @property
    def persistence_count(self) -> int:
        """How many consecutive recent readings exceeded the threshold."""
        count = 0
        for a in reversed(self._history):
            if a >= self.threshold:
                count += 1
            else:
                break
        return count

    @property
    def persistence_ratio(self) -> float:
        """Fraction of window above threshold."""
        if not self._history:
            return 0.0
        above = sum(1 for a in self._history if a >= self.threshold)
        return above / len(self._history)

    @property
    def should_contract(self) -> bool:
        """True if asymmetry has persisted long enough to trigger flux contraction.

        Requires 3+ consecutive readings above threshold.
        """
        return self.persistence_count >= 3

    @property
    def average_asymmetry(self) -> float:
        """Average asymmetry over the window."""
        if not self._history:
            return 0.0
        return sum(self._history) / len(self._history)

    def reset(self) -> None:
        """Clear the history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Flux contraction
# ---------------------------------------------------------------------------

def flux_contract(
    x: np.ndarray,
    contraction_strength: float = 0.3,
    safe_origin: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Contract a 21D state toward the safe origin.

    When mirror-asymmetry persists, this "pulls" the state back
    toward safety — like a restoring force on an ionized atom.

    The contraction interpolates: x' = (1 - alpha) * x + alpha * x_safe
    where alpha = contraction_strength.

    Args:
        x: Current 21D state vector.
        contraction_strength: How strongly to pull toward origin (0=none, 1=snap).
        safe_origin: Safe origin vector (default: UnifiedBrainState.safe_origin()).

    Returns:
        Contracted 21D state vector.
    """
    x = np.asarray(x, dtype=float)
    if safe_origin is None:
        safe_origin = np.array(UnifiedBrainState.safe_origin().to_vector())
    else:
        safe_origin = np.asarray(safe_origin, dtype=float)

    alpha = max(0.0, min(1.0, contraction_strength))
    return (1.0 - alpha) * x + alpha * safe_origin


# ---------------------------------------------------------------------------
# Governance verdict
# ---------------------------------------------------------------------------

@dataclass
class GovernanceVerdict:
    """L13 risk decision from combined mirror + fractal + charge analysis.

    This is the output of the governance adapter — a complete diagnostic
    that feeds Layer 13 risk decisions and Layer 14 audio telemetry.
    """
    decision: str                        # ALLOW, QUARANTINE, ESCALATE, DENY
    mirror_asymmetry: float              # [0, 1] channel energy imbalance
    fractal_anomaly: float               # [0, 1] multiscale anomaly score
    charge_imbalance: float              # [0, 1] 6-state charge imbalance
    combined_score: float                # [0, 1] weighted combination
    micro_census: MicroStateCensus       # 6-state particle counts
    valence_valid: bool                  # whether valence rules pass
    valence_violations: List[str]        # which rules were broken
    flux_contracted: bool                # whether contraction was applied
    contraction_factor: float            # how much contraction (0 = none)
    updated_state: Optional[np.ndarray]  # state after alignment + contraction
    persistence_count: int               # consecutive high-asymmetry readings
    alignment_corrections: int           # POCS corrections applied


def evaluate_governance(
    x_curr: np.ndarray,
    x_prev: Optional[np.ndarray] = None,
    trajectory: Optional[np.ndarray] = None,
    tracker: Optional[AsymmetryTracker] = None,
    epsilon: float = 0.01,
    quarantine_threshold: float = 0.3,
    escalate_threshold: float = 0.6,
    deny_threshold: float = 0.85,
    contraction_strength: float = 0.3,
    align: bool = True,
) -> GovernanceVerdict:
    """Full L13 governance evaluation combining mirror shift + fractal analysis.

    Pipeline:
    1. Refactor-align current state (POCS constraint enforcement)
    2. Compute dual ternary channels (if previous state available)
    3. Build 6-state micro-census + check valence rules
    4. Compute mirror asymmetry score
    5. Run multiscale fractal analysis (if trajectory available)
    6. Track asymmetry persistence
    7. Apply flux contraction if asymmetry persists
    8. Make L13 risk decision

    Args:
        x_curr: Current 21D brain state vector.
        x_prev: Previous 21D state (None = first observation).
        trajectory: Historical trajectory (T, 21) for fractal analysis.
        tracker: AsymmetryTracker for persistence detection.
        epsilon: Ternary quantization threshold.
        quarantine_threshold: Combined score for QUARANTINE.
        escalate_threshold: Combined score for ESCALATE.
        deny_threshold: Combined score for DENY.
        contraction_strength: How strongly to contract on persistent asymmetry.
        align: Whether to apply refactor-align.

    Returns:
        GovernanceVerdict with risk decision and full diagnostics.
    """
    x_curr = np.asarray(x_curr, dtype=float).copy()

    if len(x_curr) != BRAIN_DIMENSIONS:
        raise ValueError(
            f"Expected {BRAIN_DIMENSIONS}D vector, got {len(x_curr)}D."
        )

    # Step 1: Refactor-align
    alignment_corrections = 0
    if align:
        ar = refactor_align(x_curr)
        x_curr = ar.aligned_state
        alignment_corrections = ar.corrections_applied

    # Step 2: Dual ternary channels
    if x_prev is not None:
        x_prev = np.asarray(x_prev, dtype=float)
        par, perp = compute_dual_ternary(x_curr, x_prev, epsilon)
    else:
        # No previous state — treat as all-neutral (first observation)
        par = np.zeros(len(PARALLEL_DIMS), dtype=np.int8)
        perp = np.zeros(len(PERP_DIMS), dtype=np.int8)

    # Step 3: 6-state micro-census
    census = census_from_ternary(par, perp)
    valence_ok, valence_violations = check_valence(census)

    # Step 4: Mirror asymmetry
    mirror_asym = mirror_asymmetry_score(
        par.reshape(1, -1), perp.reshape(1, -1)
    )

    # Step 5: Fractal anomaly (multiscale spectrum)
    fractal_anomaly = 0.0
    if trajectory is not None:
        trajectory = np.asarray(trajectory, dtype=float)
        if trajectory.ndim == 2 and len(trajectory) > 4:
            scales = tuple(s for s in (1, 2, 4, 8) if len(trajectory) > s + 2)
            if scales:
                report = analyze_trajectory(trajectory, scales)
                fractal_anomaly = report.anomaly_score

    # Step 6: Track asymmetry persistence
    persistence_count = 0
    if tracker is not None:
        tracker.record(mirror_asym)
        persistence_count = tracker.persistence_count

    # Step 7: Flux contraction
    contracted = False
    actual_contraction = 0.0
    if tracker is not None and tracker.should_contract:
        # Scale contraction by persistence ratio
        actual_contraction = contraction_strength * tracker.persistence_ratio
        x_curr = flux_contract(x_curr, actual_contraction)
        contracted = True
        # Re-align after contraction
        if align:
            ar2 = refactor_align(x_curr)
            x_curr = ar2.aligned_state
            alignment_corrections += ar2.corrections_applied

    # Step 8: Combined scoring + risk decision
    charge_imb = census.charge_imbalance

    # Weighted combination:
    #   40% mirror asymmetry (direct channel imbalance)
    #   30% fractal anomaly (multiscale spectrum deviation)
    #   20% charge imbalance (6-state valence violation)
    #   10% valence penalty (binary: rules broken or not)
    valence_penalty = 0.0 if valence_ok else min(1.0, len(valence_violations) * 0.3)

    combined = (
        0.40 * mirror_asym
        + 0.30 * fractal_anomaly
        + 0.20 * charge_imb
        + 0.10 * valence_penalty
    )
    combined = max(0.0, min(1.0, combined))

    # Persistence amplification: if asymmetry has persisted, boost score
    if persistence_count >= 3:
        persistence_boost = min(0.15, persistence_count * 0.03)
        combined = min(1.0, combined + persistence_boost)

    # Risk decision
    if combined >= deny_threshold:
        decision = "DENY"
    elif combined >= escalate_threshold:
        decision = "ESCALATE"
    elif combined >= quarantine_threshold:
        decision = "QUARANTINE"
    else:
        decision = "ALLOW"

    return GovernanceVerdict(
        decision=decision,
        mirror_asymmetry=mirror_asym,
        fractal_anomaly=fractal_anomaly,
        charge_imbalance=charge_imb,
        combined_score=combined,
        micro_census=census,
        valence_valid=valence_ok,
        valence_violations=valence_violations,
        flux_contracted=contracted,
        contraction_factor=actual_contraction,
        updated_state=x_curr,
        persistence_count=persistence_count,
        alignment_corrections=alignment_corrections,
    )


# ---------------------------------------------------------------------------
# Trajectory governance: evaluate a full trajectory
# ---------------------------------------------------------------------------

def evaluate_trajectory_governance(
    trajectory: np.ndarray,
    tracker: Optional[AsymmetryTracker] = None,
    epsilon: float = 0.01,
    quarantine_threshold: float = 0.3,
    escalate_threshold: float = 0.6,
    deny_threshold: float = 0.85,
    contraction_strength: float = 0.3,
) -> List[GovernanceVerdict]:
    """Evaluate governance decisions across a full trajectory.

    Processes each state transition sequentially, tracking asymmetry
    persistence and applying flux contraction when needed.

    Args:
        trajectory: (T, 21) array of brain states.
        tracker: AsymmetryTracker (created internally if None).
        epsilon: Ternary quantization threshold.
        quarantine_threshold: Combined score for QUARANTINE.
        escalate_threshold: Combined score for ESCALATE.
        deny_threshold: Combined score for DENY.
        contraction_strength: Flux contraction strength.

    Returns:
        List of GovernanceVerdicts, one per timestep.
    """
    trajectory = np.asarray(trajectory, dtype=float)
    if trajectory.ndim != 2 or trajectory.shape[1] != BRAIN_DIMENSIONS:
        raise ValueError(
            f"Expected (T, {BRAIN_DIMENSIONS}) trajectory, "
            f"got shape {trajectory.shape}."
        )

    if tracker is None:
        tracker = AsymmetryTracker()

    verdicts = []
    for t in range(len(trajectory)):
        x_curr = trajectory[t]
        x_prev = trajectory[t - 1] if t > 0 else None
        # Use trajectory up to current point for fractal analysis
        traj_window = trajectory[:t + 1] if t >= 4 else None

        verdict = evaluate_governance(
            x_curr=x_curr,
            x_prev=x_prev,
            trajectory=traj_window,
            tracker=tracker,
            epsilon=epsilon,
            quarantine_threshold=quarantine_threshold,
            escalate_threshold=escalate_threshold,
            deny_threshold=deny_threshold,
            contraction_strength=contraction_strength,
        )
        verdicts.append(verdict)

    return verdicts
