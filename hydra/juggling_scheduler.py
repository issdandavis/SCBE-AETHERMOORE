"""
Juggling Agent Coordination Scheduler — Python reference implementation.

Models multi-agent task coordination as a physics juggling system.

Core mapping:
    balls   -> TaskCapsules (units of work in flight)
    hands   -> AgentSlots (bounded execution capacity)
    throws  -> structured handoffs with predicted catch windows
    arcs    -> latency/deadline envelopes
    rhythm  -> scheduler cadence / phase locking
    drops   -> timeout / failure / lost context
    pattern -> orchestration policy (siteswap notation)

Seven juggling rules:
    1. Never throw to an unready hand
    2. Every throw needs a predicted catch window
    3. High-inertia tasks have fewer handoffs
    4. Higher arcs for risky tasks (more validation slack)
    5. Detect phase drift early
    6. Build interception paths (backup handlers)
    7. Ledger catches, not just throws

Layer 13 integration: Risk decision (ALLOW / QUARANTINE / ESCALATE / DENY)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class FlightState(str, Enum):
    """Flight state of a task capsule through the juggling system."""
    HELD = "held"
    THROWN = "thrown"
    CAUGHT = "caught"
    VALIDATING = "validating"
    RECOVERING = "recovering"
    DROPPED = "dropped"
    DONE = "done"


GOVERNANCE_TIERS = ("KO", "AV", "RU", "CA", "UM", "DR")

DEFAULT_SCORE_WEIGHTS = {
    "reliability": 2.0,
    "trust_alignment": 1.0,
    "time_slack": 0.5,
    "inertia_penalty": 1.5,
    "risk_penalty": 1.2,
    "load_penalty": 2.0,
    "latency_penalty": 0.001,
}

DEFAULT_GRAVITY_LAMBDA = 0.05
MAX_RETRIES = 3
PHASE_DRIFT_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Core Data Types
# ---------------------------------------------------------------------------

@dataclass
class TaskCapsule:
    """A unit of work in flight through the juggling system."""

    task_id: str
    payload_ref: str
    priority: float
    trust_score: float
    inertia: float
    risk: float
    created_at: float
    deadline_at: float
    owner: Optional[str] = None
    next_candidates: List[str] = field(default_factory=list)
    fallback_candidates: List[str] = field(default_factory=list)
    state: FlightState = FlightState.HELD
    retry_count: int = 0
    required_quorum: int = 1
    integrity_hash: Optional[str] = None
    required_tier: str = "KO"
    arc_height: int = 3
    last_transition_at: float = 0.0
    provenance: List[Tuple[str, float, FlightState]] = field(default_factory=list)


@dataclass
class AgentSlot:
    """An agent's execution capacity in the juggling system."""

    agent_id: str
    roles: List[str]
    catch_capacity: int
    current_load: int
    reliability: float
    trust_domains: List[str]
    avg_latency_ms: float
    last_catch_at: float = 0.0
    consecutive_misses: int = 0

    def can_catch(self, task: TaskCapsule, now: float) -> bool:
        """Rule 1: Check if this agent can catch the given task."""
        if self.current_load >= self.catch_capacity:
            return False
        if now + self.avg_latency_ms / 1000.0 > task.deadline_at:
            return False
        required_idx = GOVERNANCE_TIERS.index(task.required_tier) if task.required_tier in GOVERNANCE_TIERS else 0
        max_agent_idx = max(
            (GOVERNANCE_TIERS.index(t) for t in self.trust_domains if t in GOVERNANCE_TIERS),
            default=-1,
        )
        if max_agent_idx < required_idx:
            return False
        return True


@dataclass
class HandoffReceipt:
    """Explicit ACK when an agent catches a task (Rule 7)."""

    task_id: str
    receiver_id: str
    sender_id: str
    timestamp: float
    integrity_verified: bool
    feasibility_confirmed: bool
    new_owner: str


@dataclass
class JugglingEvent:
    """Scheduler event for audit and observability."""

    type: str  # throw | catch | drop | intercept | validate | complete | phase_drift | capacity_warning
    task_id: str
    agent_id: Optional[str]
    timestamp: float
    data: dict


