"""
Swarm Consensus Timing
======================
Timing and coordination primitives for AI drone fleets.
Supports 100-1000+ agents with Byzantine fault tolerance.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
from .constants import (
    MARS_FREQUENCY_HZ,
    MARS_TICK_MS,
    BYZANTINE_ROUNDS,
    MAX_NETWORK_LATENCY_MS,
)


@dataclass
class SwarmConfig:
    """Configuration for a drone swarm."""
    n_agents: int  # Total number of agents
    max_faulty: int  # Maximum Byzantine faulty agents (must be < n/3)
    tick_hz: float = MARS_FREQUENCY_HZ  # Coordination frequency
    latency_ms: float = MAX_NETWORK_LATENCY_MS  # Network latency


def byzantine_threshold(n: int) -> int:
    """
    Calculate maximum Byzantine faulty agents.

    For BFT consensus: f < n/3
    This means we can tolerate f faulty agents out of n total.

    Args:
        n: Total number of agents

    Returns:
        Maximum number of faulty agents (f)
    """
    return (n - 1) // 3


def byzantine_rounds(n: int, f: Optional[int] = None) -> int:
    """
    Calculate rounds needed for Byzantine consensus.

    PBFT (Practical BFT) uses 3 message phases regardless of n:
    1. Pre-prepare
    2. Prepare
    3. Commit

    Args:
        n: Total number of agents
        f: Faulty agents (unused in PBFT, kept for API compatibility)

    Returns:
        Number of message rounds (always 3 for PBFT)
    """
    # PBFT always needs exactly 3 phases
    return BYZANTINE_ROUNDS


def swarm_consensus_time(
    n_agents: int,
    network_latency_ms: float = MAX_NETWORK_LATENCY_MS,
    tick_hz: float = MARS_FREQUENCY_HZ
) -> float:
    """
    Calculate time to reach consensus in a swarm.

    Args:
        n_agents: Number of agents in swarm
        network_latency_ms: Worst-case network delay
        tick_hz: Coordination tick frequency

    Returns:
        Consensus time in milliseconds
    """
    rounds = byzantine_rounds(n_agents)
    tick_ms = 1000.0 / tick_hz

    # Each round = tick + propagation
    round_time = tick_ms + network_latency_ms

    return rounds * round_time


def tick_synchronization(
    local_time_ms: float,
    tick_hz: float = MARS_FREQUENCY_HZ
) -> Tuple[int, float]:
    """
    Synchronize to the next tick boundary.

    Args:
        local_time_ms: Current local time in milliseconds
        tick_hz: Tick frequency

    Returns:
        (tick_number, ms_until_next_tick)
    """
    tick_ms = 1000.0 / tick_hz
    tick_number = int(local_time_ms / tick_ms)
    next_tick_ms = (tick_number + 1) * tick_ms
    wait_ms = next_tick_ms - local_time_ms

    return tick_number, wait_ms


def swarm_hierarchy_depth(n_agents: int, branching_factor: int = 8) -> int:
    """
    Calculate optimal hierarchy depth for hyperbolic embedding.

    Args:
        n_agents: Total agents
        branching_factor: Children per node

    Returns:
        Number of hierarchy levels
    """
    if n_agents <= 1:
        return 1

    depth = 1
    capacity = branching_factor

    while capacity < n_agents:
        depth += 1
        capacity += branching_factor ** depth

    return depth


@dataclass
class SwarmTopology:
    """
    Hyperbolic swarm topology.

    Commander at center (r=0), workers at periphery.
    """
    n_agents: int
    depth: int
    branching: int

    @classmethod
    def create(cls, n_agents: int, branching: int = 8) -> 'SwarmTopology':
        depth = swarm_hierarchy_depth(n_agents, branching)
        return cls(n_agents, depth, branching)

    def get_agent_position(self, agent_id: int) -> Tuple[float, float]:
        """
        Get hyperbolic coordinates (r, θ) for an agent.

        Agent 0 = commander at center.
        Higher IDs = further from center.
        """
        if agent_id == 0:
            return (0.0, 0.0)

        # Determine level and position within level
        level = 1
        offset = 1
        capacity = self.branching

        while agent_id >= offset + capacity:
            offset += capacity
            level += 1
            capacity = self.branching ** level

        # Position within level
        idx_in_level = agent_id - offset
        n_in_level = self.branching ** level

        # Radial position (further = less trusted)
        r = level / self.depth * 4.0  # Max radius = 4

        # Angular position
        theta = (2 * np.pi * idx_in_level) / n_in_level

        return (r, theta)

    def commander_ids(self) -> List[int]:
        """Get IDs of commander-level agents (level 0 and 1)."""
        return [0] + list(range(1, 1 + self.branching))

    def worker_ids(self) -> List[int]:
        """Get IDs of worker-level agents."""
        commander_count = 1 + self.branching
        return list(range(commander_count, self.n_agents))


def simulate_consensus(
    topology: SwarmTopology,
    faulty_ids: List[int] = None,
    latency_ms: float = MAX_NETWORK_LATENCY_MS
) -> dict:
    """
    Simulate Byzantine consensus in the swarm.

    Args:
        topology: Swarm topology
        faulty_ids: IDs of faulty agents
        latency_ms: Network latency

    Returns:
        Simulation results
    """
    if faulty_ids is None:
        faulty_ids = []

    n = topology.n_agents
    f = len(faulty_ids)
    max_f = byzantine_threshold(n)

    # Check if consensus is possible
    can_reach_consensus = f <= max_f

    # Calculate timing
    if can_reach_consensus:
        consensus_time = swarm_consensus_time(n, latency_ms)
        rounds = byzantine_rounds(n, f)
    else:
        consensus_time = float('inf')
        rounds = -1

    return {
        'n_agents': n,
        'n_faulty': f,
        'max_faulty': max_f,
        'can_reach_consensus': can_reach_consensus,
        'consensus_time_ms': consensus_time,
        'rounds_required': rounds,
        'tick_hz': MARS_FREQUENCY_HZ,
    }
