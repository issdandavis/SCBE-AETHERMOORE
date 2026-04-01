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
    - energy_budget.py       -> Energy-bounded lifecycle (optimal foraging)

@module flock_shepherd
@layer Layer 13 (Governance), Layer 12 (Entropy)
@version 1.0.0
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .energy_budget import (
    EnergyBoundedAgent,
    EnergyPhase,
    FleetEnergyManager,
)
from .trinary import BalancedTernary

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
    ISOLATED = "isolated"  # Quarantined — low coherence
    FROZEN = "frozen"  # Suspended — attack detected
    SHEARING = "shearing"  # Extracting artifacts


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
COHERENCE_ISOLATE = 0.30  # Below this -> quarantine
COHERENCE_WARN = 0.50  # Below this -> warning
COHERENCE_HEALTHY = 0.70  # Above this -> healthy


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
    coherence: float = 1.0  # 0.0 to 1.0
    error_rate: float = 0.0  # 0.0 to 1.0
    tasks_completed: int = 0
    tasks_failed: int = 0

    # 6D position in Poincare trust space
    position: List[float] = field(default_factory=lambda: [0.0] * 6)

    # Timing
    spawned_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)

    # Current task
    current_task: Optional[str] = None

    # Energy-bounded lifecycle (optimal foraging)
    energy_agent: Optional[EnergyBoundedAgent] = field(default=None, repr=False)

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
    def energy_phase(self) -> Optional[EnergyPhase]:
        """Current energy lifecycle phase, if energy tracking is enabled."""
        if self.energy_agent is None:
            return None
        return self.energy_agent.phase

    @property
    def energy_remaining(self) -> Optional[float]:
        """Remaining energy budget, if energy tracking is enabled."""
        if self.energy_agent is None:
            return None
        return self.energy_agent.energy_remaining

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

    def spend_energy(self, coords: List[float], label: str = "") -> Optional[Dict[str, Any]]:
        """Spend energy for an action at the given 6D tongue coordinates.

        Returns the energy receipt, or None if energy tracking is disabled.
        If the agent's energy is exhausted, transitions to ISOLATED state.
        """
        if self.energy_agent is None:
            return None

        receipt = self.energy_agent.spend(coords, label)

        # Energy exhaustion -> quarantine
        if not receipt["permitted"]:
            self.state = SheepState.ISOLATED
            self.coherence = min(self.coherence, COHERENCE_ISOLATE - 0.01)

        return receipt

    def complete_task(self, success: bool = True, nectar_value: float = 1.0) -> None:
        """Record task completion.

        Args:
            success: Whether the task completed successfully.
            nectar_value: Value of work produced (for foraging efficiency tracking).
        """
        if success:
            self.tasks_completed += 1
            self.recover()
            # Record nectar collected (successful work output)
            if self.energy_agent is not None:
                self.energy_agent.collect_nectar(nectar_value)
        else:
            self.tasks_failed += 1
            self.degrade()
        self.current_task = None
        self.error_rate = self.tasks_failed / max(1, self.tasks_completed + self.tasks_failed)


# ---------------------------------------------------------------------------
# Flock Task
# ---------------------------------------------------------------------------


