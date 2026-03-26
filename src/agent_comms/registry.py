"""
Agent Registry
==============

Discovery and registration service for AI agents.
Tracks agent capabilities, trust scores, and online status.

@module agent_comms/registry
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    name: str
    role: str = "worker"
    # Capabilities this agent offers
    capabilities: List[str] = field(default_factory=list)
    # Tongues this agent speaks
    tongues: List[str] = field(default_factory=lambda: ["KO"])
    # Trust score (0.0 to 1.0)
    trust_score: float = 0.5
    # Status
    online: bool = False
    last_heartbeat: float = 0.0
    registered_at: float = field(default_factory=time.time)
    # Metadata
    metadata: Dict = field(default_factory=dict)

    def is_alive(self, timeout: float = 60.0) -> bool:
        """Check if agent is alive (heartbeat within timeout)."""
        if not self.online:
            return False
        return (time.time() - self.last_heartbeat) < timeout

    def heartbeat(self):
        """Record a heartbeat."""
        self.last_heartbeat = time.time()
        self.online = True

    def disconnect(self):
        """Mark agent as offline."""
        self.online = False

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities

    def speaks_tongue(self, tongue: str) -> bool:
        """Check if agent speaks a specific tongue."""
        return tongue in self.tongues

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "tongues": self.tongues,
            "trust_score": self.trust_score,
            "online": self.online,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
            "metadata": self.metadata,
        }


class AgentRegistry:
    """
    Central registry for AI agent discovery and management.

    Agents register with their capabilities and tongues.
    Other agents can query the registry to find agents
    that match specific requirements.
    """

    def __init__(self, heartbeat_timeout: float = 60.0):
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_index: Dict[str, Set[str]] = {}
        self._tongue_index: Dict[str, Set[str]] = {}
        self.heartbeat_timeout = heartbeat_timeout

    def register(self, agent: AgentInfo) -> bool:
        """Register a new agent. Returns True if newly registered."""
        is_new = agent.agent_id not in self._agents
        self._agents[agent.agent_id] = agent
        agent.heartbeat()

        # Update capability index
        for cap in agent.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(agent.agent_id)

        # Update tongue index
        for tongue in agent.tongues:
            if tongue not in self._tongue_index:
                self._tongue_index[tongue] = set()
            self._tongue_index[tongue].add(agent.agent_id)

        return is_new

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent. Returns True if found and removed."""
        agent = self._agents.pop(agent_id, None)
        if not agent:
            return False

        # Clean up indexes
        for cap in agent.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap].discard(agent_id)

        for tongue in agent.tongues:
            if tongue in self._tongue_index:
                self._tongue_index[tongue].discard(agent_id)

        return True

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID."""
        return self._agents.get(agent_id)

    def heartbeat(self, agent_id: str) -> bool:
        """Record heartbeat for an agent. Returns False if not found."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.heartbeat()
        return True

    def find_by_capability(self, capability: str, online_only: bool = True) -> List[AgentInfo]:
        """Find agents with a specific capability."""
        agent_ids = self._capability_index.get(capability, set())
        agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]
        if online_only:
            agents = [a for a in agents if a.is_alive(self.heartbeat_timeout)]
        return agents

    def find_by_tongue(self, tongue: str, online_only: bool = True) -> List[AgentInfo]:
        """Find agents that speak a specific tongue."""
        agent_ids = self._tongue_index.get(tongue, set())
        agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]
        if online_only:
            agents = [a for a in agents if a.is_alive(self.heartbeat_timeout)]
        return agents

    def find_by_role(self, role: str, online_only: bool = True) -> List[AgentInfo]:
        """Find agents with a specific role."""
        agents = [a for a in self._agents.values() if a.role == role]
        if online_only:
            agents = [a for a in agents if a.is_alive(self.heartbeat_timeout)]
        return agents

    def find_trusted(self, min_trust: float = 0.7, online_only: bool = True) -> List[AgentInfo]:
        """Find agents above a trust threshold."""
        agents = [a for a in self._agents.values() if a.trust_score >= min_trust]
        if online_only:
            agents = [a for a in agents if a.is_alive(self.heartbeat_timeout)]
        return sorted(agents, key=lambda a: a.trust_score, reverse=True)

    def get_online_agents(self) -> List[AgentInfo]:
        """Get all online agents."""
        return [a for a in self._agents.values() if a.is_alive(self.heartbeat_timeout)]

    def get_all_agents(self) -> List[AgentInfo]:
        """Get all registered agents."""
        return list(self._agents.values())

    def prune_dead(self) -> List[str]:
        """Mark dead agents as offline. Returns list of pruned agent IDs."""
        pruned = []
        for agent in self._agents.values():
            if agent.online and not agent.is_alive(self.heartbeat_timeout):
                agent.disconnect()
                pruned.append(agent.agent_id)
        return pruned

    @property
    def agent_count(self) -> int:
        """Total registered agents."""
        return len(self._agents)

    @property
    def online_count(self) -> int:
        """Count of online agents."""
        return len(self.get_online_agents())

    def stats(self) -> Dict:
        """Get registry statistics."""
        return {
            "total_agents": self.agent_count,
            "online_agents": self.online_count,
            "capabilities": list(self._capability_index.keys()),
            "tongues": list(self._tongue_index.keys()),
        }
