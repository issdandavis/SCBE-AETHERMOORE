"""Stage 3.5: Mirror Phase Semantic Refractor Symmetry.

Passes each record through three mirrors, splitting meaning into:
- Symmetric component (survives reflection — robust, foundational)
- Antisymmetric component (flips under reflection — contextual, fragile)
- Phase angles (rotation to align reflection — semantic orientation)

Like shining white light through a prism. The record enters as combined
meaning and exits decomposed into spectral components.

Tongue mirror pairs (each forms a reflection axis):
  KO ↔ DR  (Intent ↔ Architecture)   — command structure symmetry
  AV ↔ CA  (Wisdom ↔ Compute)        — knowledge-computation duality
  RU ↔ UM  (Governance ↔ Security)   — policy-enforcement mirror
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .config import (
    PHI,
    TONGUES,
    TONGUE_MIRROR_PAIRS,
    TONGUE_WEIGHTS,
    MIRROR_ANTISYMMETRIC_THRESHOLD,
    MIRROR_SYMMETRIC_THRESHOLD,
)


@dataclass
class MirrorResult:
    """Output of the mirror phase semantic refractor."""

    # Three mirror deltas (whole, edge, signal)
    mirror_deltas: list[float]

    # Symmetric decomposition (meaning that survives reflection)
    symmetric_profile: dict[str, float]

    # Antisymmetric decomposition (meaning that flips under reflection)
    antisymmetric_profile: dict[str, float]

    # Phase angles for each mirror pair axis (3 values)
    phase_angles: list[float]

    # Composite health score [0,1]
    mirror_health_score: float

    # Classification based on symmetry
    stability_class: str  # "robust" | "fragile" | "mixed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mirror_deltas": self.mirror_deltas,
            "symmetric_profile": self.symmetric_profile,
            "antisymmetric_profile": self.antisymmetric_profile,
            "phase_angles": self.phase_angles,
            "mirror_health_score": self.mirror_health_score,
            "stability_class": self.stability_class,
        }


# ---------------------------------------------------------------------------
# Mirror operations
# ---------------------------------------------------------------------------


def _reflect_profile(profile: dict[str, float]) -> dict[str, float]:
    """Reflect a tongue profile through all three mirror axes.

    Each mirror pair swaps values:
      KO ↔ DR, AV ↔ CA, RU ↔ UM
    """
    reflected = dict(profile)
    for a, b in TONGUE_MIRROR_PAIRS:
        reflected[a], reflected[b] = profile.get(b, 0.0), profile.get(a, 0.0)
    return reflected


def _edge_reflect(profile: dict[str, float]) -> dict[str, float]:
    """Reflect only the boundary tongues (highest and lowest activation).

    Swaps the max and min tongue values, leaving the middle untouched.
    Tests stability of the extremes.
    """
    sorted_tongues = sorted(profile.items(), key=lambda x: x[1])
    reflected = dict(profile)
    if len(sorted_tongues) >= 2:
        lo_tongue, lo_val = sorted_tongues[0]
        hi_tongue, hi_val = sorted_tongues[-1]
        reflected[lo_tongue] = hi_val
        reflected[hi_tongue] = lo_val
    return reflected


def _signal_reflect(null_pattern: dict[str, int]) -> dict[str, float]:
    """Reflect the null pattern — what does absence look like from the other side?

    Inverts the null pattern: present becomes absent, absent becomes present.
    Then converts to a profile-like dict for comparison.
    """
    return {t: (1.0 - v) for t, v in null_pattern.items()}


def _profile_delta(a: dict[str, float], b: dict[str, float]) -> float:
    """L2 distance between two profiles, phi-weighted."""
    total = 0.0
    for t in TONGUES:
        diff = (a.get(t, 0.0) - b.get(t, 0.0)) * TONGUE_WEIGHTS[t]
        total += diff * diff
    return math.sqrt(total)


def _symmetric_decompose(
    profile: dict[str, float],
    reflected: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    """Decompose into symmetric (survives) and antisymmetric (flips) components.

    symmetric  = (profile + reflected) / 2
    antisymmetric = (profile - reflected) / 2
    """
    sym = {}
    antisym = {}
    for t in TONGUES:
        p = profile.get(t, 0.0)
        r = reflected.get(t, 0.0)
        sym[t] = (p + r) / 2
        antisym[t] = abs(p - r) / 2  # abs because we care about magnitude
    return sym, antisym


def _compute_phase_angle(a_val: float, b_val: float) -> float:
    """Compute phase angle between mirror pair values.

    Uses atan2 to get the rotation angle in the 2D plane defined by
    the mirror pair. This IS the semantic orientation.
    """
    return math.atan2(b_val - a_val, a_val + b_val + 1e-10)


# ---------------------------------------------------------------------------
# Main refractor
# ---------------------------------------------------------------------------


def refract(
    tongue_profile: dict[str, float],
    null_pattern: dict[str, int],
) -> MirrorResult:
    """Apply the mirror phase semantic refractor to a record.

    Three mirrors:
    1. Whole mirror: reflect entire tongue profile, measure delta
    2. Edge mirror: reflect boundary tongues only, measure stability
    3. Signal mirror: reflect null pattern, see absence from the other side
    """
    # Mirror 1: Whole reflection
    whole_reflected = _reflect_profile(tongue_profile)
    whole_delta = _profile_delta(tongue_profile, whole_reflected)

    # Mirror 2: Edge reflection
    edge_reflected = _edge_reflect(tongue_profile)
    edge_delta = _profile_delta(tongue_profile, edge_reflected)

    # Mirror 3: Signal reflection (null pattern inversion)
    signal_reflected = _signal_reflect(null_pattern)
    # Compare signal reflection to original profile
    signal_delta = _profile_delta(tongue_profile, signal_reflected)

    mirror_deltas = [whole_delta, edge_delta, signal_delta]

    # Symmetric / antisymmetric decomposition (using whole mirror)
    symmetric, antisymmetric = _symmetric_decompose(tongue_profile, whole_reflected)

    # Phase angles for each mirror pair axis
    phase_angles = []
    for a_tongue, b_tongue in TONGUE_MIRROR_PAIRS:
        angle = _compute_phase_angle(
            tongue_profile.get(a_tongue, 0.0),
            tongue_profile.get(b_tongue, 0.0),
        )
        phase_angles.append(angle)

    # Mirror health score: high symmetry = healthy, high antisymmetry = fragile
    sym_norm = math.sqrt(sum(v ** 2 for v in symmetric.values())) or 1e-10
    antisym_norm = math.sqrt(sum(v ** 2 for v in antisymmetric.values()))
    health = sym_norm / (sym_norm + antisym_norm + 1e-10)

    # Stability classification
    antisym_ratio = antisym_norm / (sym_norm + antisym_norm + 1e-10)
    if antisym_ratio > MIRROR_ANTISYMMETRIC_THRESHOLD:
        stability_class = "fragile"
    elif antisym_ratio < (1.0 - MIRROR_SYMMETRIC_THRESHOLD):
        stability_class = "robust"
    else:
        stability_class = "mixed"

    return MirrorResult(
        mirror_deltas=mirror_deltas,
        symmetric_profile=symmetric,
        antisymmetric_profile=antisymmetric,
        phase_angles=phase_angles,
        mirror_health_score=round(health, 6),
        stability_class=stability_class,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test with a security-heavy profile (UM dominant)
    test_profile = {"KO": 0.05, "AV": 0.10, "RU": 0.15, "CA": 0.20, "UM": 0.35, "DR": 0.15}
    test_null = {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}

    result = refract(test_profile, test_null)

    print("Mirror Phase Semantic Refractor")
    print(f"  Input profile: {test_profile}")
    print(f"  Null pattern:  {test_null}")
    print()
    print(f"  Mirror deltas:      {[f'{d:.4f}' for d in result.mirror_deltas]}")
    print(f"  Symmetric:          {result.symmetric_profile}")
    print(f"  Antisymmetric:      {result.antisymmetric_profile}")
    print(f"  Phase angles (rad): {[f'{a:.4f}' for a in result.phase_angles]}")
    print(f"  Health score:       {result.mirror_health_score}")
    print(f"  Stability class:    {result.stability_class}")
