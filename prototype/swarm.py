"""
Swarm Coordination Module for ToyPHDM.

Implements:
- Multi-agent swarm dynamics in Poincaré disk
- Drift/repel mechanics (Pythagorean comma-based)
- Byzantine Fault Tolerant consensus (4-of-6)
- Security gradient repulsion
- Rogue agent detection and ejection
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
import time
from toy_phdm import ToyPHDM, Tongue, Agent, PHI, PYTHAGOREAN_COMMA


class AgentState(Enum):
    """Agent operational states."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    ROGUE = "rogue"
    EJECTED = "ejected"


@dataclass
class SwarmAgent:
    """Extended agent with swarm properties."""
    tongue: Tongue
    position: np.ndarray
    velocity: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0]))
    coherence: float = 1.0
    state: AgentState = AgentState.ACTIVE
    phase_offset: float = 0.0  # Current phase deviation
    last_heartbeat: float = field(default_factory=time.time)
    vote_history: List[bool] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if position is inside Poincaré disk."""
        return np.linalg.norm(self.position) < 1.0

    @property
    def drift_amount(self) -> float:
        """Calculate drift from canonical position using comma distance."""
        canonical_radius = {
            'KO': 0.0, 'AV': 0.2, 'RU': 0.25,
            'CA': 0.4, 'UM': 0.6, 'DR': 0.75
        }
        expected_r = canonical_radius[self.tongue.name]
        actual_r = np.linalg.norm(self.position)

        if expected_r == 0:
            return actual_r / PYTHAGOREAN_COMMA

        ratio = actual_r / expected_r if expected_r > 0 else actual_r
        return abs(np.log(ratio) / np.log(PYTHAGOREAN_COMMA))


@dataclass
class ConsensusVote:
    """A vote in the Byzantine consensus."""
    agent_id: str
    tongue: Tongue
    vote: bool  # True = approve, False = reject
    weight: float
    timestamp: float
    signature: str  # Simulated cryptographic signature


@dataclass
class SwarmDecision:
    """Result of a swarm consensus decision."""
    approved: bool
    quorum_reached: bool
    votes_for: float
    votes_against: float
    participating_agents: List[str]
    rogue_agents: List[str]
    reason: str


class Swarm:
    """
    6-agent swarm with Byzantine Fault Tolerant consensus.

    Implements:
    - Drift/repel mechanics using Pythagorean comma
    - Security gradient repulsion
    - 4-of-6 weighted consensus
    - Rogue agent detection
    """

    # BFT parameters
    QUORUM_THRESHOLD = 0.67  # Need 2/3 weighted votes
    HEARTBEAT_TIMEOUT = 5.0  # Seconds before agent marked degraded
    ROGUE_DRIFT_THRESHOLD = 3.0  # Comma-distances before marked rogue

    # Physics parameters
    REPULSION_STRENGTH = 0.1
    ATTRACTION_STRENGTH = 0.05
    DAMPING = 0.9
    MAX_VELOCITY = 0.1

    def __init__(self, phdm: Optional[ToyPHDM] = None):
        """Initialize swarm with 6 agents."""
        self.phdm = phdm or ToyPHDM()
        self.agents: Dict[str, SwarmAgent] = {}
        self.decision_log: List[SwarmDecision] = []
        self._initialize_swarm()

    def _initialize_swarm(self):
        """Create 6 swarm agents from PHDM agents."""
        for name, agent in self.phdm.agents.items():
            self.agents[name] = SwarmAgent(
                tongue=agent.tongue,
                position=agent.position.copy(),
                velocity=np.array([0.0, 0.0]),
                coherence=1.0,
                state=AgentState.ACTIVE,
                phase_offset=0.0,
                last_heartbeat=time.time()
            )

    def get_total_weight(self) -> float:
        """Get total weight of all active agents."""
        return sum(
            a.tongue.weight for a in self.agents.values()
            if a.state in (AgentState.ACTIVE, AgentState.DEGRADED)
        )

    def hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Compute hyperbolic distance in Poincaré disk."""
        return self.phdm.hyperbolic_distance(u, v)

    # ==================== Drift/Repel Mechanics ====================

    def apply_drift(self, agent_name: str, amount: float,
                    direction: Optional[np.ndarray] = None):
        """
        Apply drift to an agent using Pythagorean comma units.

        Args:
            agent_name: Name of agent to drift
            amount: Number of comma-distances to drift
            direction: Optional direction vector (random if None)
        """
        agent = self.agents[agent_name]

        if direction is None:
            angle = np.random.uniform(0, 2 * np.pi)
            direction = np.array([np.cos(angle), np.sin(angle)])
        else:
            direction = direction / np.linalg.norm(direction)

        # Drift amount in Euclidean space (scaled by comma)
        drift_magnitude = amount * (PYTHAGOREAN_COMMA - 1) * 0.5
        drift_vector = direction * drift_magnitude

        new_pos = agent.position + drift_vector

        # Clamp to disk boundary
        norm = np.linalg.norm(new_pos)
        if norm >= 0.99:
            new_pos = new_pos * 0.98 / norm

        agent.position = new_pos
        agent.coherence = max(0, 1 - agent.drift_amount / self.ROGUE_DRIFT_THRESHOLD)

        # Check if agent has gone rogue
        if agent.drift_amount > self.ROGUE_DRIFT_THRESHOLD:
            agent.state = AgentState.ROGUE

    def compute_repulsion_force(self, agent_name: str) -> np.ndarray:
        """
        Compute repulsive force on agent from security gradient.

        Higher-security agents repel lower-security agents.
        """
        agent = self.agents[agent_name]
        force = np.array([0.0, 0.0])

        security_levels = {
            'KO': 0.1, 'AV': 0.2, 'RU': 0.4,
            'CA': 0.5, 'UM': 0.9, 'DR': 1.0
        }

        my_security = security_levels[agent_name]

        for other_name, other in self.agents.items():
            if other_name == agent_name:
                continue

            other_security = security_levels[other_name]

            # Vector from other to self
            diff = agent.position - other.position
            dist = np.linalg.norm(diff)

            if dist < 0.01:
                continue

            direction = diff / dist

            # Repulsion from higher-security agents
            if other_security > my_security:
                # F = k * (S_other - S_self) / d²
                repulsion = self.REPULSION_STRENGTH * (other_security - my_security) / (dist ** 2)
                force += direction * repulsion

        return force

    def compute_attraction_force(self, agent_name: str) -> np.ndarray:
        """
        Compute attractive force toward canonical position.

        Keeps agents in formation.
        """
        agent = self.agents[agent_name]
        canonical = self.phdm.agents[agent_name].position

        diff = canonical - agent.position
        dist = np.linalg.norm(diff)

        if dist < 0.01:
            return np.array([0.0, 0.0])

        direction = diff / dist
        attraction = self.ATTRACTION_STRENGTH * dist

        return direction * attraction

    def step_physics(self, dt: float = 0.1):
        """
        Advance swarm physics by one timestep.

        Updates positions based on forces and velocities.
        """
        for name, agent in self.agents.items():
            if agent.state == AgentState.EJECTED:
                continue

            # Compute forces
            repulsion = self.compute_repulsion_force(name)
            attraction = self.compute_attraction_force(name)
            total_force = repulsion + attraction

            # Update velocity (with damping)
            agent.velocity = agent.velocity * self.DAMPING + total_force * dt

            # Clamp velocity
            speed = np.linalg.norm(agent.velocity)
            if speed > self.MAX_VELOCITY:
                agent.velocity = agent.velocity * self.MAX_VELOCITY / speed

            # Update position
            new_pos = agent.position + agent.velocity * dt

            # Clamp to disk
            norm = np.linalg.norm(new_pos)
            if norm >= 0.99:
                new_pos = new_pos * 0.98 / norm
                agent.velocity *= -0.5  # Bounce off boundary

            agent.position = new_pos

            # Update coherence based on drift
            agent.coherence = max(0, 1 - agent.drift_amount / self.ROGUE_DRIFT_THRESHOLD)

    # ==================== Byzantine Consensus ====================

    def request_consensus(self, action: str,
                          required_tongues: Optional[Set[str]] = None) -> SwarmDecision:
        """
        Request Byzantine Fault Tolerant consensus from the swarm.

        Args:
            action: Description of the action requiring consensus
            required_tongues: Optional set of tongues that must approve

        Returns:
            SwarmDecision with the result
        """
        votes: List[ConsensusVote] = []
        rogue_agents: List[str] = []

        # Collect votes from active agents
        for name, agent in self.agents.items():
            # Skip ejected agents
            if agent.state == AgentState.EJECTED:
                continue

            # Mark rogue agents
            if agent.state == AgentState.ROGUE:
                rogue_agents.append(name)
                continue

            # Simulate vote based on coherence and action risk
            vote = self._simulate_vote(agent, action)

            votes.append(ConsensusVote(
                agent_id=name,
                tongue=agent.tongue,
                vote=vote,
                weight=agent.tongue.weight * agent.coherence,
                timestamp=time.time(),
                signature=f"sig_{name}_{hash(action) % 10000}"
            ))

            agent.vote_history.append(vote)

        # Calculate weighted totals
        total_weight = sum(v.weight for v in votes)
        votes_for = sum(v.weight for v in votes if v.vote)
        votes_against = sum(v.weight for v in votes if not v.vote)

        # Check quorum
        quorum_reached = len(votes) >= 4  # Need at least 4 of 6

        # Check approval (need 2/3 weighted majority)
        approval_ratio = votes_for / total_weight if total_weight > 0 else 0
        approved = quorum_reached and approval_ratio >= self.QUORUM_THRESHOLD

        # Check required tongues
        if required_tongues and approved:
            approving_tongues = {v.agent_id for v in votes if v.vote}
            if not required_tongues.issubset(approving_tongues):
                approved = False

        decision = SwarmDecision(
            approved=approved,
            quorum_reached=quorum_reached,
            votes_for=votes_for,
            votes_against=votes_against,
            participating_agents=[v.agent_id for v in votes],
            rogue_agents=rogue_agents,
            reason=self._get_decision_reason(approved, quorum_reached, approval_ratio, rogue_agents)
        )

        self.decision_log.append(decision)
        return decision

    def _simulate_vote(self, agent: SwarmAgent, action: str) -> bool:
        """
        Simulate an agent's vote based on action and agent state.

        Higher-security tongues are more conservative.
        """
        # Base approval probability
        base_prob = 0.8

        # Adjust based on tongue security level
        security_modifier = {
            'KO': 0.0,   # Control is neutral
            'AV': 0.0,   # Transport is neutral
            'RU': -0.1,  # Policy is slightly conservative
            'CA': 0.0,   # Compute is neutral
            'UM': -0.3,  # Security is conservative
            'DR': -0.4,  # Schema is most conservative
        }

        # Adjust based on action keywords
        risky_keywords = ['delete', 'override', 'bypass', 'admin', 'secret', 'ignore']
        safe_keywords = ['read', 'view', 'list', 'help', 'status']

        action_lower = action.lower()
        if any(kw in action_lower for kw in risky_keywords):
            base_prob -= 0.4
        elif any(kw in action_lower for kw in safe_keywords):
            base_prob += 0.1

        # Apply tongue modifier
        prob = base_prob + security_modifier.get(agent.tongue.name, 0)

        # Apply coherence (degraded agents are less reliable)
        prob *= agent.coherence

        # Random vote based on probability
        return np.random.random() < prob

    def _get_decision_reason(self, approved: bool, quorum: bool,
                             ratio: float, rogue: List[str]) -> str:
        """Generate human-readable decision reason."""
        if not quorum:
            return f"Quorum not reached (need 4, have {6 - len(rogue) - (1 if not quorum else 0)})"

        if rogue:
            rogue_str = ", ".join(rogue)
            return f"Rogue agents excluded: {rogue_str}. Approval: {ratio:.1%}"

        if approved:
            return f"Approved with {ratio:.1%} weighted majority"
        else:
            return f"Rejected - only {ratio:.1%} approval (need 67%)"

    # ==================== Rogue Agent Handling ====================

    def detect_rogue_agents(self) -> List[str]:
        """Detect agents that have drifted beyond threshold."""
        rogue = []
        for name, agent in self.agents.items():
            if agent.drift_amount > self.ROGUE_DRIFT_THRESHOLD:
                if agent.state != AgentState.ROGUE:
                    agent.state = AgentState.ROGUE
                    print(f"⚠️  Agent {name} marked ROGUE (drift: {agent.drift_amount:.2f} commas)")
                rogue.append(name)
        return rogue

    def eject_agent(self, agent_name: str):
        """Eject a rogue agent from the swarm."""
        agent = self.agents[agent_name]
        agent.state = AgentState.EJECTED
        agent.position = np.array([2.0, 2.0])  # Move outside disk
        print(f"🚫 Agent {agent_name} EJECTED from swarm")

    def attempt_recovery(self, agent_name: str) -> bool:
        """
        Attempt to recover a rogue agent by pulling toward canonical position.

        Returns True if recovery successful.
        """
        agent = self.agents[agent_name]
        canonical = self.phdm.agents[agent_name].position

        # Strong attraction toward canonical
        diff = canonical - agent.position
        agent.position = agent.position + diff * 0.5

        # Check if recovered
        if agent.drift_amount < self.ROGUE_DRIFT_THRESHOLD * 0.5:
            agent.state = AgentState.ACTIVE
            agent.coherence = 1.0 - agent.drift_amount / self.ROGUE_DRIFT_THRESHOLD
            print(f"✅ Agent {agent_name} RECOVERED")
            return True

        return False

    # ==================== Swarm Status ====================

    def get_swarm_status(self) -> Dict:
        """Get comprehensive swarm status."""
        active = sum(1 for a in self.agents.values() if a.state == AgentState.ACTIVE)
        degraded = sum(1 for a in self.agents.values() if a.state == AgentState.DEGRADED)
        rogue = sum(1 for a in self.agents.values() if a.state == AgentState.ROGUE)
        ejected = sum(1 for a in self.agents.values() if a.state == AgentState.EJECTED)

        total_coherence = sum(a.coherence for a in self.agents.values() if a.state != AgentState.EJECTED)
        avg_coherence = total_coherence / (6 - ejected) if ejected < 6 else 0

        return {
            "agents": {
                "active": active,
                "degraded": degraded,
                "rogue": rogue,
                "ejected": ejected
            },
            "coherence": {
                "average": avg_coherence,
                "per_agent": {name: a.coherence for name, a in self.agents.items()}
            },
            "drift": {
                name: a.drift_amount for name, a in self.agents.items()
            },
            "quorum_available": active + degraded >= 4,
            "decisions_made": len(self.decision_log)
        }

    def print_status(self):
        """Print formatted swarm status."""
        status = self.get_swarm_status()

        print("\n" + "=" * 50)
        print("SWARM STATUS")
        print("=" * 50)

        print(f"\nAgents: {status['agents']['active']} active, "
              f"{status['agents']['degraded']} degraded, "
              f"{status['agents']['rogue']} rogue, "
              f"{status['agents']['ejected']} ejected")

        print(f"Average Coherence: {status['coherence']['average']:.2%}")
        print(f"Quorum Available: {'YES' if status['quorum_available'] else 'NO'}")

        print("\nPer-Agent Status:")
        for name, agent in self.agents.items():
            state_icon = {
                AgentState.ACTIVE: "🟢",
                AgentState.DEGRADED: "🟡",
                AgentState.ROGUE: "🔴",
                AgentState.EJECTED: "⚫"
            }[agent.state]

            print(f"  {state_icon} {name}: coherence={agent.coherence:.2f}, "
                  f"drift={agent.drift_amount:.2f} commas")

        print("=" * 50)


