"""Negative Space Encoder -- complement embeddings.

The insight: knowing what something IS NOT is as informative as
knowing what it IS.  In balanced ternary, the complement is trivial:
flip every trit via Kleene NOT (-1 <-> +1, 0 stays 0).

The negative space reveals:
  - Which tongues are excluded (trits that become -1)
  - The anti-energy (energy of the complement configuration)
  - The "shadow" of the signal in lattice space

@layer Layer 9, Layer 12
@component HybridEncoder.NegativeSpace
"""
from __future__ import annotations

import math
from typing import List, Tuple

from src.hybrid_encoder.types import NegativeSpaceEmbedding, TONGUE_NAMES

PHI = (1 + math.sqrt(5)) / 2

# Phi-scaled tongue weights matching the Langues metric
_TONGUE_WEIGHTS = [PHI ** i for i in range(6)]


class NegativeSpaceEncoder:
    """Compute negative space (complement) embeddings."""

    def encode(self, tongue_trits: List[int]) -> NegativeSpaceEmbedding:
        """Compute the negative space of a 6-trit tongue vector.

        1. Kleene NOT each trit: +1 -> -1, -1 -> +1, 0 -> 0
        2. Identify excluded tongues (complement trits == -1)
        3. Compute anti-energy: sum of |complement_trit| * phi_weight
        """
        if len(tongue_trits) < 6:
            tongue_trits = tongue_trits + [0] * (6 - len(tongue_trits))

        complement = tuple(-t for t in tongue_trits[:6])

        excluded: List[str] = []
        for i, ct in enumerate(complement):
            if ct == -1 and i < len(TONGUE_NAMES):
                excluded.append(TONGUE_NAMES[i])

        anti_energy = sum(
            abs(ct) * _TONGUE_WEIGHTS[i]
            for i, ct in enumerate(complement)
        )

        return NegativeSpaceEmbedding(
            complement_trits=complement,
            excluded_tongues=excluded,
            anti_energy=anti_energy,
        )

    @staticmethod
    def complement_distance(original: List[int], candidate: List[int]) -> float:
        """Measure how close a candidate is to the negative space of the original.

        High distance = candidate is far from what the original IS NOT,
        meaning the candidate is MORE similar to the original.
        Low distance = candidate IS in the negative space (dissimilar).

        Uses phi-weighted Hamming distance in ternary space.
        """
        neg_original = [-t for t in original[:6]]
        dist = 0.0
        for i in range(min(6, len(candidate))):
            c = candidate[i] if i < len(candidate) else 0
            n = neg_original[i] if i < len(neg_original) else 0
            # Ternary difference: 0 if same, 1 if adjacent, 2 if opposite
            diff = abs(c - n)
            dist += diff * _TONGUE_WEIGHTS[i]
        return dist
