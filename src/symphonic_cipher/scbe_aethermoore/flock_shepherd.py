"""
Flock Shepherd — Multi-AI Fleet Orchestrator

Manages a governed fleet of AI agents (the "flock"). Each agent is a "sheep"
with a role, health score, position in 6D trust space, and training specialty.

The shepherd:
    - Spawns and registers agents
    - Assigns roles based on training track
    - Monitors health via coherence scores
    - Redistributes tasks when agents degrade
    - Uses balanced ternary governance for consensus
    - Extracts artifacts for federated fusion ("shearing")

Integration points:
    - hydra/head.py          -> HydraHead (agent interface)
    - hydra/spine.py         -> HydraSpine (coordinator)
    - hydra/swarm_governance.py -> SwarmAgent, BFT consensus
    - trinary.py             -> Governance decision packing
    - negabinary.py          -> Gate stability analysis

@module flock_shepherd
@layer Layer 13 (Governance), Layer 12 (Entropy)
@version 1.0.0
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from .trinary import BalancedTernary, Trit, decision_to_trit


# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------

class SheepRole(str, Enum):
    """Roles an agent can take in the flock."""
    LEADER = "leader"
    VALIDATOR = "validator"
    EXECUTOR = "executor"
    OBSERVER = "observer"


class SheepState(str, Enum):
    """Operational states."""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ISOLATED = "isolated"    # Quarantined — low coherence
    FROZEN = "frozen"        # Suspended — attack detected
    SHEARING = "shearing"    # Extracting artifacts


class TrainingTrack(str, Enum):
    """Training specialization."""
    SYSTEM = "system"
    GOVERNANCE = "governance"
    FUNCTIONS = "functions"


# Track -> default role mapping
TRACK_ROLE_MAP = {
    TrainingTrack.SYSTEM: SheepRole.LEADER,
    TrainingTrack.GOVERNANCE: SheepRole.VALIDATOR,
    TrainingTrack.FUNCTIONS: SheepRole.EXECUTOR,
}

# Role -> Sacred Tongue affinity
ROLE_TONGUE_MAP = {
    SheepRole.LEADER: "KO",
    SheepRole.VALIDATOR: "AV",
    SheepRole.EXECUTOR: "RU",
    SheepRole.OBSERVER: "UM",
}

# Coherence thresholds
COHERENCE_ISOLATE = 0.30   # Below this -> quarantine
COHERENCE_WARN = 0.50      # Below this -> warning
COHERENCE_HEALTHY = 0.70   # Above this -> healthy


# ---------------------------------------------------------------------------
# Sheep (Individual Agent)
# ---------------------------------------------------------------------------

@dataclass
class Sheep:
    """A single agent in the flock."""
    sheep_id: str
    name: str
    role: SheepRole = SheepRole.VALIDATOR
    state: SheepState = SheepState.IDLE
    track: TrainingTrack = TrainingTrack.SYSTEM

    # Health metrics
    coherence: float = 1.0       # 0.0 to 1.0
    error_rate: float = 0.0      # 0.0 to 1.0
    tasks_completed: int = 0
    tasks_failed: int = 0

    # 6D position in Poincare trust space
    position: List[float] = field(default_factory=lambda: [0.0] * 6)

    # Timing
    spawned_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)

    # Current task
    current_task: Optional[str] = None

    @property
    def tongue(self) -> str:
        """Sacred Tongue affinity based on role."""
        return ROLE_TONGUE_MAP.get(self.role, "UM")

    @property
    def is_healthy(self) -> bool:
        return self.coherence >= COHERENCE_HEALTHY and self.state == SheepState.ACTIVE

    @property
    def is_available(self) -> bool:
        return self.state in (SheepState.ACTIVE, SheepState.IDLE) and self.current_task is None

    @property
    def health_label(self) -> str:
        if self.coherence < COHERENCE_ISOLATE:
            return "CRITICAL"
        if self.coherence < COHERENCE_WARN:
            return "WARNING"
        if self.coherence < COHERENCE_HEALTHY:
            return "FAIR"
        return "HEALTHY"

    def heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = time.time()

    def degrade(self, amount: float = 0.05) -> None:
        """Degrade coherence (e.g., after an error)."""
        self.coherence = max(0.0, self.coherence - amount)
        if self.coherence < COHERENCE_ISOLATE:
            self.state = SheepState.ISOLATED

    def recover(self, amount: float = 0.02) -> None:
        """Recover coherence (e.g., after successful task)."""
        self.coherence = min(1.0, self.coherence + amount)
        if self.state == SheepState.ISOLATED and self.coherence >= COHERENCE_WARN:
            self.state = SheepState.ACTIVE

    def complete_task(self, success: bool = True) -> None:
        """Record task completion."""
        if success:
            self.tasks_completed += 1
            self.recover()
        else:
            self.tasks_failed += 1
            self.degrade()
        self.current_task = None
        self.error_rate = (
            self.tasks_failed / max(1, self.tasks_completed + self.tasks_failed)
        )


# ---------------------------------------------------------------------------
# Flock Task
# ---------------------------------------------------------------------------

@dataclass
class FlockTask:
    """A task to be distributed across the flock."""
    task_id: str
    description: str
    track: TrainingTrack = TrainingTrack.SYSTEM
    priority: int = 5          # 1 (highest) to 10 (lowest)
    owner: Optional[str] = None  # sheep_id
    status: str = "pending"    # pending, active, completed, failed, orphaned
    result: Optional[Any] = None
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Flock (The Fleet)
# ---------------------------------------------------------------------------

class Flock:
    """The managed AI agent fleet.

    Provides:
    - Agent lifecycle (spawn, retire, isolate)
    - Task distribution with governance voting
    - Health monitoring and auto-redistribution
    - Status dashboard
    """

    def __init__(self) -> None:
        self.sheep: Dict[str, Sheep] = {}
        self.tasks: Dict[str, FlockTask] = {}
        self._log: List[Dict[str, Any]] = []

    # ── Agent Lifecycle ──

    def spawn(
        self,
        name: str,
        track: TrainingTrack = TrainingTrack.SYSTEM,
        role: Optional[SheepRole] = None,
    ) -> Sheep:
        """Spawn a new agent in the flock."""
        sheep_id = f"sheep-{uuid.uuid4().hex[:8]}"
        agent_role = role or TRACK_ROLE_MAP.get(track, SheepRole.VALIDATOR)

        agent = Sheep(
            sheep_id=sheep_id,
            name=name,
            role=agent_role,
            state=SheepState.ACTIVE,
            track=track,
        )
        self.sheep[sheep_id] = agent
        self._log_event("spawn", sheep_id, f"Spawned {name} as {agent_role.value}")
        return agent

    def retire(self, sheep_id: str) -> bool:
        """Remove an agent from the flock."""
        if sheep_id not in self.sheep:
            return False
        agent = self.sheep.pop(sheep_id)
        # Orphan any active tasks
        for task in self.tasks.values():
            if task.owner == sheep_id and task.status == "active":
                task.status = "orphaned"
                task.owner = None
        self._log_event("retire", sheep_id, f"Retired {agent.name}")
        return True

    def isolate(self, sheep_id: str) -> bool:
        """Quarantine an agent."""
        agent = self.sheep.get(sheep_id)
        if not agent:
            return False
        agent.state = SheepState.ISOLATED
        self._log_event("isolate", sheep_id, f"Isolated {agent.name} (coherence={agent.coherence:.2f})")
        return True

    # ── Task Distribution ──

    def add_task(
        self,
        description: str,
        track: TrainingTrack = TrainingTrack.SYSTEM,
        priority: int = 5,
    ) -> FlockTask:
        """Add a task to the queue."""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = FlockTask(
            task_id=task_id,
            description=description,
            track=track,
            priority=priority,
        )
        self.tasks[task_id] = task
        return task

    def assign_task(self, task_id: str, sheep_id: Optional[str] = None) -> bool:
        """Assign a task to an agent (auto-select if no sheep_id given)."""
        task = self.tasks.get(task_id)
        if not task or task.status != "pending":
            return False

        if sheep_id:
            agent = self.sheep.get(sheep_id)
            if not agent or not agent.is_available:
                return False
        else:
            # Auto-select: find best available agent for this track
            agent = self._select_best_agent(task.track)
            if not agent:
                return False

        task.owner = agent.sheep_id
        task.status = "active"
        agent.current_task = task.task_id
        agent.state = SheepState.BUSY
        self._log_event("assign", agent.sheep_id, f"Assigned {task_id} to {agent.name}")
        return True

    def _select_best_agent(self, track: TrainingTrack) -> Optional[Sheep]:
        """Select the best available agent for a track."""
        candidates = [
            s for s in self.sheep.values()
            if s.is_available and s.track == track
        ]
        if not candidates:
            # Fallback: any available agent
            candidates = [s for s in self.sheep.values() if s.is_available]
        if not candidates:
            return None
        # Sort by coherence (highest first), then by tasks completed
        candidates.sort(key=lambda s: (-s.coherence, -s.tasks_completed))
        return candidates[0]

    def redistribute_orphans(self) -> int:
        """Redistribute orphaned tasks to available agents."""
        orphans = [t for t in self.tasks.values() if t.status == "orphaned"]
        reassigned = 0
        for task in orphans:
            task.status = "pending"
            if self.assign_task(task.task_id):
                reassigned += 1
        return reassigned

    # ── Governance Voting ──

    def vote_on_action(self, action: str) -> Dict[str, Any]:
        """Run a balanced ternary governance vote across active validators.

        Returns consensus decision and vote breakdown.
        """
        validators = [
            s for s in self.sheep.values()
            if s.role == SheepRole.VALIDATOR and s.state == SheepState.ACTIVE
        ]

        if not validators:
            return {
                "action": action,
                "consensus": "QUARANTINE",
                "reason": "No active validators",
                "votes": [],
            }

        # Each validator votes based on coherence
        votes: List[str] = []
        for v in validators:
            if v.coherence >= COHERENCE_HEALTHY:
                votes.append("ALLOW")
            elif v.coherence >= COHERENCE_WARN:
                votes.append("QUARANTINE")
            else:
                votes.append("DENY")

        packed = BalancedTernary.pack_decisions(votes)
        summary = packed.governance_summary()

        result = {
            "action": action,
            "consensus": summary["consensus"],
            "net_score": summary["net_score"],
            "votes": votes,
            "voter_ids": [v.sheep_id for v in validators],
            "packed_bt": str(packed),
        }
        self._log_event("vote", "flock", f"Vote on '{action}': {summary['consensus']}")
        return result

    # ── BFT Tolerance ──

    @property
    def bft_tolerance(self) -> int:
        """Maximum Byzantine (malicious/faulty) agents the flock can tolerate.

        BFT requires n >= 3f + 1, so f = (n - 1) // 3.
        """
        n = sum(1 for s in self.sheep.values() if s.state != SheepState.FROZEN)
        return max(0, (n - 1) // 3)

    # ── Health Monitoring ──

    def health_check(self) -> Dict[str, Any]:
        """Run health check across all agents."""
        total = len(self.sheep)
        active = sum(1 for s in self.sheep.values() if s.state == SheepState.ACTIVE)
        idle = sum(1 for s in self.sheep.values() if s.state == SheepState.IDLE)
        busy = sum(1 for s in self.sheep.values() if s.state == SheepState.BUSY)
        isolated = sum(1 for s in self.sheep.values() if s.state == SheepState.ISOLATED)
        frozen = sum(1 for s in self.sheep.values() if s.state == SheepState.FROZEN)

        avg_coherence = (
            sum(s.coherence for s in self.sheep.values()) / total
            if total > 0 else 0.0
        )

        healthy_count = sum(1 for s in self.sheep.values() if s.is_healthy)

        # Track breakdown
        tracks = {}
        for track in TrainingTrack:
            agents = [s for s in self.sheep.values() if s.track == track]
            tracks[track.value] = {
                "count": len(agents),
                "avg_coherence": (
                    sum(a.coherence for a in agents) / len(agents)
                    if agents else 0.0
                ),
            }

        return {
            "total": total,
            "active": active,
            "idle": idle,
            "busy": busy,
            "isolated": isolated,
            "frozen": frozen,
            "avg_coherence": round(avg_coherence, 3),
            "healthy_ratio": f"{healthy_count}/{total}",
            "bft_tolerance": self.bft_tolerance,
            "tracks": tracks,
        }

    def status_dashboard(self) -> str:
        """Generate a text status dashboard."""
        h = self.health_check()
        lines = [
            "FLOCK STATUS",
            "=" * 40,
            f"Total Agents: {h['total']}",
            f"  Active: {h['active']}  Idle: {h['idle']}  Busy: {h['busy']}",
            f"  Isolated: {h['isolated']}  Frozen: {h['frozen']}",
            f"",
            f"Average Coherence: {h['avg_coherence']:.3f}",
            f"Healthy: {h['healthy_ratio']}",
            f"BFT Tolerance: f={h['bft_tolerance']}",
            f"",
            "Tracks:",
        ]
        for track_name, info in h["tracks"].items():
            lines.append(f"  {track_name}: {info['count']} agents, "
                        f"coherence={info['avg_coherence']:.3f}")

        # Per-agent detail
        if self.sheep:
            lines.append("")
            lines.append("Agents:")
            for s in sorted(self.sheep.values(), key=lambda x: x.sheep_id):
                task_info = f" [{s.current_task}]" if s.current_task else ""
                lines.append(
                    f"  {s.sheep_id} | {s.name:<20s} | {s.role.value:<10s} | "
                    f"{s.state.value:<10s} | coh={s.coherence:.2f} | "
                    f"{s.tongue}{task_info}"
                )

        # Pending tasks
        pending = [t for t in self.tasks.values() if t.status == "pending"]
        orphaned = [t for t in self.tasks.values() if t.status == "orphaned"]
        if pending or orphaned:
            lines.append("")
            lines.append(f"Pending Tasks: {len(pending)}  Orphaned: {len(orphaned)}")

        return "\n".join(lines)

    # ── Logging ──

    def _log_event(self, event_type: str, agent_id: str, message: str) -> None:
        self._log.append({
            "time": time.time(),
            "event": event_type,
            "agent": agent_id,
            "message": message,
        })

    @property
    def event_log(self) -> List[Dict[str, Any]]:
        return list(self._log)