@dataclass
class FlockTask:
    """A task to be distributed across the flock."""

    task_id: str
    description: str
    track: TrainingTrack = TrainingTrack.SYSTEM
    priority: int = 5  # 1 (highest) to 10 (lowest)
    owner: Optional[str] = None  # sheep_id
    status: str = "pending"  # pending, active, completed, failed, orphaned
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

    def __init__(
        self,
        energy_budget: float = 2000.0,
        heartbeat_timeout: float = 60.0,
        freeze_after_missed_heartbeats: int = 2,
    ) -> None:
        self.sheep: Dict[str, Sheep] = {}
        self.tasks: Dict[str, FlockTask] = {}
        self._log: List[Dict[str, Any]] = []
        self._energy_manager = FleetEnergyManager(default_budget=energy_budget)
        self.heartbeat_timeout = heartbeat_timeout
        self.freeze_after_missed_heartbeats = freeze_after_missed_heartbeats

    # ── Fleet Refresh ──

    def refresh(
        self,
        heartbeat_timeout: Optional[float] = None,
        auto_redistribute: bool = True,
    ) -> Dict[str, Any]:
        """Refresh flock health: check heartbeats, redistribute orphaned tasks."""
        if heartbeat_timeout is not None:
            self.heartbeat_timeout = heartbeat_timeout
        now = time.time()
        stale: List[str] = []
        for sid, s in self.sheep.items():
            elapsed = now - s.last_heartbeat
            if elapsed > self.heartbeat_timeout * self.freeze_after_missed_heartbeats:
                if s.state != SheepState.FROZEN:
                    s.state = SheepState.FROZEN
                stale.append(sid)
        reassigned = 0
        if auto_redistribute and stale:
            available = [
                sid
                for sid, s in self.sheep.items()
                if sid not in stale and s.state in (SheepState.ACTIVE, SheepState.IDLE)
            ]
            for tid, task in self.tasks.items():
                if task.owner in stale and task.status == "active":
                    if available:
                        new_owner = available[reassigned % len(available)]
                        task.owner = new_owner
                    else:
                        task.status = "orphaned"
                        task.owner = None
                    reassigned += 1
        return {"stale_agents": stale, "reassigned_tasks": reassigned}

    # ── Agent Lifecycle ──

    def spawn(
        self,
        name: str,
        track: TrainingTrack = TrainingTrack.SYSTEM,
        role: Optional[SheepRole] = None,
        energy_budget: Optional[float] = None,
    ) -> Sheep:
        """Spawn a new agent in the flock.

        Each agent is provisioned with an energy budget (the bee fills
        its crop with honey before leaving the hive).
        """
        sheep_id = f"sheep-{uuid.uuid4().hex[:8]}"
        agent_role = role or TRACK_ROLE_MAP.get(track, SheepRole.VALIDATOR)

        # Provision energy budget
        energy_agent = self._energy_manager.provision(
            sheep_id,
            budget=energy_budget,
        )

        agent = Sheep(
            sheep_id=sheep_id,
            name=name,
            role=agent_role,
            state=SheepState.ACTIVE,
            track=track,
            energy_agent=energy_agent,
        )
        self.sheep[sheep_id] = agent
        self._log_event("spawn", sheep_id, f"Spawned {name} as {agent_role.value} (budget={energy_agent.budget})")
        return agent

    def retire(self, sheep_id: str) -> bool:
        """Remove an agent from the flock.

        Archives the agent's energy record (post-mortem foraging data).
        """
        if sheep_id not in self.sheep:
            return False
        agent = self.sheep.pop(sheep_id)
        # Archive energy data
        self._energy_manager.retire(sheep_id)
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
        self._log_event(
            "isolate",
            sheep_id,
            f"Isolated {agent.name} (coherence={agent.coherence:.2f})",
        )
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

    def mark_task_complete(
        self,
        task_id: str,
        success: bool = True,
        result: Any = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Mark a task as completed and free the owning agent."""
        task = self.tasks.get(task_id)
        if not task or task.status != "active":
            return False
        task.status = "completed" if success else "failed"
        task.result = result if success else {"error": error_message}
        if task.owner:
            agent = self.sheep.get(task.owner)
            if agent:
                if success:
                    agent.tasks_completed += 1
                else:
                    agent.tasks_failed += 1
                agent.current_task = None
                agent.state = SheepState.IDLE
        self._log_event("complete", task.owner or "unknown", f"Task {task_id} {'completed' if success else 'failed'}")
        return True

    def _select_best_agent(self, track: TrainingTrack) -> Optional[Sheep]:
        """Select the best available agent for a track."""
        candidates = [s for s in self.sheep.values() if s.is_available and s.track == track]
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
        validators = [s for s in self.sheep.values() if s.role == SheepRole.VALIDATOR and s.state == SheepState.ACTIVE]

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

    # ── Energy Management ──

    @property
    def energy_manager(self) -> FleetEnergyManager:
        """Access the fleet energy manager."""
        return self._energy_manager

    def spend_energy(self, sheep_id: str, coords: List[float], label: str = "") -> Optional[Dict[str, Any]]:
        """Spend energy for an agent action. Quarantines if budget exhausted.

        This is the primary integration point: every action an agent takes
        flows through here before execution.
        """
        agent = self.sheep.get(sheep_id)
        if not agent:
            return None

        receipt = agent.spend_energy(coords, label)

        # If energy caused isolation, log it and orphan tasks
        if receipt and not receipt["permitted"]:
            self._log_event(
                "energy_quarantine",
                sheep_id,
                f"Energy depleted for {agent.name} (spent={receipt.get('cost', 0):.1f})",
            )
            # Orphan any active task
            if agent.current_task:
                task = self.tasks.get(agent.current_task)
                if task and task.status == "active":
                    task.status = "orphaned"
                    task.owner = None
                agent.current_task = None

        return receipt

    # ── Health Monitoring ──

    def health_check(self) -> Dict[str, Any]:
        """Run health check across all agents."""
        total = len(self.sheep)
        active = sum(1 for s in self.sheep.values() if s.state == SheepState.ACTIVE)
        idle = sum(1 for s in self.sheep.values() if s.state == SheepState.IDLE)
        busy = sum(1 for s in self.sheep.values() if s.state == SheepState.BUSY)
        isolated = sum(1 for s in self.sheep.values() if s.state == SheepState.ISOLATED)
        frozen = sum(1 for s in self.sheep.values() if s.state == SheepState.FROZEN)

        avg_coherence = sum(s.coherence for s in self.sheep.values()) / total if total > 0 else 0.0

        healthy_count = sum(1 for s in self.sheep.values() if s.is_healthy)

        # Track breakdown
        tracks = {}
        for track in TrainingTrack:
            agents = [s for s in self.sheep.values() if s.track == track]
            tracks[track.value] = {
                "count": len(agents),
                "avg_coherence": (sum(a.coherence for a in agents) / len(agents) if agents else 0.0),
            }

        energy_status = self._energy_manager.fleet_status()

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
            "energy": energy_status,
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Return structured dashboard data for API consumers."""
        h = self.health_check()
        h["completed_tasks"] = sum(s.tasks_completed for s in self.sheep.values())
        tasks_list = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "status": t.status,
                "owner": t.owner,
                "priority": t.priority,
            }
            for t in self.tasks.values()
        ]
        return {"health": h, "tasks": tasks_list}

    def status_dashboard(self) -> str:
        """Generate a text status dashboard."""
        h = self.health_check()
        lines = [
            "FLOCK STATUS",
            "=" * 40,
            f"Total Agents: {h['total']}",
            f"  Active: {h['active']}  Idle: {h['idle']}  Busy: {h['busy']}",
            f"  Isolated: {h['isolated']}  Frozen: {h['frozen']}",
            "",
            f"Average Coherence: {h['avg_coherence']:.3f}",
            f"Healthy: {h['healthy_ratio']}",
            f"BFT Tolerance: f={h['bft_tolerance']}",
            "",
            "Tracks:",
        ]
        for track_name, info in h["tracks"].items():
            lines.append(f"  {track_name}: {info['count']} agents, " f"coherence={info['avg_coherence']:.3f}")

        # Per-agent detail
        if self.sheep:
            lines.append("")
            lines.append("Agents:")
            for s in sorted(self.sheep.values(), key=lambda x: x.sheep_id):
                task_info = f" [{s.current_task}]" if s.current_task else ""
                energy_info = ""
                if s.energy_agent is not None:
                    ef = s.energy_agent.energy_fraction
                    energy_info = f" | E={ef*100:.0f}%({s.energy_agent.phase.value})"
                lines.append(
                    f"  {s.sheep_id} | {s.name:<20s} | {s.role.value:<10s} | "
                    f"{s.state.value:<10s} | coh={s.coherence:.2f} | "
                    f"{s.tongue}{energy_info}{task_info}"
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
        self._log.append(
            {
                "time": time.time(),
                "event": event_type,
                "agent": agent_id,
                "message": message,
            }
        )

    @property
    def event_log(self) -> List[Dict[str, Any]]:
        return list(self._log)