@dataclass
class SchedulerMetrics:
    """Real-time health of the juggling pattern."""

    in_flight: int
    held: int
    drops: int
    catches: int
    phase_drift: float
    avg_arc_time_ms: float
    cadence_health: float


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def assignment_score(
    task: TaskCapsule,
    agent: AgentSlot,
    now: float,
    weights: Optional[dict] = None,
) -> float:
    """Compute assignment score for a (task, agent) pair. Higher = better."""
    w = weights or DEFAULT_SCORE_WEIGHTS
    time_left = max(task.deadline_at - now, 1e-6)
    load_ratio = agent.current_load / max(agent.catch_capacity, 1)

    required_idx = GOVERNANCE_TIERS.index(task.required_tier) if task.required_tier in GOVERNANCE_TIERS else 0
    max_agent_idx = max(
        (GOVERNANCE_TIERS.index(t) for t in agent.trust_domains if t in GOVERNANCE_TIERS),
        default=-1,
    )
    mismatch = 0 if max_agent_idx >= required_idx else (required_idx - max_agent_idx) / len(GOVERNANCE_TIERS)

    return (
        w["reliability"] * agent.reliability
        + w["trust_alignment"] * task.trust_score
        - w["inertia_penalty"] * task.inertia
        - w["risk_penalty"] * task.risk * (mismatch + 0.1)
        - w["load_penalty"] * load_ratio
        - w["latency_penalty"] * agent.avg_latency_ms
        + w["time_slack"] * math.log1p(time_left / 1.0)
    )


def recoverability(task: TaskCapsule, now: float, lam: float = DEFAULT_GRAVITY_LAMBDA) -> float:
    """Compute recoverability: U(t) = e^(-lambda * elapsed). Returns [0, 1]."""
    elapsed = max(now - task.created_at, 0)
    return math.exp(-lam * elapsed)


def select_arc_height(risk: float, inertia: float) -> int:
    """Select arc height based on risk and inertia (Rules 3 & 4)."""
    composite = 0.6 * risk + 0.4 * inertia
    if composite >= 0.8:
        return 7
    if composite >= 0.6:
        return 5
    if composite >= 0.3:
        return 3
    if composite >= 0.1:
        return 2
    return 1


# ---------------------------------------------------------------------------
# Juggling Scheduler
# ---------------------------------------------------------------------------

