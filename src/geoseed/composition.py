"""
GeoSeed Composition
===================

Aggregate dressed bits into semantic units suitable for M6 routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from src.geoseed.dressing import DressedBit


@dataclass
class SemanticUnit:
    """Composed semantic bundle from one or more dressed bits."""

    unit_id: str
    tongues: List[str]
    state21d: List[float]
    confidence: float
    metadata: Dict[str, object]


class DressedBitComposer:
    """Compose dressed bits into a stable semantic unit."""

    def compose(self, bits: Sequence[DressedBit], *, unit_id: str = "unit-0") -> SemanticUnit:
        if not bits:
            return SemanticUnit(
                unit_id=unit_id,
                tongues=[],
                state21d=[0.0] * 21,
                confidence=0.0,
                metadata={"bit_count": 0},
            )

        dim = 21
        accum = [0.0] * dim
        for bit in bits:
            for i in range(dim):
                accum[i] += bit.state21d[i]

        state21d = [round(v / len(bits), 6) for v in accum]
        tongues = sorted({b.tongue for b in bits})

        # Confidence grows with evidence volume, capped at 1.0.
        confidence = min(1.0, round(0.35 + (len(bits) / 100.0), 4))

        run_ids = sorted({b.run_id for b in bits})
        metadata = {
            "bit_count": len(bits),
            "run_ids": run_ids,
        }

        return SemanticUnit(
            unit_id=unit_id,
            tongues=tongues,
            state21d=state21d,
            confidence=confidence,
            metadata=metadata,
        )
