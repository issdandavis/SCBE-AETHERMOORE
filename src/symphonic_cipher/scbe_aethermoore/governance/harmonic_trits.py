"""
Harmonic Ternary Decomposition — The Three-Trit Decision Surface
================================================================

@file harmonic_trits.py
@module governance/harmonic_trits
@layer Layer 12, Layer 13
@component Ternary Detection Surface

The three H formulas produce a ternary decomposition that maps to the
Hamiltonian Braid's {-1, 0, +1} phase space. Each formula contributes
one trit:

    t_score : from H_score (bounded safety)
    t_wall  : from H_wall  (bounded risk multiplier)
    t_exp   : from H_exp   (unbounded cost)

Normal operation: all three agree (correlated via d*).
Disagreement = sophisticated attack detection:
    - Phase deviation pd affects ONLY H_score (not H_wall or H_exp)
    - Low d* + high pd → H_score drops, H_wall/H_exp stay safe
    - Result: (-1, +1, +1) = "geometrically close but phase-incoherent"
    - This IS the detection signal for subtle attackers

Integration with hamiltonian_braid.py:
    - braid 9-state: (parallel_trit, perp_trit) in {-1,0,+1}²
    - H-formula ternary adds a third dimension
    - Combined: (par_trit, perp_trit, h_trit) = 27-state joint space
    - h_trit = consensus of (t_score, t_wall, t_exp)

Canonical reference: docs/L12_HARMONIC_SCALING_CANON.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .harmonic_scaling import H_score, H_wall, H_exp, PHI


# ---------------------------------------------------------------------------
# Trit thresholds — THESE ARE THE CANONICAL GATE VALUES
# ---------------------------------------------------------------------------

# H_score: high = safe, low = adversarial
_SCORE_SAFE: float = 0.67     # > 0.67 → +1 (safe)
_SCORE_HOSTILE: float = 0.33  # < 0.33 → -1 (hostile)
# Between 0.33 and 0.67 → 0 (transition)

# H_wall: low = safe (near origin), high = adversarial (saturated)
_WALL_SAFE: float = 1.5       # < 1.5 → +1 (safe)
_WALL_HOSTILE: float = 1.9    # > 1.9 → -1 (hostile)
# Between 1.5 and 1.9 → 0 (transition)

# H_exp: low = safe (near 1), high = adversarial (exploding)
_EXP_SAFE: float = 2.0        # < 2.0 → +1 (safe)
_EXP_HOSTILE: float = 10.0    # > 10.0 → -1 (hostile)
# Between 2.0 and 10.0 → 0 (transition)


# ---------------------------------------------------------------------------
# TritVector dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TritVector:
    """Three-trit decision vector from harmonic decomposition.

    Each trit is in {-1, 0, +1}:
        +1 = safe region
         0 = transition zone
        -1 = hostile region
    """
    t_score: int   # from H_score
    t_wall: int    # from H_wall
    t_exp: int     # from H_exp

    # Raw values for diagnostics
    h_score: float = 0.0
    h_wall: float = 0.0
    h_exp: float = 0.0

    @property
    def as_tuple(self) -> Tuple[int, int, int]:
        return (self.t_score, self.t_wall, self.t_exp)

    @property
    def sum(self) -> int:
        """Trit sum: +3 = fully safe, -3 = fully hostile."""
        return self.t_score + self.t_wall + self.t_exp

    @property
    def unanimous(self) -> bool:
        """True if all three trits agree."""
        return self.t_score == self.t_wall == self.t_exp

    @property
    def phase_incoherent(self) -> bool:
        """True if H_score disagrees with both H_wall and H_exp.

        This is the signature of a subtle attacker: geometrically close
        to safe behavior (low d*) but phase-chaotic (high pd).
        """
        return (
            self.t_score <= 0
            and self.t_wall == 1
            and self.t_exp == 1
        )

    @property
    def any_hostile(self) -> bool:
        return self.t_score == -1 or self.t_wall == -1 or self.t_exp == -1

    @property
    def any_transition(self) -> bool:
        return self.t_score == 0 or self.t_wall == 0 or self.t_exp == 0

    @property
    def all_safe(self) -> bool:
        return self.t_score == 1 and self.t_wall == 1 and self.t_exp == 1


# ---------------------------------------------------------------------------
# Trit classification functions
# ---------------------------------------------------------------------------

def _classify_score(value: float) -> int:
    """Classify H_score into trit."""
    if value > _SCORE_SAFE:
        return 1
    elif value < _SCORE_HOSTILE:
        return -1
    return 0


def _classify_wall(value: float) -> int:
    """Classify H_wall into trit (inverted: high = hostile)."""
    if value < _WALL_SAFE:
        return 1
    elif value > _WALL_HOSTILE:
        return -1
    return 0


def _classify_exp(value: float) -> int:
    """Classify H_exp into trit (inverted: high = hostile)."""
    if value < _EXP_SAFE:
        return 1
    elif value > _EXP_HOSTILE:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def h_trit(d_star: float, phase_deviation: float = 0.0) -> Dict[str, int]:
    """Compute ternary trit decomposition as a dict.

    Convenience wrapper that returns {"t_score": int, "t_wall": int, "t_exp": int}.
    For the full dataclass, use ternary_vector().

    Args:
        d_star: Realm distance from Layer 8.
        phase_deviation: Phase deviation from Layer 10.

    Returns:
        Dict with t_score, t_wall, t_exp each in {-1, 0, +1}.
    """
    tv = ternary_vector(d_star, phase_deviation)
    return {"t_score": tv.t_score, "t_wall": tv.t_wall, "t_exp": tv.t_exp}


def ternary_vector(
    d_star: float,
    phase_deviation: float = 0.0,
    alpha: float = 1.0,
    beta: float = 1.0,
    R: float = PHI,
) -> TritVector:
    """Compute the full three-trit decision vector.

    Evaluates all three H formulas and classifies each into a trit.

    Args:
        d_star: Realm distance from Layer 8.
        phase_deviation: Phase deviation from Layer 10 spin coherence.
        alpha: H_wall amplitude parameter.
        beta: H_wall steepness parameter.
        R: H_exp base (default PHI).

    Returns:
        TritVector with all three trits and raw H values.
    """
    hs = H_score(d_star, phase_deviation)
    hw = H_wall(d_star, alpha, beta)
    he = H_exp(d_star, R)

    return TritVector(
        t_score=_classify_score(hs),
        t_wall=_classify_wall(hw),
        t_exp=_classify_exp(he),
        h_score=hs,
        h_wall=hw,
        h_exp=he,
    )


# ---------------------------------------------------------------------------
# Trit-based L13 decision bridge
# ---------------------------------------------------------------------------

# Decision constants (strings, not enums, for serialization)
ALLOW = "ALLOW"
QUARANTINE = "QUARANTINE"
ESCALATE = "ESCALATE"
DENY = "DENY"


def trit_decision(tv: TritVector) -> str:
    """Map a trit vector to a governance decision.

    Rules (ordered by severity):
        1. Any trit == -1 → DENY
        2. Phase-incoherent (t_score <= 0 but t_wall=+1, t_exp=+1) → ESCALATE
        3. Any trit == 0 → QUARANTINE
        4. All trits == +1 → ALLOW

    The ESCALATE tier captures the "geometrically close but phase-chaotic"
    attacker that simple threshold checks miss. This is the mathematical
    basis for the ESCALATE decision tier in the SaaS API.

    Args:
        tv: TritVector from ternary_vector().

    Returns:
        One of "ALLOW", "QUARANTINE", "ESCALATE", "DENY".
    """
    # Rule 1: any hostile → deny
    if tv.any_hostile:
        return DENY

    # Rule 2: phase-incoherent close attacker → escalate
    if tv.phase_incoherent:
        return ESCALATE

    # Rule 3: any transition → quarantine
    if tv.any_transition:
        return QUARANTINE

    # Rule 4: all safe → allow
    return ALLOW


# ---------------------------------------------------------------------------
# Trit labels — human-readable meanings
# ---------------------------------------------------------------------------

TRIT_LABELS: Dict[Tuple[int, int, int], str] = {
    (+1, +1, +1): "fully_safe",
    (0, 0, 0): "transition_zone",
    (-1, -1, -1): "fully_adversarial",
    (-1, +1, +1): "phase_incoherent_close",    # subtle attack signature
    (0, +1, +1): "phase_incoherent_mild",       # mild phase deviation
    (0, -1, -1): "high_distance_moderate_score",  # aggressive, easy detect
    (+1, 0, 0): "safe_score_transition_geometry",
    (+1, -1, -1): "safe_score_hostile_geometry",  # shouldn't happen normally
    (-1, 0, 0): "hostile_score_transition_geometry",
}


def trit_label(tv: TritVector) -> str:
    """Get human-readable label for a trit vector.

    Args:
        tv: TritVector to label.

    Returns:
        Label string, or "unknown_{t_score}_{t_wall}_{t_exp}" for
        unlabeled combinations.
    """
    key = tv.as_tuple
    return TRIT_LABELS.get(key, f"unknown_{key[0]}_{key[1]}_{key[2]}")
