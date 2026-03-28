"""
Negative Tongue Lattice — 12D from 6D via lazy sign-flip.
==========================================================

Extends the 6 Sacred Tongues (KO, AV, RU, CA, UM, DR) into a 12-dimensional
space by computing negative tongue coordinates on demand. The negative space
is never stored — it is a FUNCTION, not a value.

Cross-tongue bridges connect positive[a] to negative[b], weighted by phi
raised to the tongue-distance power. These bridges exist only during
computation and evaporate after the return.

Zero additional RAM cost: the lattice object is stateless after __init__.

Usage:
    lattice = NegativeTongueLattice()
    coords = [0.8, 0.3, 0.6, 0.2, 0.9, 0.4]  # 6D tongue coordinates

    # Full 6x6 cross-tongue bridge lattice (30 entries, no self-bridges)
    bridges = lattice.full_lattice(coords)

    # Total lattice energy (high = adversarial tension)
    energy = lattice.lattice_energy(coords)

    # Interference pattern: constructive vs destructive bridges
    pattern = lattice.interference_pattern(coords)

RuntimeGate Integration:
    When use_negative_lattice=True on RuntimeGate, the lattice energy is
    computed after tongue coordinates are extracted and added to the cost
    signal. Higher lattice energy = higher suspicion = more expensive action.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


class NegativeTongueLattice:
    """12D tongue system: 6 positive + 6 negative, with lazy cross-bridges.

    Negative tongue space is computed on-demand by sign-flipping the positive
    coordinates. Cross-tongue bridges are functions, not stored values.
    Zero additional RAM cost.
    """

    TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
    PHI = 1.618033988749895

    def __init__(self) -> None:
        pass  # Stateless — all computation is lazy

    def negative_coords(self, positive_coords: List[float]) -> List[float]:
        """Compute negative tongue space by sign flip. Not stored."""
        return [1.0 - c for c in positive_coords]

    def bridge(self, tongue_a: str, tongue_b: str, coords: List[float]) -> float:
        """Lazy cross-tongue bridge: positive[a] * negative[b].

        Exists only during computation. Zero memory after return.
        The bridge is a FUNCTION, not a stored value.
        """
        idx_a = self.TONGUES.index(tongue_a)
        idx_b = self.TONGUES.index(tongue_b)
        neg_b = 1.0 - coords[idx_b]  # negative space
        phi_weight = self.PHI ** abs(idx_a - idx_b)  # distance-based phi scaling
        return coords[idx_a] * neg_b / phi_weight

    def full_lattice(self, coords: List[float]) -> Dict[str, float]:
        """Compute the full 6x6 cross-tongue lattice on demand.

        Returns a dict of all 30 bridges (6x6 minus 6 self-bridges).
        The dict is the only thing stored. The computation evaporates.
        """
        result: Dict[str, float] = {}
        neg = self.negative_coords(coords)
        for i, ta in enumerate(self.TONGUES):
            for j, tb in enumerate(self.TONGUES):
                if i != j:  # no self-bridge
                    phi_w = self.PHI ** abs(i - j)
                    result[f"{ta}->{tb}"] = coords[i] * neg[j] / phi_w
        return result

    def lattice_energy(self, coords: List[float]) -> float:
        """Total energy of the cross-tongue lattice.

        High energy = tongues are in tension (adversarial signal).
        Low energy = tongues are in harmony (benign signal).
        """
        lattice = self.full_lattice(coords)
        return sum(abs(v) for v in lattice.values())

    def strongest_bridge(self, coords: List[float]) -> Tuple[str, float]:
        """Find the strongest cross-tongue connection."""
        lattice = self.full_lattice(coords)
        if not lattice:
            return ("none", 0.0)
        key = max(lattice, key=lambda k: abs(lattice[k]))
        return (key, lattice[key])

    def weakest_bridge(self, coords: List[float]) -> Tuple[str, float]:
        """Find the weakest cross-tongue connection (potential null-space)."""
        lattice = self.full_lattice(coords)
        if not lattice:
            return ("none", 0.0)
        key = min(lattice, key=lambda k: abs(lattice[k]))
        return (key, lattice[key])

    def interference_pattern(self, coords: List[float]) -> Dict[str, Dict[str, float]]:
        """Classify each bridge as constructive, destructive, or neutral.

        Neutral:      abs(value) < 0.01 (near-zero, checked first)
        Constructive: value > 0 (tongues reinforce)
        Destructive:  value < 0 (tongues cancel = Flux Framework)

        Categories are mutually exclusive: neutral takes priority over
        constructive/destructive for near-zero values.
        """
        lattice = self.full_lattice(coords)
        constructive: Dict[str, float] = {}
        destructive: Dict[str, float] = {}
        neutral: Dict[str, float] = {}
        for k, v in lattice.items():
            if abs(v) < 0.01:
                neutral[k] = v
            elif v > 0:
                constructive[k] = v
            else:
                destructive[k] = v
        return {
            "constructive": constructive,
            "destructive": destructive,
            "neutral": neutral,
        }
