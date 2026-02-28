"""
Geometric Composition — Product Manifold (S² x Cl(6,0))^n
===========================================================

Full geometric composition layer:
1. Group dressed bits by tongue → 6 tongue groups
2. Intra-tongue: graph convolution on each sphere grid
3. Cross-tongue: 15 bivector interaction channels (C(6,2) pairs)
4. Convergence: exponential map to hyperbolic manifold

For the lightweight M6 integration layer, see composition.py.

@layer L5, L6, L9, L12
@component GeoSeed.CompositionGeometric
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.geoseed.sphere_grid import (
    TONGUE_NAMES,
    PHI_WEIGHTS,
    CL6,
    SphereGrid,
    SphereGridNetwork,
    poincare_project,
    mobius_add,
    hyperbolic_distance,
    cross_tongue_convolve,
)
from src.geoseed.dressing_geometric import GeometricDressedBit, GovernanceDecision


@dataclass
class CrossTerm:
    """A bivector interaction between two tongues."""

    tongue_a: str
    tongue_b: str
    bivector_index: int
    strength: float
    correlation: float

    @property
    def energy(self) -> float:
        return abs(self.strength * self.correlation)


@dataclass
class GeometricSemanticUnit:
    """Composed semantic unit from the product manifold (S² x Cl(6,0))^n."""

    bits: List[GeometricDressedBit]
    tongue_signals: Dict[str, np.ndarray] = field(default_factory=dict)
    cross_terms: List[CrossTerm] = field(default_factory=list)
    convergence_point: Optional[np.ndarray] = None
    total_energy: float = 0.0
    governance_ratio: float = 1.0

    @property
    def n_bits(self) -> int:
        return len(self.bits)

    @property
    def active_tongues(self) -> List[str]:
        return [t for t, s in self.tongue_signals.items() if np.any(s != 0)]

    @property
    def n_interactions(self) -> int:
        n = len(self.active_tongues)
        return n * (n - 1) // 2

    def to_embedding(self, dim: int = 384) -> np.ndarray:
        """Convert to a fixed-size embedding vector."""
        parts = []

        if self.convergence_point is not None:
            parts.append(self.convergence_point)

        for tongue in TONGUE_NAMES:
            if tongue in self.tongue_signals:
                parts.append(self.tongue_signals[tongue])
            else:
                parts.append(np.zeros(64))

        energies = np.array([ct.energy for ct in self.cross_terms])
        parts.append(energies)

        scalars = np.array([
            self.total_energy,
            self.governance_ratio,
            float(self.n_bits),
            float(self.n_interactions),
        ])
        parts.append(scalars)

        full = np.concatenate(parts)
        if len(full) >= dim:
            return full[:dim]
        return np.pad(full, (0, dim - len(full)))


class GeometricComposer:
    """Full geometric composition via sphere grid propagation + bivector interactions."""

    def __init__(
        self,
        resolution: int = 3,
        signal_dim: int = 64,
        n_propagation_steps: int = 2,
        include_quarantined: bool = False,
    ):
        self.network = SphereGridNetwork(resolution=resolution, signal_dim=signal_dim)
        self.n_propagation_steps = n_propagation_steps
        self.include_quarantined = include_quarantined

    def compose(self, dressed_bits: List[GeometricDressedBit]) -> GeometricSemanticUnit:
        """Compose dressed bits into a semantic unit via the product manifold."""
        if self.include_quarantined:
            active_bits = [b for b in dressed_bits if b.decision != GovernanceDecision.DENY]
        else:
            active_bits = [b for b in dressed_bits if b.decision == GovernanceDecision.ALLOW]

        allowed_count = sum(1 for b in dressed_bits if b.decision == GovernanceDecision.ALLOW)
        governance_ratio = allowed_count / max(len(dressed_bits), 1)

        self.network.clear_all()

        for bit in active_bits:
            if bit.sphere_position is not None and bit.multivector is not None:
                self.network.deposit(bit.tongue, bit.sphere_position, bit.multivector)

        final_signals = self.network.forward(n_steps=self.n_propagation_steps)

        tongue_signals = {}
        for tongue in TONGUE_NAMES:
            tongue_signals[tongue] = self.network.grids[tongue].signals.mean(axis=0)

        cross_terms = []
        for t1, t2 in self.network.tongue_pairs:
            bv_idx = CL6.tongue_bivector_index(t1, t2)
            strength = CL6.bivector_strength(t1, t2)
            correlation = float(np.dot(tongue_signals[t1], tongue_signals[t2]))
            cross_terms.append(CrossTerm(
                tongue_a=t1,
                tongue_b=t2,
                bivector_index=bv_idx,
                strength=strength,
                correlation=correlation,
            ))

        total_energy = sum(ct.energy for ct in cross_terms)

        convergence = np.zeros(64)
        total_phi = sum(PHI_WEIGHTS.values())
        for tongue in TONGUE_NAMES:
            weight = PHI_WEIGHTS[tongue]
            projected = poincare_project(tongue_signals[tongue])
            convergence = mobius_add(convergence, weight * projected / total_phi)

        return GeometricSemanticUnit(
            bits=active_bits,
            tongue_signals=tongue_signals,
            cross_terms=cross_terms,
            convergence_point=convergence,
            total_energy=total_energy,
            governance_ratio=governance_ratio,
        )

    def compose_sequence(
        self,
        dressed_bits: List[GeometricDressedBit],
        window_size: int = 6,
        stride: int = 6,
    ) -> List[GeometricSemanticUnit]:
        """Compose a sequence using a sliding window."""
        units = []
        for start in range(0, len(dressed_bits), stride):
            window = dressed_bits[start : start + window_size]
            if len(window) < 2:
                break
            units.append(self.compose(window))
        return units