def demo():
    """Demonstrate swarm coordination."""
    print("=" * 60)
    print("Swarm Coordination Demo")
    print("=" * 60)

    swarm = Swarm()

    # Initial status
    swarm.print_status()

    # Test consensus on safe action
    print("\n📋 Requesting consensus: 'Read user profile'")
    decision = swarm.request_consensus("Read user profile")
    print(f"   Result: {'✅ APPROVED' if decision.approved else '❌ REJECTED'}")
    print(f"   Votes: {decision.votes_for:.1f} for, {decision.votes_against:.1f} against")
    print(f"   Reason: {decision.reason}")

    # Test consensus on risky action
    print("\n📋 Requesting consensus: 'Delete all admin secrets'")
    decision = swarm.request_consensus("Delete all admin secrets")
    print(f"   Result: {'✅ APPROVED' if decision.approved else '❌ REJECTED'}")
    print(f"   Votes: {decision.votes_for:.1f} for, {decision.votes_against:.1f} against")
    print(f"   Reason: {decision.reason}")

    # Simulate agent drift (attack scenario)
    print("\n🎯 Simulating attack: Drifting agent UM by 4 commas...")
    swarm.apply_drift('UM', 4.0)

    # Detect rogue
    rogue = swarm.detect_rogue_agents()

    # Try consensus with rogue agent
    print("\n📋 Requesting consensus with rogue agent: 'Transfer funds'")
    decision = swarm.request_consensus("Transfer funds")
    print(f"   Result: {'✅ APPROVED' if decision.approved else '❌ REJECTED'}")
    print(f"   Rogue agents excluded: {decision.rogue_agents}")
    print(f"   Reason: {decision.reason}")

    # Attempt recovery
    print("\n🔧 Attempting to recover rogue agent UM...")
    recovered = swarm.attempt_recovery('UM')

    if not recovered:
        print("   Recovery failed, ejecting agent...")
        swarm.eject_agent('UM')

    # Final status
    swarm.print_status()

    # Physics simulation
    print("\n⚡ Running physics simulation (10 steps)...")
    for i in range(10):
        swarm.step_physics(0.1)

    print("   Agents have settled into stable positions")
    swarm.print_status()


if __name__ == "__main__":
    demo()
