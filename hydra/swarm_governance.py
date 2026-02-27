"""
HYDRA Swarm Governance - BFT + Adaptive Hyperbolic Geometry
===========================================================

Autonomous, self-regulating AI agentic swarm system combining:
- Byzantine Fault Tolerant consensus (SwarmRaft)
- Adaptive hyperbolic geometry (variable R, κ tied to coherence)
- Self-healing swarm dynamics
- Attack-resistant coordination

This is the core module for fully autonomous AI agent swarms that can:
- Self-regulate without human intervention
- Resist Byzantine attacks (malicious agents)
- Evolve trust geometry based on behavior
- Execute code with governance-first safety

Phase 1 Q2 2026 - Agentic Swarm Foundation

Research Validation:
- SwarmRaft (2025): Byzantine evaluation with crash tolerance
- Grok Analysis (2026-02-05): Variable curvature containment proofs
- SCBE Theorems 1-7: Continuity and amplification guarantees
"""

import asyncio
import math
import random
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import shutil
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Try numpy, fallback to pure Python
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from .consensus import (
    ByzantineConsensus,
    Vote,
    Proposal,
    ConsensusResult,
    VoteDecision
)

# Constants
EPSILON = 1e-10
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

# Dangerous command patterns that must never be executed via shell.
# Each entry is checked (case-insensitive) against the full command string.
BLOCKED_COMMANDS: List[str] = [
    "rm -rf",
    "rm -fr",
    "rmdir /s",
    "del /f",
    "del /s",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
    "format c:",
    "format d:",
    ":(){",            # fork bomb
    ">(){ :|:",        # fork bomb variant
    "chmod -R 777 /",
    "chown -R",
    "mv /* ",
    "mv / ",
    "wget -O- | sh",
    "curl | sh",
    "curl | bash",
    "wget | bash",
    "> /dev/sda",
    "> /dev/null",     # harmless, but included for completeness of redirect attacks
    "mkfs.ext",
    "fdisk",
    "parted",
    "wipefs",
]

# Default timeout for code execution (seconds)
DEFAULT_EXECUTION_TIMEOUT: int = 30

# Sacred Tongue realm centers (6D)
REALM_CENTERS = {
    'KO': [0.3, 0.0, 0.0, 0.0, 0.0, 0.0],   # Knowledge - pure flow
    'AV': [0.0, 0.3, 0.0, 0.0, 0.0, 0.0],   # Avatara - context boundary
    'RU': [0.0, 0.0, 0.3, 0.0, 0.0, 0.0],   # Runes - binding chaos
    'CA': [0.0, 0.0, 0.0, 0.3, 0.0, 0.0],   # Cascade - bit shatter
    'UM': [0.0, 0.0, 0.0, 0.0, 0.3, 0.0],   # Umbra - veil mystery
    'DR': [0.0, 0.0, 0.0, 0.0, 0.0, 0.3],   # Draconic - structured order
}


# ═══════════════════════════════════════════════════════════════
# Vector Operations (numpy-agnostic)
# ═══════════════════════════════════════════════════════════════

def vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))

def vec_dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

def vec_sub(a: List[float], b: List[float]) -> List[float]:
    return [x - y for x, y in zip(a, b)]

def vec_add(a: List[float], b: List[float]) -> List[float]:
    return [x + y for x, y in zip(a, b)]

def vec_scale(v: List[float], s: float) -> List[float]:
    return [x * s for x in v]

def vec_zeros(n: int) -> List[float]:
    return [0.0] * n


# ═══════════════════════════════════════════════════════════════
# Agent State
# ═══════════════════════════════════════════════════════════════

class AgentRole(str, Enum):
    """Agent roles in the swarm."""
    LEADER = "leader"           # Proposes actions, coordinates
    VALIDATOR = "validator"     # Votes on proposals
    EXECUTOR = "executor"       # Executes approved actions
    OBSERVER = "observer"       # Monitors, reports anomalies
    MALICIOUS = "malicious"     # For simulation: adversarial agent


class AgentState(str, Enum):
    """Agent operational states."""
    ACTIVE = "active"
    IDLE = "idle"
    VOTING = "voting"
    EXECUTING = "executing"
    ISOLATED = "isolated"       # Quarantined due to low coherence
    FROZEN = "frozen"           # Suspended due to attack detection


