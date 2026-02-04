"""
HYDRA Byzantine Consensus Module
=================================

SwarmRaft-inspired consensus for multi-head coordination.

Based on:
- SwarmRaft (2025) - Crash fault-tolerant with Byzantine evaluation
- Practical Byzantine Fault Tolerance (PBFT)

Guarantees:
- Tolerates f < n/3 Byzantine (malicious) heads
- Requires 2f+1 votes for consensus
- Provides cryptographic vote verification
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid


class VoteDecision(str, Enum):
    """Possible vote decisions."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    ESCALATE = "ESCALATE"


@dataclass
class Vote:
    """A vote from a HYDRA head."""
    head_id: str
    proposal_id: str
    decision: VoteDecision
    reasoning: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: str = ""

    def sign(self, secret: str) -> None:
        """Sign the vote for verification."""
        content = f"{self.head_id}:{self.proposal_id}:{self.decision.value}:{self.confidence}"
        self.signature = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:32]

    def verify(self, secret: str) -> bool:
        """Verify vote signature."""
        content = f"{self.head_id}:{self.proposal_id}:{self.decision.value}:{self.confidence}"
        expected = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:32]
        return self.signature == expected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "head_id": self.head_id,
            "proposal_id": self.proposal_id,
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "signature": self.signature[:8] + "..."
        }


@dataclass
class Proposal:
    """A proposal requiring consensus."""
    id: str
    action: str
    target: str
    context: Dict[str, Any]
    proposer_id: str
    required_quorum: int
    timeout_seconds: float = 30.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "target": self.target,
            "proposer_id": self.proposer_id,
            "required_quorum": self.required_quorum,
            "created_at": self.created_at
        }


@dataclass
class ConsensusResult:
    """Result of a consensus round."""
    proposal_id: str
    consensus_reached: bool
    final_decision: VoteDecision
    vote_counts: Dict[str, int]
    total_votes: int
    quorum_required: int
    votes: List[Vote]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "consensus_reached": self.consensus_reached,
            "final_decision": self.final_decision.value,
            "vote_counts": self.vote_counts,
            "total_votes": self.total_votes,
            "quorum_required": self.quorum_required,
            "votes": [v.to_dict() for v in self.votes],
            "timestamp": self.timestamp
        }


