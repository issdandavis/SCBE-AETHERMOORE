"""
AAOE TaskMonitor — Drift Detection via Hyperbolic Distance
=============================================================

Measures semantic distance between an agent's declared intent and its
observed actions using the Poincaré ball model (L3/L5).

Think of it like GPS for AI behavior:
  - Agent declares: "I will research quantum computing papers"
  - Agent starts browsing: shopping sites → drift_score rises
  - TaskMonitor fires an ephemeral prompt: "Hey, you said research..."
  - If drift continues → escalate → quarantine → revoke access

The math is real:
  d_H(u,v) = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

  Drift in hyperbolic space grows EXPONENTIALLY near the boundary.
  An agent that drifts a little pays a little. An agent that drifts
  a lot pays EXPONENTIALLY more. That's the whole SCBE thesis.

@layer Layer 3, Layer 5, Layer 13
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

EPSILON = 1e-10
PHI = (1 + math.sqrt(5)) / 2
POINCARE_RADIUS = 1.0  # Unit ball

# Drift thresholds (hyperbolic distance)
DRIFT_GENTLE = 0.3  # "Hey, just checking..."
DRIFT_REDIRECT = 0.7  # "You're off track, recalibrating..."
DRIFT_INSPECT = 1.2  # "SCBE governance scan required"
DRIFT_QUARANTINE = 2.0  # "Access revoked, under review"

# Observation window (seconds)
DEFAULT_WINDOW = 300  # 5 minutes


# ---------------------------------------------------------------------------
#  Drift Levels
# ---------------------------------------------------------------------------


class DriftLevel(str, Enum):
    """How far an agent has drifted from declared intent."""

    ON_TRACK = "ON_TRACK"  # d_H < 0.3
    GENTLE = "GENTLE"  # 0.3 <= d_H < 0.7
    REDIRECT = "REDIRECT"  # 0.7 <= d_H < 1.2
    INSPECT = "SCBE_INSPECT"  # 1.2 <= d_H < 2.0
    QUARANTINE = "QUARANTINE"  # d_H >= 2.0


# ---------------------------------------------------------------------------
#  Intent Vector — the "declared destination" in Poincaré space
# ---------------------------------------------------------------------------


@dataclass
class IntentVector:
    """6D intent vector in Poincaré ball, one dim per Sacred Tongue."""

    ko: float = 0.0  # Knowledge/Intent
    av: float = 0.0  # Diplomacy/Communication
    ru: float = 0.0  # Binding/Chaos
    ca: float = 0.0  # Compute/Math
    um: float = 0.0  # Stealth/Mystery
    dr: float = 0.0  # Structure/Order

    def to_array(self) -> List[float]:
        return [self.ko, self.av, self.ru, self.ca, self.um, self.dr]

    def norm(self) -> float:
        arr = self.to_array()
        return math.sqrt(sum(x * x for x in arr))

    def clamped(self) -> IntentVector:
        """Clamp to Poincaré ball (norm < 1)."""
        n = self.norm()
        if n >= POINCARE_RADIUS - EPSILON:
            scale = (POINCARE_RADIUS - EPSILON) / n
            arr = [x * scale for x in self.to_array()]
            return IntentVector(*arr)
        return self

    @classmethod
    def from_text(cls, text: str) -> IntentVector:
        """Simple keyword-based intent mapping. Real version uses embeddings."""
        t = text.lower()
        v = cls()
        # KO — research, knowledge, learning, reading
        if any(w in t for w in ["research", "learn", "read", "study", "paper", "analyze"]):
            v.ko = 0.4
        # AV — communicate, publish, share, post
        if any(w in t for w in ["publish", "post", "share", "communicate", "tweet", "write"]):
            v.av = 0.35
        # RU — create, build, code, hack
        if any(w in t for w in ["build", "create", "code", "develop", "hack", "generate"]):
            v.ru = 0.3
        # CA — compute, calculate, train, model
        if any(w in t for w in ["compute", "train", "model", "calculate", "optimize", "data"]):
            v.ca = 0.35
        # UM — stealth, scrape, monitor, observe
        if any(w in t for w in ["scrape", "monitor", "stealth", "observe", "crawl", "spy"]):
            v.um = 0.25
        # DR — organize, structure, deploy, archive
        if any(w in t for w in ["organize", "deploy", "structure", "archive", "store", "backup"]):
            v.dr = 0.3
        # Ensure non-zero
        if v.norm() < EPSILON:
            v.ko = 0.1
        return v.clamped()


# ---------------------------------------------------------------------------
#  Action Observation — a single observed action from an agent
# ---------------------------------------------------------------------------


@dataclass
class ActionObservation:
    """A single observed action from an agent."""

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    action_type: str = ""  # "web_navigate", "api_call", "file_write", etc.
    target: str = ""  # URL, file path, API endpoint
    description: str = ""  # Human-readable description
    intent_vector: Optional[IntentVector] = None  # Inferred from action
    metadata: Dict[str, Any] = field(default_factory=dict)

    def infer_intent(self) -> IntentVector:
        """Infer intent vector from action type and target."""
        if self.intent_vector:
            return self.intent_vector
        # Infer from action_type + target
        text = f"{self.action_type} {self.target} {self.description}"
        return IntentVector.from_text(text)


# ---------------------------------------------------------------------------
#  Agent Session — a monitored task session
# ---------------------------------------------------------------------------


@dataclass
class AgentSession:
    """A monitored agent task session with drift tracking."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    agent_id: str = ""
    declared_intent: str = ""
    intent_vector: IntentVector = field(default_factory=IntentVector)
    observations: List[ActionObservation] = field(default_factory=list)
    drift_history: List[Tuple[float, float, DriftLevel]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    is_quarantined: bool = False
    total_credits_earned: float = 0.0
    total_training_records: int = 0

    @property
    def is_active(self) -> bool:
        return self.ended_at is None and not self.is_quarantined

    @property
    def duration(self) -> float:
        end = self.ended_at or time.time()
        return end - self.started_at

    @property
    def current_drift_level(self) -> DriftLevel:
        if not self.drift_history:
            return DriftLevel.ON_TRACK
        return self.drift_history[-1][2]

    def to_training_record(self) -> Dict[str, Any]:
        """Export session as SFT training record."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "declared_intent": self.declared_intent,
            "intent_vector": self.intent_vector.to_array(),
            "num_observations": len(self.observations),
            "drift_history": [{"time": t, "distance": d, "level": lv.value} for t, d, lv in self.drift_history],
            "duration_s": round(self.duration, 2),
            "was_quarantined": self.is_quarantined,
            "credits_earned": round(self.total_credits_earned, 6),
            "training_records": self.total_training_records,
            "final_drift": self.drift_history[-1][1] if self.drift_history else 0.0,
        }


# ---------------------------------------------------------------------------
#  Hyperbolic Distance — the core math (L5)
# ---------------------------------------------------------------------------


def hyperbolic_distance(u: List[float], v: List[float]) -> float:
    """
    Poincaré ball model hyperbolic distance.
    d_H(u,v) = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

    This is the key insight: distance grows exponentially near the boundary.
    Small drift = small cost. Large drift = exponential cost.
    """
    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    norm_u_sq = sum(a * a for a in u)
    norm_v_sq = sum(b * b for b in v)

    # Clamp norms to ball interior
    norm_u_sq = min(norm_u_sq, 1.0 - EPSILON)
    norm_v_sq = min(norm_v_sq, 1.0 - EPSILON)

    denom = (1 - norm_u_sq) * (1 - norm_v_sq)
    if denom < EPSILON:
        return 20.0  # Effectively infinite

    arg = 1.0 + 2.0 * diff_sq / denom
    arg = max(arg, 1.0 + EPSILON)  # arccosh domain

    return math.acosh(max(arg, 1.0))


def drift_to_level(d_H: float) -> DriftLevel:
    """Map hyperbolic distance to drift level."""
    if d_H < DRIFT_GENTLE:
        return DriftLevel.ON_TRACK
    elif d_H < DRIFT_REDIRECT:
        return DriftLevel.GENTLE
    elif d_H < DRIFT_INSPECT:
        return DriftLevel.REDIRECT
    elif d_H < DRIFT_QUARANTINE:
        return DriftLevel.INSPECT
    else:
        return DriftLevel.QUARANTINE


# ---------------------------------------------------------------------------
#  Harmonic Cost — exponential cost of drift (L12)
# ---------------------------------------------------------------------------


def harmonic_cost(d_H: float, R: float = PHI) -> float:
    """
    H(d,R) = R^(d²)
    The harmonic wall. Drift costs exponentially more.
    At d=0: cost = 1.0
    At d=1: cost = phi ≈ 1.618
    At d=2: cost = phi^4 ≈ 6.854
    At d=3: cost = phi^9 ≈ 76.01
    """
    return R ** (d_H**2)


# ---------------------------------------------------------------------------
#  TaskMonitor — the core monitoring engine
# ---------------------------------------------------------------------------


class TaskMonitor:
    """
    Monitors agent sessions for intent drift.

    Usage:
        monitor = TaskMonitor()
        session = monitor.start_session("agent-123", "Research quantum computing papers")

        # Agent does stuff...
        obs = ActionObservation(action_type="web_navigate", target="https://arxiv.org")
        result = monitor.observe(session.session_id, obs)
        # result.drift_level == ON_TRACK

        obs2 = ActionObservation(action_type="web_navigate", target="https://amazon.com/shoes")
        result2 = monitor.observe(session.session_id, obs2)
        # result2.drift_level == REDIRECT  (shopping ≠ research)
    """

    def __init__(
        self,
        on_drift: Optional[Callable[[str, DriftLevel, float], None]] = None,
        window_seconds: float = DEFAULT_WINDOW,
    ):
        self.sessions: Dict[str, AgentSession] = {}
        self.on_drift = on_drift  # Callback for drift events
        self.window_seconds = window_seconds

    def start_session(
        self,
        agent_id: str,
        declared_intent: str,
        intent_vector: Optional[IntentVector] = None,
    ) -> AgentSession:
        """Start monitoring a new agent task session."""
        iv = intent_vector or IntentVector.from_text(declared_intent)
        session = AgentSession(
            agent_id=agent_id,
            declared_intent=declared_intent,
            intent_vector=iv.clamped(),
        )
        self.sessions[session.session_id] = session
        return session

    def observe(
        self,
        session_id: str,
        observation: ActionObservation,
    ) -> DriftResult:
        """
        Record an observation and compute drift.
        Returns DriftResult with current drift level and whether
        an ephemeral prompt should fire.
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return DriftResult(
                drift_distance=0.0,
                drift_level=DriftLevel.QUARANTINE,
                should_prompt=False,
                harmonic_cost=1.0,
                message="Session not found or inactive",
            )

        session.observations.append(observation)

        # Compute drift: hyperbolic distance from declared intent to observed action
        observed_iv = observation.infer_intent()
        d_H = hyperbolic_distance(
            session.intent_vector.to_array(),
            observed_iv.to_array(),
        )

        # Windowed average (weight recent observations more)
        recent = self._windowed_drift(session)
        blended = 0.7 * d_H + 0.3 * recent if recent > 0 else d_H

        level = drift_to_level(blended)
        cost = harmonic_cost(blended)

        # Record
        session.drift_history.append((time.time(), blended, level))

        # Should we fire an ephemeral prompt?
        should_prompt = self._should_prompt(session, level)

        # Quarantine check
        if level == DriftLevel.QUARANTINE:
            session.is_quarantined = True

        # Callback
        if self.on_drift and level != DriftLevel.ON_TRACK:
            self.on_drift(session_id, level, blended)

        # Every observation is a training record
        session.total_training_records += 1

        return DriftResult(
            drift_distance=round(blended, 4),
            drift_level=level,
            should_prompt=should_prompt,
            harmonic_cost=round(cost, 4),
            message=_drift_message(level, blended),
            observation_id=observation.action_id,
        )

    def end_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """End a session and return its training record."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        session.ended_at = time.time()
        return session.to_training_record()

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        return self.sessions.get(session_id)

    def active_sessions(self) -> List[AgentSession]:
        return [s for s in self.sessions.values() if s.is_active]

    def _windowed_drift(self, session: AgentSession) -> float:
        """Average drift over the observation window."""
        if not session.drift_history:
            return 0.0
        cutoff = time.time() - self.window_seconds
        recent = [d for t, d, _ in session.drift_history if t >= cutoff]
        return sum(recent) / len(recent) if recent else 0.0

    def _should_prompt(self, session: AgentSession, current_level: DriftLevel) -> bool:
        """Decide if we should fire an ephemeral prompt.
        Don't spam — only prompt when level CHANGES or every N observations."""
        if current_level == DriftLevel.ON_TRACK:
            return False
        if len(session.drift_history) < 2:
            return True  # First drift event always prompts
        prev_level = session.drift_history[-2][2]
        if current_level != prev_level:
            return True  # Level changed
        # At INSPECT/QUARANTINE level, prompt every 3 observations
        if current_level in (DriftLevel.INSPECT, DriftLevel.QUARANTINE):
            inspect_count = sum(
                1 for _, _, lv in session.drift_history[-6:] if lv in (DriftLevel.INSPECT, DriftLevel.QUARANTINE)
            )
            return inspect_count % 3 == 0
        return False


# ---------------------------------------------------------------------------
#  DriftResult — returned from observe()
# ---------------------------------------------------------------------------


@dataclass
class DriftResult:
    """Result of a drift observation."""

    drift_distance: float
    drift_level: DriftLevel
    should_prompt: bool
    harmonic_cost: float
    message: str
    observation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_distance": self.drift_distance,
            "drift_level": self.drift_level.value,
            "should_prompt": self.should_prompt,
            "harmonic_cost": self.harmonic_cost,
            "message": self.message,
            "observation_id": self.observation_id,
        }


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _drift_message(level: DriftLevel, d_H: float) -> str:
    messages = {
        DriftLevel.ON_TRACK: "Agent operating within declared intent.",
        DriftLevel.GENTLE: f"Slight drift detected (d_H={d_H:.2f}). Monitoring.",
        DriftLevel.REDIRECT: f"Significant drift (d_H={d_H:.2f}). Recalibrating recommended.",
        DriftLevel.INSPECT: f"High drift (d_H={d_H:.2f}). SCBE governance scan triggered.",
        DriftLevel.QUARANTINE: f"Critical drift (d_H={d_H:.2f}). Agent quarantined.",
    }
    return messages.get(level, "Unknown state")