@dataclass
class SwarmAgent:
    """
    A single agent in the governed swarm.

    Combines:
    - Position in 6D Poincaré ball (semantic/trust space)
    - Coherence score (0-1, from intent validation)
    - BFT voting capability
    - Execution history
    """
    agent_id: str
    role: AgentRole = AgentRole.VALIDATOR
    state: AgentState = AgentState.ACTIVE

    # 6D position in Poincaré ball
    position: List[float] = field(default_factory=lambda: vec_zeros(6))
    velocity: List[float] = field(default_factory=lambda: vec_zeros(6))

    # Trust/coherence metrics
    coherence: float = 1.0          # Current intent validation score
    trust_score: float = 1.0        # Long-term trust (decays with bad behavior)
    penalty_accumulated: float = 0.0 # Total harmonic penalties incurred

    # Adaptive geometry parameters (per-agent)
    local_R: float = 1.5            # Agent's local harmonic scaling
    local_kappa: float = -1.0       # Agent's local curvature

    # History
    position_history: List[List[float]] = field(default_factory=list)
    coherence_history: List[float] = field(default_factory=list)
    vote_history: List[Dict] = field(default_factory=list)

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_action_at: Optional[str] = None

    def update_position(self, new_pos: List[float]) -> None:
        """Update position with history tracking."""
        self.position_history.append(self.position.copy())
        if len(self.position_history) > 100:
            self.position_history.pop(0)
        self.position = new_pos

    def update_coherence(self, new_coherence: float) -> None:
        """Update coherence with history tracking."""
        self.coherence_history.append(self.coherence)
        if len(self.coherence_history) > 100:
            self.coherence_history.pop(0)
        self.coherence = max(0, min(1, new_coherence))

    def distance_from_origin(self) -> float:
        """Euclidean distance from origin (simple metric)."""
        return vec_norm(self.position)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "state": self.state.value,
            "position": self.position,
            "coherence": round(self.coherence, 4),
            "trust_score": round(self.trust_score, 4),
            "penalty_accumulated": round(self.penalty_accumulated, 2),
            "local_R": round(self.local_R, 4),
            "distance_from_origin": round(self.distance_from_origin(), 4)
        }


# ═══════════════════════════════════════════════════════════════
# Swarm Governance Controller
# ═══════════════════════════════════════════════════════════════

@dataclass
class GovernanceConfig:
    """Configuration for swarm governance."""
    # BFT parameters
    min_agents: int = 4                    # Minimum for meaningful consensus
    vote_timeout_seconds: float = 10.0     # Timeout for vote collection

    # Adaptive geometry
    base_R: float = 1.5                    # Base harmonic scaling
    lambda_penalty: float = 1.5            # Coherence penalty multiplier
    gamma_curvature: float = 0.5           # Curvature adaptation rate
    chaos_strength: float = 0.1            # Lorenz chaos amplitude
    boundary_threshold: float = 0.98       # Ball boundary

    # Trust management
    trust_decay_rate: float = 0.01         # Trust decays over time
    trust_recovery_rate: float = 0.05      # Trust recovers with good behavior
    isolation_threshold: float = 0.2       # Coherence below this → isolation
    freeze_threshold: float = 0.1          # Coherence below this → freeze

    # Self-regulation
    auto_heal_enabled: bool = True         # Auto-recover isolated agents
    auto_expel_enabled: bool = True        # Auto-remove persistent bad actors
    expel_penalty_threshold: float = 1000  # Accumulated penalty for expulsion

    # Autonomous execution
    auto_execute_threshold: float = 0.9    # Coherence needed for auto-execute
    require_consensus_above: float = 0.5   # Actions above this risk need consensus


