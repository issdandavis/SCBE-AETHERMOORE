"""
Byzantine Fault-Tolerant Consensus - Python Reference Implementation

Corrected BFT consensus: n >= 3f + 1 (not 2f + 1).
For f = 1 fault: need n >= 4 nodes, quorum = 2f + 1 = 3.

This is majority voting with BFT guarantees, NOT full PBFT.

@module ai_brain/bft_consensus
@layer Layer 10, Layer 13
@version 1.1.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ConsensusResult:
    """Result of BFT consensus evaluation."""

    reached: bool
    outcome: Optional[str]  # 'approve', 'reject', or None
    total_nodes: int
    max_faults: int
    required_nodes: int
    quorum_size: int
    vote_counts: Dict[str, int]
    valid_configuration: bool


class BFTConsensus:
    """Byzantine Fault-Tolerant Consensus Engine.

    Corrected formula: requires n >= 3f + 1 total nodes to tolerate f faults.

    For f = 1: n >= 4 nodes, quorum = 3
    For f = 2: n >= 7 nodes, quorum = 5
    For f = 3: n >= 10 nodes, quorum = 7

    Note: This provides BFT guarantees for simple majority decisions.
    It is NOT full PBFT (Practical Byzantine Fault Tolerance).

    Args:
        max_faults: Maximum Byzantine faults to tolerate (default: 1).

    Raises:
        ValueError: If max_faults is negative.
    """

    def __init__(self, max_faults: int = 1):
        if max_faults < 0:
            raise ValueError("max_faults must be a non-negative integer")
        self.max_faults = max_faults
        self.required_nodes = 3 * max_faults + 1
        self.quorum_size = 2 * max_faults + 1

    def evaluate(self, votes: List[str]) -> ConsensusResult:
        """Run consensus on a set of votes.

        Args:
            votes: List of votes ('approve', 'reject', 'abstain').

        Returns:
            ConsensusResult with outcome.
        """
        total_nodes = len(votes)
        valid_config = total_nodes >= self.required_nodes

        vote_counts = {"approve": 0, "reject": 0, "abstain": 0}
        for vote in votes:
            if vote in vote_counts:
                vote_counts[vote] += 1

        if not valid_config:
            return ConsensusResult(
                reached=False,
                outcome=None,
                total_nodes=total_nodes,
                max_faults=self.max_faults,
                required_nodes=self.required_nodes,
                quorum_size=self.quorum_size,
                vote_counts=vote_counts,
                valid_configuration=False,
            )

        reached = False
        outcome = None

        if vote_counts["approve"] >= self.quorum_size:
            reached = True
            outcome = "approve"
        elif vote_counts["reject"] >= self.quorum_size:
            reached = True
            outcome = "reject"

        return ConsensusResult(
            reached=reached,
            outcome=outcome,
            total_nodes=total_nodes,
            max_faults=self.max_faults,
            required_nodes=self.required_nodes,
            quorum_size=self.quorum_size,
            vote_counts=vote_counts,
            valid_configuration=True,
        )

    def is_sufficient(self, node_count: int) -> bool:
        """Check if a given number of nodes is sufficient for this BFT level."""
        return node_count >= self.required_nodes

    @staticmethod
    def max_tolerable_faults(node_count: int) -> int:
        """Compute the maximum faults tolerable for a given node count.

        f_max = floor((n - 1) / 3)
        """
        return (node_count - 1) // 3
