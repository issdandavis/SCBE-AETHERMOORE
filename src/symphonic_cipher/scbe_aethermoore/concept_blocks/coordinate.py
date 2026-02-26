"""
Concept Blocks — COORDINATE
============================

Byzantine Fault Tolerant swarm consensus.  Maps to SCBE Layer 12
(polyglot / multi-agent coordination).

BFTConsensus
------------
Simplified PBFT-style consensus: nodes propose values, votes are
tallied, and agreement requires > 2/3 of participants.

CoordinateBlock
---------------
ConceptBlock wrapper — feed proposals into ``tick()`` and get
consensus result back.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Hashable, List, Optional, Tuple

from .base import BlockResult, BlockStatus, ConceptBlock


@dataclass
class SwarmNode:
    """A participant in the consensus protocol."""
    node_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    trust_score: float = 1.0
    is_byzantine: bool = False


class BFTConsensus:
    """Simple BFT consensus engine.

    Tolerates up to ``max_faulty`` Byzantine nodes out of ``num_nodes``.
    Default: max_faulty = floor((num_nodes - 1) / 3)  (classic 3f+1).
    """

    def __init__(self, num_nodes: int, max_faulty: Optional[int] = None) -> None:
        self.num_nodes = num_nodes
        self.max_faulty = max_faulty if max_faulty is not None else (num_nodes - 1) // 3
        self._proposals: List[Tuple[str, Any, float]] = []  # (node_id, value, trust)

    @property
    def quorum(self) -> int:
        """Minimum votes needed for consensus (2f+1)."""
        return 2 * self.max_faulty + 1

    def propose(self, node_id: str, value: Any, trust: float = 1.0) -> None:
        self._proposals.append((node_id, value, trust))

    def collect_votes(self) -> Dict[Any, float]:
        """Tally proposals. Returns {value: weighted_vote_count}."""
        tally: Dict[Any, float] = {}
        for _nid, val, trust in self._proposals:
            key = val if isinstance(val, Hashable) else str(val)
            tally[key] = tally.get(key, 0.0) + trust
        return tally

    def reach_consensus(self) -> Tuple[bool, Any]:
        """Attempt consensus. Returns (success, agreed_value)."""
        tally = self.collect_votes()
        if not tally:
            return False, None

        best_val = max(tally, key=tally.get)
        best_votes = tally[best_val]

        if best_votes >= self.quorum:
            return True, best_val
        return False, None

    def reset(self) -> None:
        self._proposals.clear()


# -- concept block wrapper ---------------------------------------------------

class CoordinateBlock(ConceptBlock):
    """Concept block wrapping BFT swarm consensus.

    tick(inputs):
        inputs["proposals"]  — List[Dict] each with "node_id", "value", and optional "trust"
    returns:
        BlockResult with output={
            "consensus_reached": bool,
            "agreed_value": Any,
            "vote_tally": Dict,
            "fault_tolerance": int,
            "quorum": int,
        }
    """

    def __init__(self, num_nodes: int = 4, max_faulty: Optional[int] = None, name: str = "COORDINATE") -> None:
        super().__init__(name)
        self._consensus = BFTConsensus(num_nodes, max_faulty)

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        proposals = inputs.get("proposals", [])
        if not proposals:
            return BlockResult(status=BlockStatus.FAILURE, message="No proposals provided")

        self._consensus.reset()
        for p in proposals:
            self._consensus.propose(
                node_id=p["node_id"],
                value=p["value"],
                trust=p.get("trust", 1.0),
            )

        reached, value = self._consensus.reach_consensus()
        tally = self._consensus.collect_votes()

        return BlockResult(
            status=BlockStatus.SUCCESS if reached else BlockStatus.FAILURE,
            output={
                "consensus_reached": reached,
                "agreed_value": value,
                "vote_tally": tally,
                "fault_tolerance": self._consensus.max_faulty,
                "quorum": self._consensus.quorum,
                "total_proposals": len(proposals),
            },
            message="Consensus reached" if reached else "No consensus",
        )

    def _do_configure(self, params: Dict[str, Any]) -> None:
        if "num_nodes" in params or "max_faulty" in params:
            self._consensus = BFTConsensus(
                num_nodes=params.get("num_nodes", self._consensus.num_nodes),
                max_faulty=params.get("max_faulty", None),
            )

    def _do_reset(self) -> None:
        self._consensus.reset()