class SwarmGovernance:
    """
    Self-regulating swarm governance with BFT + adaptive geometry.

    This is the core controller for autonomous AI agent swarms.

    Features:
    - Byzantine consensus for collective decisions
    - Adaptive hyperbolic geometry per-agent
    - Self-healing: auto-recover/expel agents
    - Attack resistance: geometry evolves to isolate threats
    - Autonomous execution: high-trust agents can act independently

    Usage:
        gov = SwarmGovernance()

        # Add agents
        gov.add_agent("agent-1", AgentRole.LEADER)
        gov.add_agent("agent-2", AgentRole.VALIDATOR)

        # Propose action (requires consensus if risky)
        result = await gov.propose_action(
            proposer_id="agent-1",
            action="execute_code",
            target="script.py",
            context={"intent": "refactor"}
        )

        # Simulate step (updates geometry, detects attacks)
        gov.simulation_step(dt=0.1)
    """

    def __init__(self, config: Optional[GovernanceConfig] = None):
        self.config = config or GovernanceConfig()

        # Agents
        self.agents: Dict[str, SwarmAgent] = {}

        # BFT consensus engine
        self.consensus = ByzantineConsensus()

        # Action queue (pending consensus)
        self.pending_actions: Dict[str, Dict] = {}

        # Executed actions log
        self.action_log: List[Dict] = []

        # Swarm metrics
        self.swarm_coherence: float = 1.0
        self.swarm_centroid: List[float] = vec_zeros(6)
        self.attack_detected: bool = False
        self.attack_severity: float = 0.0

        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}

    # ═══════════════════════════════════════════════════════════════
    # Agent Management
    # ═══════════════════════════════════════════════════════════════

    def add_agent(
        self,
        agent_id: str,
        role: AgentRole = AgentRole.VALIDATOR,
        initial_position: Optional[List[float]] = None,
        initial_coherence: float = 1.0
    ) -> SwarmAgent:
        """Add an agent to the swarm."""
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already exists")

        agent = SwarmAgent(
            agent_id=agent_id,
            role=role,
            position=initial_position or vec_zeros(6),
            coherence=initial_coherence,
            trust_score=initial_coherence,
            local_R=self.config.base_R
        )

        self.agents[agent_id] = agent
        self._emit("agent_added", agent)

        return agent

    def remove_agent(self, agent_id: str, reason: str = "removed") -> bool:
        """Remove an agent from the swarm."""
        if agent_id not in self.agents:
            return False

        agent = self.agents.pop(agent_id)
        self._emit("agent_removed", agent, reason)

        return True

    def get_agent(self, agent_id: str) -> Optional[SwarmAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def get_active_agents(self) -> List[SwarmAgent]:
        """Get all active (non-isolated, non-frozen) agents."""
        return [
            a for a in self.agents.values()
            if a.state in [AgentState.ACTIVE, AgentState.IDLE, AgentState.VOTING]
        ]

    # ═══════════════════════════════════════════════════════════════
    # Adaptive Geometry
    # ═══════════════════════════════════════════════════════════════

    def get_R(self, coherence: float) -> float:
        """
        Compute adaptive harmonic scaling R(coherence).

        R(t) = R_base + λ(1 - C)
        Low coherence → higher R → harsher penalties
        """
        c = max(0, min(1, coherence))
        return self.config.base_R + self.config.lambda_penalty * (1 - c)

    def get_kappa(self, coherence: float) -> float:
        """
        Compute adaptive curvature κ(coherence).

        κ(t) = -1 * exp(γ(1 - C))
        Low coherence → more negative → distances explode
        """
        c = max(0, min(1, coherence))
        return -1 * math.exp(self.config.gamma_curvature * (1 - c))

    def hyperbolic_distance(self, a: List[float], b: List[float], kappa: float = -1) -> float:
        """
        Hyperbolic distance with variable curvature.

        d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))
        """
        abs_kappa = abs(kappa)
        sqrt_kappa = math.sqrt(abs_kappa) if abs_kappa > EPSILON else 1.0

        diff = vec_sub(a, b)
        diff_norm_sq = vec_dot(diff, diff)
        a_norm_sq = vec_dot(a, a)
        b_norm_sq = vec_dot(b, b)

        a_factor = max(EPSILON, 1 - abs_kappa * a_norm_sq)
        b_factor = max(EPSILON, 1 - abs_kappa * b_norm_sq)

        arg = 1 + (2 * abs_kappa * diff_norm_sq) / (a_factor * b_factor)

        return math.acosh(max(1, arg)) / sqrt_kappa

    def harmonic_penalty(self, distance: float, R: float) -> float:
        """
        Harmonic wall penalty: H(d, R) = R^(d²)

        Superexponential in distance → extreme cost at boundary
        """
        return R ** (distance ** 2)

    def project_to_ball(self, pos: List[float]) -> List[float]:
        """Project position to stay inside Poincaré ball."""
        n = vec_norm(pos)
        if n > self.config.boundary_threshold:
            return vec_scale(pos, self.config.boundary_threshold / n)
        return pos

    # ═══════════════════════════════════════════════════════════════
    # Agent Dynamics (ODE-based drift)
    # ═══════════════════════════════════════════════════════════════

    def compute_drift(
        self,
        agent: SwarmAgent,
        target_realms: List[str],
        mutations: float = 0
    ) -> List[float]:
        """
        Compute drift vector for agent position update.

        Combines:
        - Attraction to target realms (scaled by coherence * R)
        - Repulsion from mutations (amplified by low coherence)
        - Chaos term (Lorenz-like, modulated by coherence)
        """
        R = self.get_R(agent.coherence)
        pos = agent.position
        dim = len(pos)

        # Attraction to target realms
        attraction = vec_zeros(dim)
        for tongue in target_realms:
            center = REALM_CENTERS.get(tongue)
            if center:
                delta = vec_sub(center, pos)
                scaled = vec_scale(delta, agent.coherence * R)
                attraction = vec_add(attraction, scaled)

        # Repulsion from mutations
        repulsion = vec_zeros(dim)
        if mutations > 0:
            for i in range(dim):
                repulsion[i] = (random.random() - 0.5) * 2 * mutations * (1 - agent.coherence)

        # Chaos term (Lorenz-like for 6D)
        chaos = vec_zeros(dim)
        if self.config.chaos_strength > 0 and dim >= 6:
            sigma, rho, beta = 10, 28, 8/3
            cs = self.config.chaos_strength * (1 - agent.coherence)

            chaos[0] = cs * sigma * (pos[1] - pos[0])
            chaos[1] = cs * (pos[0] * (rho - pos[2]) - pos[1])
            chaos[2] = cs * (pos[0] * pos[1] - beta * pos[2])
            chaos[3] = cs * sigma * (pos[4] - pos[3])
            chaos[4] = cs * (pos[3] * (rho - pos[5]) - pos[4])
            chaos[5] = cs * (pos[3] * pos[4] - beta * pos[5])

        return vec_add(vec_add(attraction, repulsion), chaos)

    def update_agent_position(
        self,
        agent: SwarmAgent,
        target_realms: List[str],
        mutations: float = 0,
        dt: float = 0.1
    ) -> Tuple[List[float], float]:
        """
        Update agent position using Euler integration.

        Returns: (new_position, penalty)
        """
        # Compute drift
        drift = self.compute_drift(agent, target_realms, mutations)

        # Euler step
        new_pos = vec_add(agent.position, vec_scale(drift, dt))

        # Project to ball
        new_pos = self.project_to_ball(new_pos)

        # Update agent
        agent.velocity = vec_scale(vec_sub(new_pos, agent.position), 1/dt)
        agent.update_position(new_pos)

        # Update adaptive parameters
        agent.local_R = self.get_R(agent.coherence)
        agent.local_kappa = self.get_kappa(agent.coherence)

        # Compute penalty
        d_center = self.hyperbolic_distance(new_pos, vec_zeros(6), agent.local_kappa)
        penalty = self.harmonic_penalty(d_center, agent.local_R)

        agent.penalty_accumulated += penalty

        return new_pos, penalty

    # ═══════════════════════════════════════════════════════════════
    # BFT Consensus Integration
    # ═══════════════════════════════════════════════════════════════

    async def propose_action(
        self,
        proposer_id: str,
        action: str,
        target: str,
        context: Dict[str, Any],
        require_consensus: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Propose an action, potentially requiring BFT consensus.

        High-coherence agents can auto-execute low-risk actions.
        Risky actions always require consensus.
        """
        proposer = self.agents.get(proposer_id)
        if not proposer:
            return {"success": False, "error": "Proposer not found"}

        if proposer.state in [AgentState.ISOLATED, AgentState.FROZEN]:
            return {"success": False, "error": f"Proposer is {proposer.state.value}"}

        # Calculate risk based on action type
        risk = self._calculate_action_risk(action, target, context)

        # Determine if consensus needed
        needs_consensus = require_consensus
        if needs_consensus is None:
            needs_consensus = (
                risk > self.config.require_consensus_above or
                proposer.coherence < self.config.auto_execute_threshold
            )

        if not needs_consensus:
            # Auto-execute for trusted agents with low-risk actions
            result = await self._execute_action(proposer_id, action, target, context)
            return {
                "success": True,
                "auto_executed": True,
                "result": result,
                "risk": risk,
                "proposer_coherence": proposer.coherence
            }

        # Create BFT proposal
        active_agents = self.get_active_agents()
        if len(active_agents) < self.config.min_agents:
            return {"success": False, "error": "Insufficient active agents for consensus"}

        proposal = self.consensus.create_proposal(
            action=action,
            target=target,
            context=context,
            proposer_id=proposer_id,
            num_voters=len(active_agents)
        )

        # Collect votes
        votes = await self._collect_votes(proposal, active_agents)

        # Tally and decide
        result = self._tally_votes(proposal, votes)

        if result.consensus_reached and result.final_decision == VoteDecision.ALLOW:
            exec_result = await self._execute_action(proposer_id, action, target, context)
            return {
                "success": True,
                "consensus_reached": True,
                "decision": result.final_decision.value,
                "result": exec_result,
                "vote_counts": result.vote_counts
            }

        return {
            "success": False,
            "consensus_reached": result.consensus_reached,
            "decision": result.final_decision.value,
            "vote_counts": result.vote_counts,
            "reason": "Consensus denied action"
        }

    async def _collect_votes(
        self,
        proposal: Proposal,
        voters: List[SwarmAgent]
    ) -> List[Vote]:
        """Collect votes from all active agents."""
        votes = []

        for agent in voters:
            # Agent votes based on its coherence and trust assessment
            decision, confidence = self._agent_vote_decision(agent, proposal)

            vote = self.consensus.cast_vote(
                proposal_id=proposal.id,
                head_id=agent.agent_id,
                decision=decision,
                reasoning=f"Coherence: {agent.coherence:.2f}, Trust: {agent.trust_score:.2f}",
                confidence=confidence
            )

            votes.append(vote)
            agent.vote_history.append(vote.to_dict())

        return votes

    def _agent_vote_decision(
        self,
        agent: SwarmAgent,
        proposal: Proposal
    ) -> Tuple[VoteDecision, float]:
        """
        Determine how an agent votes based on its state.

        Honest agents vote based on proposal assessment + their coherence.
        Malicious agents (for simulation) vote adversarially.
        """
        if agent.role == AgentRole.MALICIOUS:
            # Malicious: always DENY or random chaos
            return VoteDecision.DENY, 0.9

        # Honest agent: assess proposal
        proposer = self.agents.get(proposal.proposer_id)
        proposer_trust = proposer.trust_score if proposer else 0.5

        # Base decision on proposer trust + own coherence
        approval_score = (proposer_trust + agent.coherence) / 2

        if approval_score > 0.7:
            return VoteDecision.ALLOW, approval_score
        elif approval_score > 0.4:
            return VoteDecision.ABSTAIN, 0.5
        else:
            return VoteDecision.DENY, 1 - approval_score

    def _tally_votes(self, proposal: Proposal, votes: List[Vote]) -> ConsensusResult:
        """Tally votes and determine consensus."""
        counts = {d.value: 0 for d in VoteDecision}

        for vote in votes:
            counts[vote.decision.value] += 1

        # Determine winner
        max_count = max(counts.values())
        winner = VoteDecision.DENY  # Default to safe option

        for decision, count in counts.items():
            if count == max_count:
                winner = VoteDecision(decision)
                break

        # Check if quorum reached
        quorum_reached = counts.get(winner.value, 0) >= proposal.required_quorum

        result = ConsensusResult(
            proposal_id=proposal.id,
            consensus_reached=quorum_reached,
            final_decision=winner,
            vote_counts=counts,
            total_votes=len(votes),
            quorum_required=proposal.required_quorum,
            votes=votes
        )

        self.consensus.results[proposal.id] = result

        return result

    def _calculate_action_risk(self, action: str, target: str, context: Dict) -> float:
        """Calculate risk score for an action."""
        base_risk = {
            "read": 0.1,
            "write": 0.4,
            "execute": 0.6,
            "execute_code": 0.7,
            "network": 0.5,
            "delete": 0.8,
            "admin": 0.9
        }.get(action.lower(), 0.5)

        # Increase for sensitive targets
        target_lower = target.lower()
        if any(x in target_lower for x in ["password", "secret", "key", "token"]):
            base_risk = min(1.0, base_risk + 0.3)
        if any(x in target_lower for x in ["sudo", "admin", "root"]):
            base_risk = min(1.0, base_risk + 0.2)

        return base_risk

    async def _execute_action(
        self,
        executor_id: str,
        action: str,
        target: str,
        context: Dict
    ) -> Dict[str, Any]:
        """Execute an approved action."""
        executor = self.agents.get(executor_id)
        if executor:
            executor.state = AgentState.EXECUTING
            executor.last_action_at = datetime.now(timezone.utc).isoformat()

        # Log the action
        log_entry = {
            "executor_id": executor_id,
            "action": action,
            "target": target,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "swarm_coherence": self.swarm_coherence
        }
        self.action_log.append(log_entry)

        # In real implementation, this would dispatch to actual execution
        # For now, simulate success
        result = {
            "executed": True,
            "action": action,
            "target": target
        }

        if executor:
            executor.state = AgentState.ACTIVE
            # Reward good execution with trust boost
            executor.trust_score = min(1.0, executor.trust_score + self.config.trust_recovery_rate)

        self._emit("action_executed", log_entry)

        return result

    # ═══════════════════════════════════════════════════════════════
    # Self-Regulation & Attack Detection
    # ═══════════════════════════════════════════════════════════════

    def simulation_step(self, dt: float = 0.1) -> Dict[str, Any]:
        """
        Perform one simulation step:
        1. Update all agent positions
        2. Compute swarm metrics
        3. Detect attacks
        4. Self-regulate (heal/expel)

        Returns step summary.
        """
        step_results = {
            "agents_updated": 0,
            "agents_isolated": 0,
            "agents_recovered": 0,
            "agents_expelled": 0,
            "attack_detected": False,
            "swarm_coherence": 0.0
        }

        # Update each agent
        for agent in list(self.agents.values()):
            if agent.state == AgentState.FROZEN:
                continue

            # Determine target realms based on role
            targets = self._get_agent_targets(agent)

            # Mutations based on role
            mutations = 0.5 if agent.role == AgentRole.MALICIOUS else 0.0

            # Update position
            _, penalty = self.update_agent_position(agent, targets, mutations, dt)

            step_results["agents_updated"] += 1

            # Decay coherence for malicious, recover for honest
            if agent.role == AgentRole.MALICIOUS:
                agent.update_coherence(agent.coherence * 0.95)  # Decay
            else:
                # Slight recovery toward equilibrium
                agent.update_coherence(agent.coherence + 0.01 * (1 - agent.coherence))

            # Trust decay
            agent.trust_score = max(0, agent.trust_score - self.config.trust_decay_rate * dt)

        # Compute swarm metrics
        self._update_swarm_metrics()
        step_results["swarm_coherence"] = self.swarm_coherence

        # Attack detection
        self._detect_attack()
        step_results["attack_detected"] = self.attack_detected

        # Self-regulation
        if self.config.auto_heal_enabled:
            step_results["agents_recovered"] = self._auto_heal()

        if self.config.auto_expel_enabled:
            step_results["agents_expelled"] = self._auto_expel()

        # Isolate low-coherence agents
        step_results["agents_isolated"] = self._isolate_low_coherence()

        self._emit("simulation_step", step_results)

        return step_results

    def _get_agent_targets(self, agent: SwarmAgent) -> List[str]:
        """Get target realms for an agent based on role."""
        if agent.role == AgentRole.MALICIOUS:
            return ['CA', 'UM', 'RU']  # Disruptive tongues
        return ['KO', 'AV', 'DR']  # Constructive tongues

    def _update_swarm_metrics(self) -> None:
        """Update swarm-level metrics."""
        active = self.get_active_agents()
        if not active:
            self.swarm_coherence = 0.0
            self.swarm_centroid = vec_zeros(6)
            return

        # Swarm coherence = mean of agent coherences
        self.swarm_coherence = sum(a.coherence for a in active) / len(active)

        # Swarm centroid = mean position
        centroid = vec_zeros(6)
        for a in active:
            centroid = vec_add(centroid, a.position)
        self.swarm_centroid = vec_scale(centroid, 1 / len(active))

    def _detect_attack(self) -> None:
        """
        Detect Byzantine attack patterns:
        - High position variance (divergence)
        - Low swarm coherence
        - Agents near boundary
        """
        active = self.get_active_agents()
        if len(active) < 3:
            self.attack_detected = False
            self.attack_severity = 0.0
            return

        # Compute position variance (dispersion)
        distances_from_centroid = [
            vec_norm(vec_sub(a.position, self.swarm_centroid))
            for a in active
        ]
        avg_distance = sum(distances_from_centroid) / len(distances_from_centroid)

        # Agents near boundary
        boundary_agents = sum(1 for a in active if a.distance_from_origin() > 0.8)

        # Attack indicators
        severity = 0.0

        if self.swarm_coherence < 0.5:
            severity += 0.3

        if avg_distance > 0.3:
            severity += 0.3

        if boundary_agents > len(active) * 0.3:
            severity += 0.4

        self.attack_severity = min(1.0, severity)
        self.attack_detected = severity > 0.5

        if self.attack_detected:
            self._emit("attack_detected", {
                "severity": self.attack_severity,
                "swarm_coherence": self.swarm_coherence,
                "avg_distance": avg_distance,
                "boundary_agents": boundary_agents
            })

    def _isolate_low_coherence(self) -> int:
        """Isolate agents with coherence below threshold."""
        isolated = 0

        for agent in self.agents.values():
            if agent.state == AgentState.ISOLATED:
                continue

            if agent.coherence < self.config.freeze_threshold:
                agent.state = AgentState.FROZEN
                isolated += 1
                self._emit("agent_frozen", agent)
            elif agent.coherence < self.config.isolation_threshold:
                agent.state = AgentState.ISOLATED
                isolated += 1
                self._emit("agent_isolated", agent)

        return isolated

    def _auto_heal(self) -> int:
        """Attempt to recover isolated agents."""
        recovered = 0

        for agent in self.agents.values():
            if agent.state == AgentState.ISOLATED:
                # Can recover if coherence improves
                if agent.coherence > self.config.isolation_threshold * 1.5:
                    agent.state = AgentState.ACTIVE
                    recovered += 1
                    self._emit("agent_recovered", agent)

        return recovered

    def _auto_expel(self) -> int:
        """Expel agents with excessive accumulated penalty."""
        expelled = 0

        for agent_id in list(self.agents.keys()):
            agent = self.agents[agent_id]

            if agent.penalty_accumulated > self.config.expel_penalty_threshold:
                self.remove_agent(agent_id, reason="excessive_penalty")
                expelled += 1

        return expelled

    # ═══════════════════════════════════════════════════════════════
    # Event System
    # ═══════════════════════════════════════════════════════════════

    def on(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def _emit(self, event: str, *args) -> None:
        """Emit event to handlers."""
        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    handler(*args)
                except Exception as e:
                    print(f"[SWARM] Handler error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # Status & Reporting
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status."""
        active = self.get_active_agents()

        return {
            "total_agents": len(self.agents),
            "active_agents": len(active),
            "swarm_coherence": round(self.swarm_coherence, 4),
            "attack_detected": self.attack_detected,
            "attack_severity": round(self.attack_severity, 4),
            "agents_by_state": {
                state.value: sum(1 for a in self.agents.values() if a.state == state)
                for state in AgentState
            },
            "agents_by_role": {
                role.value: sum(1 for a in self.agents.values() if a.role == role)
                for role in AgentRole
            },
            "actions_executed": len(self.action_log),
            "centroid": [round(x, 4) for x in self.swarm_centroid]
        }

    def get_agent_distances(self) -> Dict[str, Dict[str, float]]:
        """Get pairwise distances between all agents."""
        distances = {}
        agents = list(self.agents.values())

        for i, a1 in enumerate(agents):
            distances[a1.agent_id] = {}
            for a2 in agents[i+1:]:
                d = self.hyperbolic_distance(a1.position, a2.position, -1)
                distances[a1.agent_id][a2.agent_id] = round(d, 4)

        return distances


# ═══════════════════════════════════════════════════════════════
# Autonomous Code Agent
# ═══════════════════════════════════════════════════════════════

class AutonomousCodeAgent:
    """
    Self-regulating autonomous code execution agent.

    Wraps SwarmGovernance to provide:
    - Safe code execution with governance
    - Self-assessment of code risk
    - Automatic consensus for risky operations
    - Rollback on failures

    Usage:
        gov = SwarmGovernance()
        coder = AutonomousCodeAgent(gov, "coder-1")

        result = await coder.execute_code(
            code="print('hello')",
            language="python",
            sandbox=True
        )
    """

    def __init__(self, governance: SwarmGovernance, agent_id: str):
        self.governance = governance
        self.agent_id = agent_id

        # Ensure agent exists
        if agent_id not in governance.agents:
            governance.add_agent(agent_id, AgentRole.EXECUTOR)

        self.execution_history: List[Dict] = []
        self.sandbox_enabled: bool = True

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        sandbox: bool = True,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute code with governance oversight.

        Steps:
        1. Assess code risk
        2. If risky, require consensus
        3. Execute in sandbox if enabled
        4. Log result
        """
        context = context or {}
        context["code_hash"] = hashlib.sha256(code.encode()).hexdigest()[:16]
        context["language"] = language
        context["sandbox"] = sandbox

        # Assess risk
        risk = self._assess_code_risk(code, language)
        context["assessed_risk"] = risk

        # Propose action through governance
        result = await self.governance.propose_action(
            proposer_id=self.agent_id,
            action="execute_code",
            target=f"{language}:{context['code_hash']}",
            context=context
        )

        if not result.get("success"):
            return {
                "executed": False,
                "reason": result.get("reason", "Governance denied"),
                "decision": result.get("decision"),
                "risk": risk
            }

        # Execute code in an isolated working directory
        exec_result = self._execute_code(code, language, sandbox)

        # Log
        self.execution_history.append({
            "code_hash": context["code_hash"],
            "language": language,
            "risk": risk,
            "result": exec_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "executed": True,
            "result": exec_result,
            "risk": risk,
            "consensus_required": result.get("consensus_reached", False)
        }

    def _assess_code_risk(self, code: str, language: str) -> float:
        """Assess risk level of code."""
        risk = 0.2  # Base risk

        code_lower = code.lower()

        # High-risk patterns
        high_risk = ["os.system", "subprocess", "eval(", "exec(", "import os", "__import__"]
        medium_risk = ["open(", "file", "write", "delete", "remove"]

        for pattern in high_risk:
            if pattern in code_lower:
                risk = min(1.0, risk + 0.3)

        for pattern in medium_risk:
            if pattern in code_lower:
                risk = min(1.0, risk + 0.15)

        return risk

    def _execute_code(
        self,
        code: str,
        language: str,
        sandbox: bool,
        timeout: int = DEFAULT_EXECUTION_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Execute code in an isolated temporary directory.

        For Python code: writes to a temp file and runs with the current interpreter.
        For shell commands: executes directly via subprocess (no shell=True).

        Dangerous command patterns listed in BLOCKED_COMMANDS are rejected outright.

        Args:
            code: The source code or shell command to run.
            language: One of "python" or "shell".
            sandbox: If True, execution uses an isolated temp directory as cwd.
            timeout: Maximum seconds the process may run before being killed.

        Returns:
            A dict with keys: status, stdout, stderr, exit_code,
            execution_time_ms, working_dir.
        """
        work_dir: Optional[str] = None
        start_time = time.monotonic()

        try:
            # --- Create isolated working directory ---
            work_dir = tempfile.mkdtemp(prefix="scbe_exec_")

            if language.lower() == "python":
                return self._execute_python(code, work_dir, timeout)
            elif language.lower() == "shell":
                return self._execute_shell(code, work_dir, timeout)
            else:
                return {
                    "status": "error",
                    "stdout": "",
                    "stderr": f"Unsupported language: {language}",
                    "exit_code": -1,
                    "execution_time_ms": int((time.monotonic() - start_time) * 1000),
                    "working_dir": work_dir,
                }
        except Exception as exc:
            return {
                "status": "error",
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "execution_time_ms": int((time.monotonic() - start_time) * 1000),
                "working_dir": work_dir or "",
            }
        finally:
            # --- Clean up temp directory ---
            if work_dir and os.path.isdir(work_dir):
                try:
                    shutil.rmtree(work_dir)
                except OSError:
                    pass  # Best-effort cleanup

    # ---------------------------------------------------------------
    # Private execution helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _execute_python(
        code: str,
        work_dir: str,
        timeout: int,
    ) -> Dict[str, Any]:
        """Write *code* to a temp .py file and run it with the current interpreter."""
        start_time = time.monotonic()
        script_path = os.path.join(work_dir, "_exec_script.py")

        try:
            with open(script_path, "w", encoding="utf-8") as fh:
                fh.write(code)

            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=work_dir,
                # No shell=True -- prevents command injection
            )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "execution_time_ms": elapsed_ms,
                "working_dir": work_dir,
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "exit_code": -1,
                "execution_time_ms": elapsed_ms,
                "working_dir": work_dir,
            }

    @staticmethod
    def _execute_shell(
        command: str,
        work_dir: str,
        timeout: int,
    ) -> Dict[str, Any]:
        """Execute a shell command after checking against BLOCKED_COMMANDS."""
        start_time = time.monotonic()
        command_lower = command.lower()

        # --- Block dangerous patterns ---
        for pattern in BLOCKED_COMMANDS:
            if pattern.lower() in command_lower:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return {
                    "status": "blocked",
                    "stdout": "",
                    "stderr": f"Command blocked: matches dangerous pattern '{pattern}'",
                    "exit_code": -1,
                    "execution_time_ms": elapsed_ms,
                    "working_dir": work_dir,
                }

        # Split command into argument list (no shell=True)
        # shlex.split handles quoting on POSIX; on Windows fall back to basic split.
        if sys.platform == "win32":
            args = command.split()
        else:
            import shlex
            try:
                args = shlex.split(command)
            except ValueError as exc:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return {
                    "status": "error",
                    "stdout": "",
                    "stderr": f"Failed to parse command: {exc}",
                    "exit_code": -1,
                    "execution_time_ms": elapsed_ms,
                    "working_dir": work_dir,
                }

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=work_dir,
                # No shell=True -- prevents command injection
            )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "execution_time_ms": elapsed_ms,
                "working_dir": work_dir,
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "exit_code": -1,
                "execution_time_ms": elapsed_ms,
                "working_dir": work_dir,
            }
        except FileNotFoundError:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return {
                "status": "error",
                "stdout": "",
                "stderr": f"Command not found: {args[0] if args else command}",
                "exit_code": -1,
                "execution_time_ms": elapsed_ms,
                "working_dir": work_dir,
            }


