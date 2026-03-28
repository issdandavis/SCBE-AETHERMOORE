"""Phi-Ternary Primitive — golden-ratio-weighted ternary logic.

The fundamental engineering primitive from the 2026-03-25 research session:

  state:     q in {-1, 0, +1}   (ternary decision)
  scale:     w = phi^k           (golden ratio hierarchy)
  embedding: x = q * w           (phi-lifted ternary value)

Ternary decides DIRECTION. Phi decides STRENGTH.
The neutral (0) is a REAL state, not absence.
Positive/negative mirror symmetrically around it.

Patent relevant: extends USPTO #63/961,403
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

PHI = (1 + math.sqrt(5)) / 2  # 1.6180339887...


@dataclass(frozen=True)
class PhiTernary:
    """A phi-weighted ternary value.

    q: ternary state (-1, 0, +1)
    k: phi exponent (determines scale/depth)
    """

    q: int  # -1, 0, or +1
    k: int  # phi exponent

    def __post_init__(self):
        if self.q not in (-1, 0, 1):
            raise ValueError(f"q must be -1, 0, or +1, got {self.q}")

    @property
    def weight(self) -> float:
        """Phi-scaled weight: phi^k."""
        return PHI**self.k

    @property
    def value(self) -> float:
        """Phi-lifted ternary value: q * phi^k."""
        return self.q * self.weight

    @property
    def is_neutral(self) -> bool:
        return self.q == 0

    @property
    def is_positive(self) -> bool:
        return self.q == 1

    @property
    def is_negative(self) -> bool:
        return self.q == -1

    def mirror(self) -> "PhiTernary":
        """Reflect through the ternary center: q -> -q."""
        return PhiTernary(q=-self.q, k=self.k)

    def scale_up(self) -> "PhiTernary":
        """Move one phi level deeper: k -> k+1."""
        return PhiTernary(q=self.q, k=self.k + 1)

    def scale_down(self) -> "PhiTernary":
        """Move one phi level shallower: k -> k-1."""
        return PhiTernary(q=self.q, k=self.k - 1)


def phi_ternary(q: int, k: int = 0) -> PhiTernary:
    """Create a phi-ternary value."""
    return PhiTernary(q=q, k=k)


# ── Dual Ternary ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DualPhiTernary:
    """Two independent phi-ternary systems that verify each other.

    System A: e.g., Hamiltonian Braid (Mirror/Shift/Refactor)
    System B: e.g., Governance Gate (ALLOW/QUARANTINE/DENY)

    Agreement: both centers match -> 1 = 1
    Disagreement: non-congruent object detected
    """

    a: PhiTernary
    b: PhiTernary

    @property
    def agrees(self) -> bool:
        """Do both systems agree on direction?"""
        return self.a.q == self.b.q

    @property
    def disagreement_score(self) -> float:
        """Phi-scaled disagreement magnitude."""
        if self.agrees:
            return 0.0
        diff = abs(self.a.q - self.b.q)  # 0, 1, or 2
        max_k = max(self.a.k, self.b.k)
        return diff * PHI**max_k

    @property
    def combined_value(self) -> float:
        """Weighted average of both systems."""
        if self.agrees:
            return self.a.value
        # Disagreement: use the higher-confidence system (higher k)
        if self.a.k >= self.b.k:
            return self.a.value
        return self.b.value

    @property
    def is_non_congruent(self) -> bool:
        """A non-congruent object: systems disagree on direction."""
        return self.a.q != 0 and self.b.q != 0 and self.a.q != self.b.q


def dual_phi_ternary(qa: int, ka: int, qb: int, kb: int) -> DualPhiTernary:
    """Create a dual phi-ternary pair."""
    return DualPhiTernary(a=PhiTernary(qa, ka), b=PhiTernary(qb, kb))


# ── Tongue Mapping ────────────────────────────────────────────────────────

TONGUE_PHI_K = {
    "KO": 0,  # phi^0 = 1.000
    "AV": 1,  # phi^1 = 1.618
    "RU": 2,  # phi^2 = 2.618
    "CA": 3,  # phi^3 = 4.236
    "UM": 4,  # phi^4 = 6.854
    "DR": 5,  # phi^5 = 11.090
}


def tongue_phi_ternary(tongue: str, decision: int) -> PhiTernary:
    """Create a phi-ternary for a specific Sacred Tongue.

    tongue: KO, AV, RU, CA, UM, DR
    decision: -1 (inhibit), 0 (neutral), +1 (activate)
    """
    k = TONGUE_PHI_K.get(tongue, 0)
    return PhiTernary(q=decision, k=k)


def tongue_vector_to_phi_ternary(activations: List[float], threshold: float = 0.1) -> List[PhiTernary]:
    """Convert a 6D tongue activation vector to phi-ternary values.

    Each tongue's activation is quantized to {-1, 0, +1} based on threshold,
    then phi-weighted by tongue index.
    """
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
    result = []
    for i, (tongue, val) in enumerate(zip(tongues, activations)):
        if val > threshold:
            q = 1
        elif val < -threshold:
            q = -1
        else:
            q = 0
        result.append(PhiTernary(q=q, k=i))
    return result


def phi_ternary_energy(values: List[PhiTernary]) -> float:
    """Total energy of a phi-ternary vector.

    Energy = sum of |value|^2 = sum of (q * phi^k)^2.
    Neutral states contribute 0. Activated states contribute phi^(2k).
    """
    return sum(v.value**2 for v in values)


def phi_ternary_center(values: List[PhiTernary]) -> float:
    """Center of mass of a phi-ternary vector.

    If perfectly balanced: center = 0 (the ternary center).
    Deviation from 0 = asymmetry = potential non-congruence.
    """
    if not values:
        return 0.0
    return sum(v.value for v in values) / len(values)


def phi_ternary_symmetry(values: List[PhiTernary]) -> float:
    """Symmetry score: 1.0 = perfect ternary balance, 0.0 = fully asymmetric.

    Measures how close the positive and negative components are to mirroring
    each other, with neutral states stabilizing the center.
    """
    pos_sum = sum(v.weight for v in values if v.is_positive)
    neg_sum = sum(v.weight for v in values if v.is_negative)
    total = pos_sum + neg_sum
    if total == 0:
        return 1.0  # All neutral = perfect balance
    return 1.0 - abs(pos_sum - neg_sum) / total
