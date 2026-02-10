"""
HyperbolicRAG: Nearest-neighbor retrieval in the Poincare ball with d* cost gating.
==================================================================================

k-NN search via hyperbolic distance (arcosh metric) with:
- d* cost gating: high-cost candidates quarantined (Layer 12 wall)
- Phase alignment: tongue-phase consistency filters off-grammar chunks
- Trust scoring: inverse cost with phase weighting
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple, Any

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.geoseal import hyperbolic_distance, phase_deviation, clamp_to_ball, TONGUE_PHASES


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class RAGCandidate:
    id: str
    embedding: List[float]
    tongue: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RAGResult:
    id: str
    distance: float
    trust_score: float
    phase_score: float
    gated: bool
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HyperbolicRAGConfig:
    max_k: int = 20
    cost_threshold: float = 1.5
    min_phase_alignment: float = 0.0
    phase_weight: float = 2.0


# ---------------------------------------------------------------------------
# Projection helper
# ---------------------------------------------------------------------------


def project_to_ball(v: List[float], alpha: float = 0.15) -> List[float]:
    """Project embedding to Poincare ball via element-wise tanh scaling."""
    return [math.tanh(alpha * x) for x in v]


# ---------------------------------------------------------------------------
# HyperbolicRAG
# ---------------------------------------------------------------------------


class HyperbolicRAG:
    """Hyperbolic k-NN retrieval with d* cost gating."""

    def __init__(self, config: Optional[HyperbolicRAGConfig] = None):
        self.config = config or HyperbolicRAGConfig()

    def retrieve(
        self,
        query_embedding: List[float],
        candidates: List[RAGCandidate],
        query_tongue: Optional[str] = None,
    ) -> List[RAGResult]:
        """Retrieve trusted candidates via hyperbolic k-NN with cost gating."""
        query = project_to_ball(query_embedding)
        query_phase = TONGUE_PHASES.get(query_tongue) if query_tongue else None

        scored: List[RAGResult] = []
        for c in candidates:
            projected = project_to_ball(list(c.embedding))
            dist = hyperbolic_distance(query, projected)

            cand_phase = TONGUE_PHASES.get(c.tongue) if c.tongue else None
            phase_dev = phase_deviation(query_phase, cand_phase)
            p_score = 1.0 - phase_dev

            raw_trust = 1.0 / (1.0 + dist + self.config.phase_weight * phase_dev)

            gated = (
                dist > self.config.cost_threshold
                or p_score < self.config.min_phase_alignment
            )

            scored.append(
                RAGResult(
                    id=c.id,
                    distance=dist,
                    trust_score=0 if gated else raw_trust,
                    phase_score=p_score,
                    gated=gated,
                    metadata=c.metadata,
                )
            )

        scored.sort(key=lambda x: x.distance)

        results: List[RAGResult] = []
        for s in scored:
            if len(results) >= self.config.max_k:
                break
            if not s.gated:
                results.append(s)

        return results

    def retrieve_all(
        self,
        query_embedding: List[float],
        candidates: List[RAGCandidate],
        query_tongue: Optional[str] = None,
    ) -> List[RAGResult]:
        """Retrieve all results including gated (for diagnostics)."""
        query = project_to_ball(query_embedding)
        query_phase = TONGUE_PHASES.get(query_tongue) if query_tongue else None

        scored: List[RAGResult] = []
        for c in candidates:
            projected = project_to_ball(list(c.embedding))
            dist = hyperbolic_distance(query, projected)
            cand_phase = TONGUE_PHASES.get(c.tongue) if c.tongue else None
            phase_dev = phase_deviation(query_phase, cand_phase)
            p_score = 1.0 - phase_dev
            raw_trust = 1.0 / (1.0 + dist + self.config.phase_weight * phase_dev)
            gated = (
                dist > self.config.cost_threshold
                or p_score < self.config.min_phase_alignment
            )
            scored.append(
                RAGResult(
                    id=c.id,
                    distance=dist,
                    trust_score=0 if gated else raw_trust,
                    phase_score=p_score,
                    gated=gated,
                    metadata=c.metadata,
                )
            )
        scored.sort(key=lambda x: x.distance)
        return scored
