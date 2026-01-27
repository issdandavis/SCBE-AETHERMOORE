"""
Agent Registry
==============

Tracks known agents and their trust levels.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class TrustLevel(Enum):
    """Trust classification levels."""
    UNKNOWN = auto()      # Never seen
    UNTRUSTED = auto()    # Known bad actor
    PROBATION = auto()    # Limited trust
    TRUSTED = auto()      # Normal operations
    VERIFIED = auto()     # Highly trusted


@dataclass
class AgentInfo:
    """Information about a known agent."""

    agent_id: str
    public_key: Optional[bytes] = None

    # Trust
    trust_level: TrustLevel = TrustLevel.UNKNOWN
    trust_score: float = 0.5  # 0.0 to 1.0

    # 6D position (for routing decisions)
    position: Tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # History
    first_seen: int = 0
    last_seen: int = 0
    message_count: int = 0
    failed_auth_count: int = 0

    # Metadata
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.first_seen == 0:
            self.first_seen = int(time.time() * 1000)
        if self.last_seen == 0:
            self.last_seen = self.first_seen

    def update_trust(self, success: bool) -> float:
        """
        Update trust score based on interaction outcome.

        Uses exponential moving average with asymmetric updates:
        - Success increases trust slowly
        - Failure decreases trust quickly
        """
        alpha_success = 0.1   # Slow increase
        alpha_failure = 0.3   # Fast decrease

        if success:
            self.trust_score = self.trust_score + alpha_success * (1.0 - self.trust_score)
            self.message_count += 1
        else:
            self.trust_score = self.trust_score - alpha_failure * self.trust_score
            self.failed_auth_count += 1

        # Update trust level based on score
        if self.trust_score < 0.2:
            self.trust_level = TrustLevel.UNTRUSTED
        elif self.trust_score < 0.4:
            self.trust_level = TrustLevel.PROBATION
        elif self.trust_score < 0.8:
            self.trust_level = TrustLevel.TRUSTED
        else:
            self.trust_level = TrustLevel.VERIFIED

        self.last_seen = int(time.time() * 1000)

        return self.trust_score

    def distance_to(self, other: "AgentInfo") -> float:
        """Compute Euclidean distance in 6D space."""
        return math.sqrt(sum(
            (a - b) ** 2
            for a, b in zip(self.position, other.position)
        ))


class AgentRegistry:
    """
    Registry of known agents.

    Provides:
    - Agent lookup by ID
    - Trust-based filtering
    - Nearest neighbor queries (for routing)
    """

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._id_by_key: Dict[bytes, str] = {}  # Public key -> agent ID

    def register(
        self,
        agent_id: str,
        public_key: Optional[bytes] = None,
        position: Optional[Tuple[float, ...]] = None,
        initial_trust: float = 0.5,
    ) -> AgentInfo:
        """Register a new agent or update existing."""

        if agent_id in self._agents:
            agent = self._agents[agent_id]
            if public_key:
                agent.public_key = public_key
            if position:
                agent.position = position
            agent.last_seen = int(time.time() * 1000)
            return agent

        agent = AgentInfo(
            agent_id=agent_id,
            public_key=public_key,
            position=position or (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            trust_score=initial_trust,
        )

        self._agents[agent_id] = agent

        if public_key:
            self._id_by_key[public_key] = agent_id

        return agent

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def get_by_key(self, public_key: bytes) -> Optional[AgentInfo]:
        """Get agent by public key."""
        agent_id = self._id_by_key.get(public_key)
        if agent_id:
            return self._agents.get(agent_id)
        return None

    def remove(self, agent_id: str) -> bool:
        """Remove agent from registry."""
        agent = self._agents.pop(agent_id, None)
        if agent and agent.public_key:
            self._id_by_key.pop(agent.public_key, None)
        return agent is not None

    def list_all(self) -> List[AgentInfo]:
        """List all agents."""
        return list(self._agents.values())

    def list_trusted(self, min_level: TrustLevel = TrustLevel.TRUSTED) -> List[AgentInfo]:
        """List agents at or above a trust level."""
        return [
            a for a in self._agents.values()
            if a.trust_level.value >= min_level.value
        ]

    def nearest_neighbors(
        self,
        position: Tuple[float, ...],
        k: int = 5,
        min_trust: TrustLevel = TrustLevel.PROBATION,
    ) -> List[AgentInfo]:
        """
        Find k nearest agents by 6D position.

        Used for routing decisions - find nearby trusted relays.
        """
        # Filter by trust
        candidates = [
            a for a in self._agents.values()
            if a.trust_level.value >= min_trust.value
        ]

        # Compute distances
        def distance(agent: AgentInfo) -> float:
            return math.sqrt(sum(
                (a - b) ** 2
                for a, b in zip(agent.position, position)
            ))

        # Sort by distance and return top k
        candidates.sort(key=distance)
        return candidates[:k]

    def decay_trust(self, decay_rate: float = 0.001) -> None:
        """
        Apply time-based trust decay to all agents.

        Agents that haven't been seen recently lose trust.
        """
        now_ms = int(time.time() * 1000)

        for agent in self._agents.values():
            # Calculate time since last seen (in hours)
            hours_since = (now_ms - agent.last_seen) / (1000 * 60 * 60)

            if hours_since > 1:
                # Decay trust
                decay = decay_rate * hours_since
                agent.trust_score = max(0.0, agent.trust_score - decay)

                # Update level
                agent.update_trust(True)  # Recalculate level without changing score

    def stats(self) -> Dict[str, int]:
        """Get registry statistics."""
        level_counts = {level.name: 0 for level in TrustLevel}

        for agent in self._agents.values():
            level_counts[agent.trust_level.name] += 1

        return {
            "total": len(self._agents),
            **level_counts,
        }