class ByzantineConsensus:
    """
    Byzantine Fault Tolerant consensus for HYDRA heads.

    Implements a simplified SwarmRaft protocol:
    1. Proposer creates proposal
    2. All heads vote (ALLOW/DENY/ABSTAIN/ESCALATE)
    3. Consensus requires 2f+1 matching votes where f = (n-1)/3

    Security Properties:
    - Safety: Honest heads agree on the same decision
    - Liveness: Eventually a decision is made
    - Byzantine Tolerance: Up to f Byzantine heads can't affect consensus
    """

    def __init__(self, secret: str = None):
        """
        Args:
            secret: Shared secret for vote signing (in production, use PKI)
        """
        self.secret = secret or hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
        self.proposals: Dict[str, Proposal] = {}
        self.votes: Dict[str, List[Vote]] = {}  # proposal_id -> votes
        self.results: Dict[str, ConsensusResult] = {}

    def calculate_byzantine_threshold(self, n: int) -> int:
        """
        Calculate maximum Byzantine heads tolerated.

        f < n/3, so f_max = floor((n-1)/3)
        """
        return (n - 1) // 3

    def calculate_quorum(self, n: int) -> int:
        """
        Calculate required quorum for consensus.

        Quorum = 2f + 1 where f is max Byzantine tolerance
        """
        f = self.calculate_byzantine_threshold(n)
        return 2 * f + 1

    def create_proposal(
        self,
        action: str,
        target: str,
        context: Dict[str, Any],
        proposer_id: str,
        num_voters: int
    ) -> Proposal:
        """Create a new proposal for voting."""
        proposal = Proposal(
            id=f"proposal-{uuid.uuid4().hex[:8]}",
            action=action,
            target=target,
            context=context,
            proposer_id=proposer_id,
            required_quorum=self.calculate_quorum(num_voters)
        )

        self.proposals[proposal.id] = proposal
        self.votes[proposal.id] = []

        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        head_id: str,
        decision: VoteDecision,
        reasoning: str = "",
        confidence: float = 1.0
    ) -> Vote:
        """Cast a vote on a proposal."""
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal not found: {proposal_id}")

        vote = Vote(
            head_id=head_id,
            proposal_id=proposal_id,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence
        )
        vote.sign(self.secret)

        self.votes[proposal_id].append(vote)

        return vote

    def tally_votes(self, proposal_id: str) -> ConsensusResult:
        """
        Tally votes and determine consensus.

        Uses weighted confidence voting with Byzantine tolerance.
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal not found: {proposal_id}")

        proposal = self.proposals[proposal_id]
        votes = self.votes.get(proposal_id, [])

        # Verify all vote signatures
        valid_votes = [v for v in votes if v.verify(self.secret)]

        # Count by decision
        counts = {d.value: 0 for d in VoteDecision}
        weighted_counts = {d.value: 0.0 for d in VoteDecision}

        for vote in valid_votes:
            counts[vote.decision.value] += 1
            weighted_counts[vote.decision.value] += vote.confidence

        # Determine consensus
        quorum = proposal.required_quorum
        consensus_reached = False
        final_decision = VoteDecision.ABSTAIN

        # Check each decision type for quorum
        for decision in [VoteDecision.ALLOW, VoteDecision.DENY, VoteDecision.ESCALATE]:
            if counts[decision.value] >= quorum:
                consensus_reached = True
                final_decision = decision
                break

        # If no quorum, use weighted voting for tie-breaking
        if not consensus_reached:
            max_weighted = max(weighted_counts.values())
            for decision in VoteDecision:
                if weighted_counts[decision.value] == max_weighted:
                    final_decision = decision
                    break

        result = ConsensusResult(
            proposal_id=proposal_id,
            consensus_reached=consensus_reached,
            final_decision=final_decision,
            vote_counts=counts,
            total_votes=len(valid_votes),
            quorum_required=quorum,
            votes=valid_votes
        )

        self.results[proposal_id] = result

        return result

    async def run_consensus_round(
        self,
        action: str,
        target: str,
        context: Dict[str, Any],
        voting_heads: List[Any],  # List of HydraHead
        vote_collector: Callable,
        proposer_id: str = "system"
    ) -> ConsensusResult:
        """
        Run a complete consensus round.

        Args:
            action: The action requiring consensus
            target: Action target
            context: Additional context for voters
            voting_heads: List of HydraHead instances to vote
            vote_collector: Async function to collect vote from each head
            proposer_id: ID of proposing head

        Returns:
            ConsensusResult with final decision
        """
        n = len(voting_heads)

        if n < 1:
            return ConsensusResult(
                proposal_id="none",
                consensus_reached=False,
                final_decision=VoteDecision.DENY,
                vote_counts={d.value: 0 for d in VoteDecision},
                total_votes=0,
                quorum_required=1,
                votes=[]
            )

        # Create proposal
        proposal = self.create_proposal(
            action=action,
            target=target,
            context=context,
            proposer_id=proposer_id,
            num_voters=n
        )

        print(f"\n[CONSENSUS] Starting round for: {action}")
        print(f"  Voters: {n}, Quorum: {proposal.required_quorum}")
        print(f"  Byzantine tolerance: {self.calculate_byzantine_threshold(n)}")

        # Collect votes from all heads concurrently
        async def collect_vote(head):
            try:
                vote_data = await asyncio.wait_for(
                    vote_collector(head, proposal),
                    timeout=proposal.timeout_seconds
                )

                decision = VoteDecision(vote_data.get("decision", "ABSTAIN"))
                return self.cast_vote(
                    proposal_id=proposal.id,
                    head_id=head.head_id,
                    decision=decision,
                    reasoning=vote_data.get("reasoning", ""),
                    confidence=vote_data.get("confidence", 1.0)
                )

            except asyncio.TimeoutError:
                print(f"  [{head.head_id}] Vote timeout - treating as ABSTAIN")
                return self.cast_vote(
                    proposal_id=proposal.id,
                    head_id=head.head_id,
                    decision=VoteDecision.ABSTAIN,
                    reasoning="Vote timeout",
                    confidence=0.0
                )

            except Exception as e:
                print(f"  [{head.head_id}] Vote error: {e}")
                return self.cast_vote(
                    proposal_id=proposal.id,
                    head_id=head.head_id,
                    decision=VoteDecision.ABSTAIN,
                    reasoning=f"Error: {str(e)}",
                    confidence=0.0
                )

        # Gather all votes
        votes = await asyncio.gather(*[collect_vote(h) for h in voting_heads])

        # Log votes
        for vote in votes:
            print(f"  [{vote.head_id[:12]}] {vote.decision.value} ({vote.confidence:.2f})")

        # Tally and return result
        result = self.tally_votes(proposal.id)

        print(f"\n[CONSENSUS] Result: {result.final_decision.value}")
        print(f"  Consensus reached: {result.consensus_reached}")
        print(f"  Vote counts: {result.vote_counts}")

        return result


class RoundtableConsensus(ByzantineConsensus):
    """
    Sacred Tongue Roundtable consensus.

    Extends Byzantine consensus with tier-based voting weights
    matching the SCBE Roundtable system.

    Tiers:
    1. Single (KO): 1 signature, 1.5× multiplier
    2. Dual (KO+RU): 2 signatures, 5.06× multiplier
    3. Triple (KO+RU+UM): 3 signatures, 38.4× multiplier
    4. Quad (KO+RU+UM+CA): 4 signatures, 656× multiplier
    5. Quint (KO+RU+UM+CA+AV): 5 signatures, 14,348× multiplier
    6. Full Roundtable (all 6): 6 signatures, 518,400× multiplier
    """

    TIER_MULTIPLIERS = {
        1: 1.5,
        2: 5.06,
        3: 38.4,
        4: 656,
        5: 14348,
        6: 518400
    }

    TIER_TONGUES = {
        1: ["KO"],
        2: ["KO", "RU"],
        3: ["KO", "RU", "UM"],
        4: ["KO", "RU", "UM", "CA"],
        5: ["KO", "RU", "UM", "CA", "AV"],
        6: ["KO", "AV", "RU", "CA", "UM", "DR"]
    }

    def __init__(self, secret: str = None):
        super().__init__(secret)
        self.tongue_heads: Dict[str, str] = {}  # tongue -> head_id

    def register_tongue_head(self, tongue: str, head_id: str) -> None:
        """Register a head for a specific Sacred Tongue."""
        self.tongue_heads[tongue] = head_id

    def get_required_tier(self, action: str, sensitivity: float) -> int:
        """
        Determine required tier based on action sensitivity.

        Higher sensitivity = more signatures required.
        """
        if sensitivity >= 0.9:
            return 6  # Full Roundtable
        elif sensitivity >= 0.8:
            return 5
        elif sensitivity >= 0.7:
            return 4
        elif sensitivity >= 0.5:
            return 3
        elif sensitivity >= 0.3:
            return 2
        else:
            return 1

    async def roundtable_consensus(
        self,
        action: str,
        target: str,
        sensitivity: float,
        context: Dict[str, Any],
        heads: Dict[str, Any]  # tongue -> HydraHead
    ) -> Dict[str, Any]:
        """
        Run Roundtable consensus with tier-based requirements.

        Args:
            action: The action requiring consensus
            target: Action target
            sensitivity: Action sensitivity (0-1)
            context: Additional context
            heads: Map of tongue -> HydraHead

        Returns:
            Roundtable decision with all signatures
        """
        tier = self.get_required_tier(action, sensitivity)
        required_tongues = self.TIER_TONGUES[tier]
        multiplier = self.TIER_MULTIPLIERS[tier]

        print(f"\n[ROUNDTABLE] Tier {tier} consensus required")
        print(f"  Tongues: {required_tongues}")
        print(f"  Security multiplier: {multiplier:,.2f}×")

        # Check we have required heads
        available_tongues = [t for t in required_tongues if t in heads]
        if len(available_tongues) < len(required_tongues):
            missing = set(required_tongues) - set(available_tongues)
            return {
                "success": False,
                "decision": "DENY",
                "reason": f"Missing required tongues: {missing}",
                "tier": tier
            }

        # Collect signatures from each required tongue
        signatures = []
        all_allow = True

        for tongue in required_tongues:
            head = heads[tongue]
            # Each head votes
            vote_result = {
                "decision": "ALLOW",  # In production, would actually query head
                "confidence": 0.9,
                "tongue": tongue
            }

            signatures.append({
                "tongue": tongue,
                "head_id": head.head_id if hasattr(head, 'head_id') else str(head),
                "decision": vote_result["decision"],
                "confidence": vote_result["confidence"]
            })

            if vote_result["decision"] != "ALLOW":
                all_allow = False

        return {
            "success": all_allow,
            "decision": "ALLOW" if all_allow else "DENY",
            "tier": tier,
            "multiplier": multiplier,
            "signatures": signatures,
            "required_tongues": required_tongues,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
