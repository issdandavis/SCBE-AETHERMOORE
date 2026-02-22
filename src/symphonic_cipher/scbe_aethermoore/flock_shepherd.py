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

v2.0 additions:
    - FlockEventLog: immutable event-sourced audit trail for all flock mutations
    - FlockWatchdog: auto-refresh loop with health scanning, isolation, retirement,
      and task rebalancing
    - flock_health_report(): comprehensive health dashboard with recommendations
    - Error handling: retry with exponential backoff, graceful BFT degradation,
      fallback task assignment

Integration points:
    - hydra/head.py          -> HydraHead (agent interface)
    - hydra/spine.py         -> HydraSpine (coordinator)
    - hydra/swarm_governance.py -> SwarmAgent, BFT consensus
    - trinary.py             -> Governance decision packing
    - negabinary.py          -> Gate stability analysis

@module flock_shepherd
@layer Layer 13 (Governance), Layer 12 (Entropy)
@version 2.0.0
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .trinary import BalancedTernary, Trit, decision_to_trit

logger = logging.getLogger(__name__)


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
# Event Sourcing — FlockEventLog
# ---------------------------------------------------------------------------

@dataclass
class FlockEvent:
    """A single immutable event in the flock audit trail."""
    event_id: str
    timestamp: float
    event_type: str         # spawn, retire, isolate, task_assign, task_complete,
                            # vote, watchdog_action, bft_warning, retry, error
    sheep_id: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = f"evt-{uuid.uuid4().hex[:12]}"