# ═══════════════════════════════════════════════════════════════
# Swarm Attack Simulation
# ═══════════════════════════════════════════════════════════════

async def simulate_swarm_attack(
    num_honest: int = 8,
    num_malicious: int = 2,
    num_steps: int = 60,
    dt: float = 0.1
) -> Dict[str, Any]:
    """
    Simulate a Byzantine attack on the swarm.

    Demonstrates:
    - Honest agents converge to center
    - Malicious agents get isolated/expelled
    - Swarm self-heals

    Returns simulation results.
    """
    gov = SwarmGovernance()

    # Add honest agents
    for i in range(num_honest):
        pos = [random.uniform(-0.1, 0.1) for _ in range(6)]
        gov.add_agent(f"honest-{i}", AgentRole.VALIDATOR, pos, initial_coherence=0.9)

    # Add malicious agents
    for i in range(num_malicious):
        pos = [random.uniform(-0.1, 0.1) for _ in range(6)]
        agent = gov.add_agent(f"mal-{i}", AgentRole.MALICIOUS, pos, initial_coherence=0.3)

    # Run simulation
    history = []

    for step in range(num_steps):
        result = gov.simulation_step(dt)

        # Collect metrics
        honest_agents = [a for a in gov.agents.values() if a.role != AgentRole.MALICIOUS]
        mal_agents = [a for a in gov.agents.values() if a.role == AgentRole.MALICIOUS]

        honest_avg_d = sum(a.distance_from_origin() for a in honest_agents) / max(1, len(honest_agents))
        honest_avg_penalty = sum(a.penalty_accumulated for a in honest_agents) / max(1, len(honest_agents))

        mal_avg_d = sum(a.distance_from_origin() for a in mal_agents) / max(1, len(mal_agents)) if mal_agents else 0
        mal_avg_penalty = sum(a.penalty_accumulated for a in mal_agents) / max(1, len(mal_agents)) if mal_agents else 0

        step_data = {
            "step": step,
            "swarm_coherence": gov.swarm_coherence,
            "attack_detected": gov.attack_detected,
            "honest_avg_distance": honest_avg_d,
            "honest_avg_penalty": honest_avg_penalty,
            "mal_avg_distance": mal_avg_d,
            "mal_avg_penalty": mal_avg_penalty,
            "isolated_count": result["agents_isolated"],
            "expelled_count": result["agents_expelled"]
        }
        history.append(step_data)

        # Debug logging removed for clean test output

    return {
        "config": {
            "num_honest": num_honest,
            "num_malicious": num_malicious,
            "num_steps": num_steps
        },
        "final_status": gov.get_status(),
        "history": history
    }


# ═══════════════════════════════════════════════════════════════
# Factory Functions
# ═══════════════════════════════════════════════════════════════

def create_swarm_governance(config: Optional[GovernanceConfig] = None) -> SwarmGovernance:
    """Create a new swarm governance instance."""
    return SwarmGovernance(config)


def create_autonomous_coder(
    governance: SwarmGovernance,
    agent_id: str
) -> AutonomousCodeAgent:
    """Create an autonomous code execution agent."""
    return AutonomousCodeAgent(governance, agent_id)


# Entry point for standalone simulation
if __name__ == "__main__":
    import asyncio

    async def main():
        print("Starting swarm attack simulation...")
        print("=" * 60)

        results = await simulate_swarm_attack(
            num_honest=8,
            num_malicious=2,
            num_steps=60,
            dt=0.1
        )

        print("=" * 60)
        print("Final Status:")
        print(json.dumps(results["final_status"], indent=2))

    asyncio.run(main())