class JugglingScheduler:
    """
    Governed task-flight coordinator.

    Work capsules move between specialized agents along predicted arcs,
    with explicit catches, bounded capacity, phase timing, and recovery
    on missed handoffs.
    """

    def __init__(
        self,
        weights: Optional[dict] = None,
        gravity_lambda: float = DEFAULT_GRAVITY_LAMBDA,
    ):
        self._capsules: Dict[str, TaskCapsule] = {}
        self._agents: Dict[str, AgentSlot] = {}
        self._event_log: List[JugglingEvent] = []
        self._receipt_log: List[HandoffReceipt] = []
        self._weights = weights or DEFAULT_SCORE_WEIGHTS
        self._gravity_lambda = gravity_lambda

    # ---- Agent Management ----

    def register_agent(self, slot: AgentSlot) -> None:
        """Register an agent slot."""
        self._agents[slot.agent_id] = slot

    def remove_agent(self, agent_id: str) -> List[TaskCapsule]:
        """Remove an agent. Tasks held by it enter RECOVERING."""
        self._agents.pop(agent_id, None)
        orphaned: List[TaskCapsule] = []
        for capsule in self._capsules.values():
            if capsule.owner == agent_id and capsule.state != FlightState.DONE:
                capsule.state = FlightState.RECOVERING
                capsule.last_transition_at = time.time()
                capsule.owner = None
                orphaned.append(capsule)
        return orphaned

    def get_agent(self, agent_id: str) -> Optional[AgentSlot]:
        return self._agents.get(agent_id)

    # ---- Capsule Management ----

    def add_capsule(self, capsule: TaskCapsule) -> None:
        self._capsules[capsule.task_id] = capsule

    def get_capsule(self, task_id: str) -> Optional[TaskCapsule]:
        return self._capsules.get(task_id)

    def get_capsules_by_state(self, state: FlightState) -> List[TaskCapsule]:
        return [c for c in self._capsules.values() if c.state == state]

    # ---- Core Scheduling ----

    def find_best_receiver(self, capsule: TaskCapsule) -> Optional[AgentSlot]:
        """Rule 1 & 2: Find the best agent for a capsule."""
        now = time.time()

        if capsule.next_candidates:
            candidates = [self._agents[aid] for aid in capsule.next_candidates if aid in self._agents]
        else:
            candidates = list(self._agents.values())

        eligible = [a for a in candidates if a.can_catch(capsule, now)]

        if not eligible:
            # Rule 6: try fallback / interception
            fallbacks = [self._agents[aid] for aid in capsule.fallback_candidates if aid in self._agents]
            eligible = [a for a in fallbacks if a.can_catch(capsule, now)]
            if not eligible:
                return None

        return self._pick_best(eligible, capsule, now)

    def throw_capsule(self, task_id: str) -> Optional[HandoffReceipt]:
        """Throw a capsule to the best available agent."""
        capsule = self._capsules.get(task_id)
        if capsule is None:
            return None

        receiver = self.find_best_receiver(capsule)
        if receiver is None:
            if capsule.state != FlightState.DROPPED:
                capsule.state = FlightState.RECOVERING
                capsule.last_transition_at = time.time()
            return None

        sender_id = capsule.owner or "__scheduler__"
        now = time.time()

        capsule.state = FlightState.THROWN
        capsule.last_transition_at = now

        capsule.state = FlightState.CAUGHT
        capsule.last_transition_at = now
        capsule.owner = receiver.agent_id
        receiver.current_load += 1
        receiver.consecutive_misses = 0
        receiver.last_catch_at = now

        capsule.provenance.append((receiver.agent_id, now, FlightState.CAUGHT))

        receipt = HandoffReceipt(
            task_id=capsule.task_id,
            receiver_id=receiver.agent_id,
            sender_id=sender_id,
            timestamp=now,
            integrity_verified=capsule.integrity_hash is not None,
            feasibility_confirmed=True,
            new_owner=receiver.agent_id,
        )
        self._receipt_log.append(receipt)

        self._emit(JugglingEvent(
            type="catch",
            task_id=capsule.task_id,
            agent_id=receiver.agent_id,
            timestamp=now,
            data={"sender_id": sender_id, "arc_height": capsule.arc_height},
        ))

        if capsule.required_quorum > 1:
            capsule.state = FlightState.VALIDATING
            capsule.last_transition_at = now

        return receipt

    def complete_capsule(self, task_id: str) -> bool:
        """Mark a capsule as complete. Frees the agent's slot."""
        capsule = self._capsules.get(task_id)
        if capsule is None:
            return False

        if capsule.owner:
            agent = self._agents.get(capsule.owner)
            if agent and agent.current_load > 0:
                agent.current_load -= 1

        now = time.time()
        capsule.state = FlightState.DONE
        capsule.last_transition_at = now
        capsule.provenance.append((capsule.owner or "__none__", now, FlightState.DONE))

        self._emit(JugglingEvent(
            type="complete",
            task_id=task_id,
            agent_id=capsule.owner,
            timestamp=now,
            data={"retry_count": capsule.retry_count},
        ))
        return True

    def handle_drop(self, task_id: str) -> Optional[HandoffReceipt]:
        """Handle a drop: retry or permanent drop (Rule 3)."""
        capsule = self._capsules.get(task_id)
        if capsule is None:
            return None

        if capsule.owner:
            prev = self._agents.get(capsule.owner)
            if prev:
                if prev.current_load > 0:
                    prev.current_load -= 1
                prev.consecutive_misses += 1

        capsule.retry_count += 1
        capsule.owner = None
        now = time.time()

        self._emit(JugglingEvent(
            type="drop",
            task_id=task_id,
            agent_id=None,
            timestamp=now,
            data={"retry_count": capsule.retry_count},
        ))

        # Rule 3: high-inertia or max retries → permanent drop
        if capsule.retry_count >= MAX_RETRIES or (capsule.inertia > 0.7 and capsule.retry_count >= 2):
            capsule.state = FlightState.DROPPED
            capsule.last_transition_at = now
            return None

        capsule.state = FlightState.RECOVERING
        capsule.last_transition_at = now
        return self.throw_capsule(task_id)

    # ---- Phase Monitoring ----

    def detect_phase_drift(self) -> float:
        """Rule 5: Detect phase drift. Returns overdue ratio."""
        now = time.time()
        in_flight = self.get_capsules_by_state(FlightState.THROWN)
        recovering = self.get_capsules_by_state(FlightState.RECOVERING)
        all_active = in_flight + recovering

        if not all_active:
            return 0.0

        overdue = sum(1 for c in all_active if now > c.deadline_at)
        drift = overdue / len(all_active)

        if drift >= PHASE_DRIFT_THRESHOLD:
            self._emit(JugglingEvent(
                type="phase_drift",
                task_id="__system__",
                agent_id=None,
                timestamp=now,
                data={"drift": drift, "overdue_count": overdue, "total": len(all_active)},
            ))

        return drift

    # ---- Metrics ----

    def get_metrics(self) -> SchedulerMetrics:
        """Get current scheduler health metrics."""
        all_capsules = list(self._capsules.values())
        in_flight = sum(1 for c in all_capsules if c.state == FlightState.THROWN)
        held = sum(1 for c in all_capsules if c.state in (FlightState.HELD, FlightState.CAUGHT, FlightState.VALIDATING))
        drops = sum(1 for c in all_capsules if c.state == FlightState.DROPPED)
        done = sum(1 for c in all_capsules if c.state == FlightState.DONE)

        avg_arc = 0.0
        if self._receipt_log:
            recent = self._receipt_log[-50:]
            times = []
            for r in recent:
                c = self._capsules.get(r.task_id)
                if c:
                    times.append((r.timestamp - c.created_at) * 1000)
            if times:
                avg_arc = sum(times) / len(times)

        drift = self.detect_phase_drift()
        total = len(all_capsules) or 1

        return SchedulerMetrics(
            in_flight=in_flight,
            held=held,
            drops=drops,
            catches=done,
            phase_drift=drift,
            avg_arc_time_ms=avg_arc,
            cadence_health=max(0.0, 1.0 - drift - drops / total),
        )

    # ---- Tick ----

    def tick(self) -> SchedulerMetrics:
        """Tick the scheduler: expire, recover, assign, check phase."""
        now = time.time()

        for capsule in list(self._capsules.values()):
            if capsule.state in (FlightState.DONE, FlightState.DROPPED):
                continue
            if now > capsule.deadline_at:
                self.handle_drop(capsule.task_id)

        for capsule in self.get_capsules_by_state(FlightState.HELD):
            if capsule.owner is None:
                self.throw_capsule(capsule.task_id)

        for capsule in self.get_capsules_by_state(FlightState.RECOVERING):
            self.throw_capsule(capsule.task_id)

        return self.get_metrics()

    # ---- Siteswap Encoding ----

    def encode_siteswap(self, task_id: str) -> str:
        """Encode a capsule's journey as a siteswap-like string."""
        capsule = self._capsules.get(task_id)
        if capsule is None:
            return ""
        parts: List[str] = []
        for _, _, state in capsule.provenance:
            if state == FlightState.CAUGHT:
                parts.append(str(capsule.arc_height))
            elif state == FlightState.VALIDATING:
                parts.append(f"{capsule.arc_height}Q")
            elif state == FlightState.DONE:
                parts.append("0")
        return " -> ".join(parts)

    # ---- Events ----

    @property
    def events(self) -> List[JugglingEvent]:
        return list(self._event_log)

    @property
    def receipts(self) -> List[HandoffReceipt]:
        return list(self._receipt_log)

    # ---- Internal ----

    def _pick_best(self, eligible: List[AgentSlot], capsule: TaskCapsule, now: float) -> AgentSlot:
        best = eligible[0]
        best_score = -math.inf
        for agent in eligible:
            score = assignment_score(capsule, agent, now, self._weights)
            if score > best_score:
                best_score = score
                best = agent
        return best

    def _emit(self, event: JugglingEvent) -> None:
        self._event_log.append(event)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_capsule(
    task_id: str,
    payload_ref: str,
    priority: float = 2.0,
    trust_score: float = 0.5,
    inertia: float = 0.2,
    risk: float = 0.2,
    deadline_sec: float = 30.0,
    next_candidates: Optional[List[str]] = None,
    fallback_candidates: Optional[List[str]] = None,
    required_quorum: int = 1,
    required_tier: str = "KO",
    integrity_hash: Optional[str] = None,
) -> TaskCapsule:
    """Create a new TaskCapsule with sensible defaults."""
    now = time.time()
    return TaskCapsule(
        task_id=task_id,
        payload_ref=payload_ref,
        priority=priority,
        trust_score=trust_score,
        inertia=inertia,
        risk=risk,
        created_at=now,
        deadline_at=now + deadline_sec,
        next_candidates=next_candidates or [],
        fallback_candidates=fallback_candidates or [],
        required_quorum=required_quorum,
        integrity_hash=integrity_hash,
        required_tier=required_tier,
        arc_height=select_arc_height(risk, inertia),
        last_transition_at=now,
    )