class FlockEventLog:
    """Immutable, queryable audit trail for all flock mutations.

    Every flock action (spawn, retire, isolate, task assignment, voting,
    watchdog actions) is recorded as a FlockEvent.  Events can be queried
    by type, time range, or sheep_id.
    """

    def __init__(self) -> None:
        self._events: List[FlockEvent] = []
        self._lock = threading.Lock()

    # ── Recording ──

    def record(
        self,
        event_type: str,
        sheep_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> FlockEvent:
        """Record a new event and return it."""
        evt = FlockEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            event_type=event_type,
            sheep_id=sheep_id,
            details=details or {},
        )
        with self._lock:
            self._events.append(evt)
        return evt

    # ── Queries ──

    def all(self) -> List[FlockEvent]:
        """Return a copy of all events."""
        with self._lock:
            return list(self._events)

    def by_type(self, event_type: str) -> List[FlockEvent]:
        """Filter events by type."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def by_sheep(self, sheep_id: str) -> List[FlockEvent]:
        """Filter events related to a specific sheep."""
        with self._lock:
            return [e for e in self._events if e.sheep_id == sheep_id]

    def by_time_range(
        self, start: float, end: Optional[float] = None
    ) -> List[FlockEvent]:
        """Filter events within a time range (inclusive)."""
        if end is None:
            end = time.time()
        with self._lock:
            return [e for e in self._events if start <= e.timestamp <= end]

    def count(self, event_type: Optional[str] = None) -> int:
        """Count events, optionally filtered by type."""
        with self._lock:
            if event_type is None:
                return len(self._events)
            return sum(1 for e in self._events if e.event_type == event_type)

    def latest(self, n: int = 10) -> List[FlockEvent]:
        """Return the most recent *n* events."""
        with self._lock:
            return list(self._events[-n:])

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    def __bool__(self) -> bool:
        # Always truthy — the log object exists even when empty.
        return True


# ---------------------------------------------------------------------------
# Retry Helper
# ---------------------------------------------------------------------------

def _retry_with_backoff(
    fn: Callable[..., Any],
    max_retries: int = 3,
    base_delay: float = 0.1,
    event_log: Optional[FlockEventLog] = None,
    context: str = "",
) -> Any:
    """Execute *fn* with exponential backoff retry on failure.

    Returns the result of *fn* on success.
    Raises the last exception if all retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            delay = base_delay * (2 ** attempt)
            if event_log:
                event_log.record(
                    "retry",
                    details={
                        "context": context,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "delay": delay,
                        "error": str(exc),
                    },
                )
            logger.warning(
                "Retry %d/%d for '%s' after %.2fs: %s",
                attempt + 1, max_retries, context, delay, exc,
            )
            time.sleep(delay)
    # All retries exhausted
    raise last_exc  # type: ignore[misc]


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
    - Event-sourced audit trail (FlockEventLog)
    - Retry with exponential backoff on transient failures
    - Graceful BFT degradation when quorum is lost
    - Comprehensive health report with recommendations
    """

    def __init__(self) -> None:
        self.sheep: Dict[str, Sheep] = {}
        self.tasks: Dict[str, FlockTask] = {}
        self._log: List[Dict[str, Any]] = []
        self.events = FlockEventLog()

    # ── Agent Lifecycle ──

    def spawn(
        self,
        name: str,
        track: TrainingTrack = TrainingTrack.SYSTEM,
        role: Optional[SheepRole] = None,
    ) -> Sheep:
        """Spawn a new agent in the flock."""
        try:
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
            self.events.record("spawn", sheep_id, {
                "name": name,
                "role": agent_role.value,
                "track": track.value,
            })
            return agent
        except Exception as exc:
            self.events.record("error", details={
                "context": "spawn",
                "name": name,
                "error": str(exc),
            })
            logger.error("Failed to spawn agent '%s': %s", name, exc)
            raise

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
        self.events.record("retire", sheep_id, {"name": agent.name})
        return True

    def isolate(self, sheep_id: str) -> bool:
        """Quarantine an agent."""
        agent = self.sheep.get(sheep_id)
        if not agent:
            return False
        agent.state = SheepState.ISOLATED
        self._log_event("isolate", sheep_id, f"Isolated {agent.name} (coherence={agent.coherence:.2f})")
        self.events.record("isolate", sheep_id, {
            "name": agent.name,
            "coherence": agent.coherence,
        })
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
        self.events.record("task_create", details={
            "task_id": task_id,
            "description": description,
            "track": track.value,
            "priority": priority,
        })
        return task

    def assign_task(self, task_id: str, sheep_id: Optional[str] = None) -> bool:
        """Assign a task to an agent (auto-select if no sheep_id given).

        Includes try/except with fallback to next available sheep on failure.
        """
        task = self.tasks.get(task_id)
        if not task or task.status != "pending":
            return False

        try:
            if sheep_id:
                agent = self.sheep.get(sheep_id)
                if not agent or not agent.is_available:
                    # Fallback: try auto-selecting instead
                    agent = self._select_best_agent(task.track)
                    if not agent:
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
            self.events.record("task_assign", agent.sheep_id, {
                "task_id": task_id,
                "description": task.description,
            })
            return True
        except Exception as exc:
            self.events.record("error", details={
                "context": "assign_task",
                "task_id": task_id,
                "error": str(exc),
            })
            logger.error("Failed to assign task '%s': %s", task_id, exc)
            return False

    def assign_task_with_retry(
        self,
        task_id: str,
        sheep_id: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 0.1,
    ) -> bool:
        """Assign a task with retry logic and exponential backoff.

        On each failure attempt, the method tries the next available sheep.
        """
        task = self.tasks.get(task_id)
        if not task or task.status != "pending":
            return False

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                result = self.assign_task(task_id, sheep_id)
                if result:
                    return True
                # Assignment returned False — not an exception, but still a failure.
                # On subsequent attempts, try auto-selection (clear sheep_id).
                sheep_id = None
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.events.record("retry", details={
                        "context": "assign_task_with_retry",
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "delay": delay,
                    })
                    time.sleep(delay)
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.events.record("retry", details={
                        "context": "assign_task_with_retry",
                        "task_id": task_id,
                        "attempt": attempt + 1,
                        "delay": delay,
                        "error": str(exc),
                    })
                    time.sleep(delay)

        # All retries exhausted
        self.events.record("error", details={
            "context": "assign_task_with_retry_exhausted",
            "task_id": task_id,
            "max_retries": max_retries,
            "last_error": str(last_exc) if last_exc else "no_available_agent",
        })
        return False

    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """Mark a task as completed or failed and update the sheep.

        After completion the sheep transitions back to ACTIVE (or remains
        ISOLATED if coherence dropped below threshold during degrade).
        """
        task = self.tasks.get(task_id)
        if not task or task.status != "active":
            return False

        agent = self.sheep.get(task.owner) if task.owner else None
        if agent:
            agent.complete_task(success)
            # Transition from BUSY back to ACTIVE (unless degraded to ISOLATED)
            if agent.state == SheepState.BUSY:
                agent.state = SheepState.ACTIVE

        task.status = "completed" if success else "failed"
        self.events.record("task_complete", task.owner, {
            "task_id": task_id,
            "success": success,
        })
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

    def rebalance_from_failed(self, failed_sheep_id: str) -> int:
        """Rebalance all active tasks from a failed/isolated sheep to healthy ones.

        Returns the number of tasks successfully reassigned.
        """
        reassigned = 0
        for task in list(self.tasks.values()):
            if task.owner == failed_sheep_id and task.status == "active":
                task.status = "orphaned"
                task.owner = None
                # Clear the failed sheep's current_task if still referencing this
                failed_agent = self.sheep.get(failed_sheep_id)
                if failed_agent and failed_agent.current_task == task.task_id:
                    failed_agent.current_task = None

        # Now redistribute all orphans (including these)
        reassigned = self.redistribute_orphans()
        if reassigned > 0:
            self.events.record("watchdog_action", failed_sheep_id, {
                "action": "rebalance_from_failed",
                "reassigned": reassigned,
            })
        return reassigned

    # ── Governance Voting ──

    def vote_on_action(self, action: str) -> Dict[str, Any]:
        """Run a balanced ternary governance vote across active validators.

        Returns consensus decision and vote breakdown.
        Includes graceful degradation when BFT quorum is lost.
        """
        validators = [
            s for s in self.sheep.values()
            if s.role == SheepRole.VALIDATOR and s.state == SheepState.ACTIVE
        ]

        if not validators:
            self.events.record("bft_warning", details={
                "action": action,
                "warning": "No active validators — defaulting to QUARANTINE",
            })
            logger.warning(
                "BFT quorum lost: no active validators for action '%s'. "
                "Continuing with QUARANTINE (reduced safety).", action
            )
            return {
                "action": action,
                "consensus": "QUARANTINE",
                "reason": "No active validators",
                "votes": [],
                "bft_degraded": True,
            }

        # Check if we have enough validators for BFT tolerance
        n_active = len(validators)
        needed_for_f1 = 4  # n >= 3f+1, so f=1 needs n>=4
        bft_degraded = n_active < needed_for_f1
        if bft_degraded:
            self.events.record("bft_warning", details={
                "action": action,
                "active_validators": n_active,
                "needed_for_f1": needed_for_f1,
                "warning": "Insufficient validators for f=1 BFT tolerance",
            })
            logger.warning(
                "BFT degraded: only %d validators (need %d for f=1). "
                "Continuing with reduced safety.", n_active, needed_for_f1
            )

        # Each validator votes based on coherence
        votes: List[str] = []
        for v in validators:
            if v.coherence >= COHERENCE_HEALTHY:
                votes.append("ALLOW")
            elif v.coherence >= COHERENCE_WARN:
                votes.append("QUARANTINE")
            else:
                votes.append("DENY")

        try:
            packed = BalancedTernary.pack_decisions(votes)
            summary = packed.governance_summary()

            result: Dict[str, Any] = {
                "action": action,
                "consensus": summary["consensus"],
                "net_score": summary["net_score"],
                "votes": votes,
                "voter_ids": [v.sheep_id for v in validators],
                "packed_bt": str(packed),
                "bft_degraded": bft_degraded,
            }
        except Exception as exc:
            # Graceful degradation: if voting mechanism fails, default to QUARANTINE
            logger.error("Voting failed for '%s': %s — defaulting to QUARANTINE", action, exc)
            self.events.record("error", details={
                "context": "vote_on_action",
                "action": action,
                "error": str(exc),
            })
            result = {
                "action": action,
                "consensus": "QUARANTINE",
                "reason": f"Voting error: {exc}",
                "votes": votes,
                "voter_ids": [v.sheep_id for v in validators],
                "bft_degraded": True,
            }

        self._log_event("vote", "flock", f"Vote on '{action}': {result['consensus']}")
        self.events.record("vote", details={
            "action": action,
            "consensus": result["consensus"],
            "votes": votes,
            "bft_degraded": bft_degraded,
        })
        return result

    # ── BFT Tolerance ──

    @property
    def bft_tolerance(self) -> int:
        """Maximum Byzantine (malicious/faulty) agents the flock can tolerate.

        BFT requires n >= 3f + 1, so f = (n - 1) // 3.
        """
        n = sum(1 for s in self.sheep.values() if s.state != SheepState.FROZEN)
        return max(0, (n - 1) // 3)

    @property
    def bft_quorum_met(self) -> bool:
        """True if the flock has enough active nodes for f >= 1 BFT tolerance."""
        return self.bft_tolerance >= 1

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

    def flock_health_report(self) -> Dict[str, Any]:
        """Comprehensive health report with per-sheep detail, task stats,
        BFT status, and actionable recommendations.

        Returns a dict with:
            - flock_health_score  (float 0-1)
            - per_sheep           (list of per-agent summaries)
            - task_stats          (success/fail/pending/orphaned counts + rate)
            - bft                 (quorum_met, tolerance, active_non_frozen)
            - recommendations     (list of human-readable suggestions)
        """
        total = len(self.sheep)

        # ── Overall Flock Health Score (0-1) ──
        if total == 0:
            flock_score = 0.0
        else:
            # Weighted average: coherence contributes 60%, availability 40%
            avg_coh = sum(s.coherence for s in self.sheep.values()) / total
            available_ratio = (
                sum(1 for s in self.sheep.values()
                    if s.state not in (SheepState.ISOLATED, SheepState.FROZEN))
                / total
            )
            flock_score = round(0.6 * avg_coh + 0.4 * available_ratio, 4)

        # ── Per-sheep summary ──
        per_sheep: List[Dict[str, Any]] = []
        for s in sorted(self.sheep.values(), key=lambda x: x.sheep_id):
            per_sheep.append({
                "sheep_id": s.sheep_id,
                "name": s.name,
                "role": s.role.value,
                "state": s.state.value,
                "coherence": round(s.coherence, 4),
                "health_label": s.health_label,
                "tasks_completed": s.tasks_completed,
                "tasks_failed": s.tasks_failed,
                "error_rate": round(s.error_rate, 4),
                "current_task": s.current_task,
            })

        # ── Task stats ──
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        pending = sum(1 for t in self.tasks.values() if t.status == "pending")
        active = sum(1 for t in self.tasks.values() if t.status == "active")
        orphaned = sum(1 for t in self.tasks.values() if t.status == "orphaned")
        total_finished = completed + failed
        success_rate = (completed / total_finished) if total_finished > 0 else 1.0

        task_stats = {
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "active": active,
            "orphaned": orphaned,
            "success_rate": round(success_rate, 4),
        }

        # ── BFT status ──
        n_active = sum(
            1 for s in self.sheep.values()
            if s.state != SheepState.FROZEN
        )
        f_tolerance = self.bft_tolerance
        bft = {
            "quorum_met": f_tolerance >= 1,
            "tolerance": f_tolerance,
            "active_non_frozen": n_active,
            "needed_for_next_f": 3 * (f_tolerance + 1) + 1,
        }

        # ── Recommendations ──
        recommendations: List[str] = []
        if total == 0:
            recommendations.append("Flock is empty. Spawn agents to begin operations.")
        else:
            if flock_score < 0.5:
                recommendations.append(
                    "Flock health is critically low. Consider spawning fresh agents "
                    "and retiring degraded ones."
                )
            isolated_count = sum(
                1 for s in self.sheep.values()
                if s.state == SheepState.ISOLATED
            )
            if isolated_count > 0:
                recommendations.append(
                    f"{isolated_count} sheep isolated. Investigate root cause or retire them."
                )
            if orphaned > 0:
                recommendations.append(
                    f"{orphaned} orphaned tasks need redistribution. "
                    "Call redistribute_orphans()."
                )
            if not bft["quorum_met"]:
                needed = bft["needed_for_next_f"] - n_active
                recommendations.append(
                    f"BFT quorum not met (f=0). Spawn {needed} more sheep "
                    f"to achieve f=1 tolerance."
                )
            elif f_tolerance < 2:
                needed = bft["needed_for_next_f"] - n_active
                recommendations.append(
                    f"Spawn {needed} more sheep to restore f={f_tolerance + 1} "
                    f"tolerance (currently f={f_tolerance})."
                )
            # Check for low-coherence validators
            low_validators = [
                s for s in self.sheep.values()
                if s.role == SheepRole.VALIDATOR and s.coherence < COHERENCE_WARN
            ]
            if low_validators:
                recommendations.append(
                    f"{len(low_validators)} validator(s) below warning threshold. "
                    "Governance quality is at risk."
                )

        return {
            "flock_health_score": flock_score,
            "per_sheep": per_sheep,
            "task_stats": task_stats,
            "bft": bft,
            "recommendations": recommendations,
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


# ---------------------------------------------------------------------------
# FlockWatchdog — Auto-Refresh Loop
# ---------------------------------------------------------------------------

class FlockWatchdog:
    """Periodic health scanner that automatically maintains flock integrity.

    The watchdog runs a scan loop (either as a background thread or driven
    manually via ``tick()``) that:

    1. Checks all sheep coherence and auto-isolates those below threshold.
    2. Auto-retires sheep stuck in ISOLATED state beyond a configurable timeout.
    3. Rebalances tasks from failed/isolated sheep to healthy ones.
    4. Logs every action to the flock's FlockEventLog.

    Parameters
    ----------
    flock : Flock
        The flock instance to monitor.
    coherence_threshold : float
        Coherence level below which a sheep is auto-isolated (default 0.30).
    isolation_timeout : float
        Seconds a sheep can remain ISOLATED before being auto-retired (default 300).
    scan_interval : float
        Seconds between automatic scans when running as a background thread
        (default 10).
    """

    def __init__(
        self,
        flock: Flock,
        coherence_threshold: float = 0.30,
        isolation_timeout: float = 300.0,
        scan_interval: float = 10.0,
    ) -> None:
        self.flock = flock
        self.coherence_threshold = coherence_threshold
        self.isolation_timeout = isolation_timeout
        self.scan_interval = scan_interval

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Track when each sheep entered ISOLATED state
        self._isolation_timestamps: Dict[str, float] = {}

    # ── Single Tick ──

    def tick(self, now: Optional[float] = None) -> Dict[str, Any]:
        """Execute a single watchdog scan cycle.

        Returns a summary dict of actions taken.
        """
        if now is None:
            now = time.time()

        actions: Dict[str, Any] = {
            "isolated": [],
            "retired": [],
            "rebalanced": 0,
        }

        # 1. Scan coherence — auto-isolate low-coherence sheep
        for sheep_id, sheep in list(self.flock.sheep.items()):
            if (
                sheep.state not in (SheepState.ISOLATED, SheepState.FROZEN)
                and sheep.coherence < self.coherence_threshold
            ):
                self.flock.isolate(sheep_id)
                self._isolation_timestamps[sheep_id] = now
                actions["isolated"].append(sheep_id)
                self.flock.events.record("watchdog_action", sheep_id, {
                    "action": "auto_isolate",
                    "coherence": sheep.coherence,
                    "threshold": self.coherence_threshold,
                })
                logger.info(
                    "Watchdog: auto-isolated %s (coherence=%.3f < %.3f)",
                    sheep_id, sheep.coherence, self.coherence_threshold,
                )

        # Track newly isolated sheep we haven't seen yet
        for sheep_id, sheep in list(self.flock.sheep.items()):
            if sheep.state == SheepState.ISOLATED and sheep_id not in self._isolation_timestamps:
                self._isolation_timestamps[sheep_id] = now

        # 2. Auto-retire sheep stuck in ISOLATED beyond timeout
        for sheep_id in list(self._isolation_timestamps.keys()):
            sheep = self.flock.sheep.get(sheep_id)
            if sheep is None:
                # Already retired
                self._isolation_timestamps.pop(sheep_id, None)
                continue
            if sheep.state != SheepState.ISOLATED:
                # Recovered
                self._isolation_timestamps.pop(sheep_id, None)
                continue

            elapsed = now - self._isolation_timestamps[sheep_id]
            if elapsed >= self.isolation_timeout:
                # Rebalance tasks before retiring
                rebalanced = self.flock.rebalance_from_failed(sheep_id)
                actions["rebalanced"] += rebalanced

                self.flock.retire(sheep_id)
                actions["retired"].append(sheep_id)
                self._isolation_timestamps.pop(sheep_id, None)
                self.flock.events.record("watchdog_action", sheep_id, {
                    "action": "auto_retire",
                    "elapsed_seconds": elapsed,
                    "timeout": self.isolation_timeout,
                    "rebalanced_tasks": rebalanced,
                })
                logger.info(
                    "Watchdog: auto-retired %s after %.1fs isolation (timeout=%.1fs)",
                    sheep_id, elapsed, self.isolation_timeout,
                )

        # 3. Rebalance any remaining orphaned tasks
        orphan_rebalanced = self.flock.redistribute_orphans()
        actions["rebalanced"] += orphan_rebalanced

        return actions

    # ── Background Thread ──

    def start(self) -> None:
        """Start the watchdog as a daemon background thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.flock.events.record("watchdog_action", details={
            "action": "watchdog_started",
            "scan_interval": self.scan_interval,
        })

    def stop(self) -> None:
        """Stop the background watchdog thread."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.scan_interval + 1)
        self._thread = None
        self.flock.events.record("watchdog_action", details={
            "action": "watchdog_stopped",
        })

    @property
    def is_running(self) -> bool:
        return self._running

    def _run_loop(self) -> None:
        """Internal loop executed by the background thread."""
        while self._running and not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:
                logger.error("Watchdog scan error: %s", exc)
                self.flock.events.record("error", details={
                    "context": "watchdog_scan",
                    "error": str(exc),
                })
            self._stop_event.wait(self.scan_interval)
