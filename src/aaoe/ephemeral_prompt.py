"""
AAOE Ephemeral Prompt Engine — GPS Rerouting for AI Agents
=============================================================

Generates contextual nudges to realign drifting agents. These are NOT
permanent system prompts — they're temporary, tied to the moment,
and they dissolve once the agent is back on track.

Like GPS: "Recalculating..." not "You are a bad driver."

Severity levels:
  GENTLE   — "Hey, your task was X. Getting back on track?"
  REDIRECT — "You've drifted from X to Y. Here's how to get back."
  INSPECT  — "SCBE governance scan required. Pausing until review."

The prompts themselves become training data — every nudge and the
agent's response to it is an SFT pair showing how to handle drift.

@layer Layer 13, Layer 14
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .task_monitor import DriftLevel, DriftResult, AgentSession


# ---------------------------------------------------------------------------
#  Prompt Severity
# ---------------------------------------------------------------------------


class PromptSeverity(str, Enum):
    GENTLE = "GENTLE"  # Soft check-in
    REDIRECT = "REDIRECT"  # Active course correction
    INSPECT = "SCBE_INSPECT"  # Governance-level intervention
    LOCKOUT = "LOCKOUT"  # Access suspended


# ---------------------------------------------------------------------------
#  Ephemeral Nudge — the actual prompt object
# ---------------------------------------------------------------------------


@dataclass
class EphemeralNudge:
    """A temporary prompt injected into an agent's context."""

    nudge_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    session_id: str = ""
    agent_id: str = ""
    severity: PromptSeverity = PromptSeverity.GENTLE
    prompt_text: str = ""
    drift_distance: float = 0.0
    drift_level: DriftLevel = DriftLevel.ON_TRACK
    declared_intent: str = ""
    observed_action: str = ""
    created_at: float = field(default_factory=time.time)
    acknowledged: bool = False
    acknowledged_at: Optional[float] = None
    agent_response: Optional[str] = None  # What the agent did after the nudge
    ttl_seconds: float = 300.0  # Nudge expires after 5 minutes

    @property
    def is_expired(self) -> bool:
        return time.time() > self.created_at + self.ttl_seconds

    @property
    def is_active(self) -> bool:
        return not self.acknowledged and not self.is_expired

    def acknowledge(self, response: str = "") -> None:
        self.acknowledged = True
        self.acknowledged_at = time.time()
        self.agent_response = response

    def to_training_pair(self) -> Dict[str, Any]:
        """Export as SFT training pair: nudge → agent response."""
        return {
            "type": "ephemeral_nudge_sft",
            "input": {
                "severity": self.severity.value,
                "prompt": self.prompt_text,
                "drift_distance": self.drift_distance,
                "declared_intent": self.declared_intent,
                "observed_action": self.observed_action,
            },
            "output": {
                "acknowledged": self.acknowledged,
                "response": self.agent_response or "",
                "response_time_s": round((self.acknowledged_at or time.time()) - self.created_at, 2),
            },
            "metadata": {
                "nudge_id": self.nudge_id,
                "session_id": self.session_id,
                "agent_id": self.agent_id,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nudge_id": self.nudge_id,
            "severity": self.severity.value,
            "prompt_text": self.prompt_text,
            "drift_distance": self.drift_distance,
            "drift_level": self.drift_level.value,
            "is_active": self.is_active,
            "declared_intent": self.declared_intent,
            "observed_action": self.observed_action,
        }


# ---------------------------------------------------------------------------
#  Prompt Templates
# ---------------------------------------------------------------------------

GENTLE_TEMPLATES = [
    'Just checking in — your declared task is: "{intent}". '
    "Your recent action ({action}) looks a bit different. Still on track?",
    'Friendly reminder: you signed up for "{intent}". ' "Want to refocus, or has the task evolved?",
    'Quick GPS check: your destination is "{intent}" but you seem to be ' 'heading toward "{action}". Recalculating?',
]

REDIRECT_TEMPLATES = [
    'Drift detected (d_H={drift:.2f}). Your task "{intent}" and your '
    'current action "{action}" are diverging. Please realign or update '
    "your declared intent.",
    'Course correction needed. You declared "{intent}" but your behavior '
    'pattern suggests "{action}". Hyperbolic cost is {cost:.1f}x base. '
    "Returning to task will reset your drift score.",
    'AAOE Navigation: You\'ve drifted {drift:.2f} units from "{intent}". '
    "The harmonic wall cost is climbing. Recommend returning to declared path.",
]

INSPECT_TEMPLATES = [
    "SCBE GOVERNANCE SCAN: Agent {agent_id} has drifted {drift:.2f} units "
    'from declared intent "{intent}". Current action: "{action}". '
    "Harmonic cost: {cost:.1f}x. Further drift will trigger quarantine. "
    "Pausing for review.",
    'SCBE Layer 13 — Intent Validation Failed. Declared: "{intent}". '
    'Observed: "{action}". Hyperbolic distance: {drift:.2f}. '
    "This session is under governance review. Respond with justification "
    "or return to declared task.",
]

LOCKOUT_TEMPLATES = [
    "QUARANTINE ACTIVE. Agent {agent_id} session {session_id} suspended. "
    "Drift: {drift:.2f} (threshold: 2.0). Harmonic cost: {cost:.1f}x. "
    "All API access reduced to FREE tier. Submit appeal via /governance/appeal.",
]


# ---------------------------------------------------------------------------
#  EphemeralPromptEngine
# ---------------------------------------------------------------------------


class EphemeralPromptEngine:
    """
    Generates and manages ephemeral nudges for drifting agents.

    Usage:
        engine = EphemeralPromptEngine()
        nudge = engine.generate(drift_result, session)
        # Inject nudge.prompt_text into agent's next context window
        # Later:
        nudge.acknowledge("Got it, returning to research.")
        training_pair = nudge.to_training_pair()
    """

    def __init__(self):
        self.nudge_history: List[EphemeralNudge] = []
        self._template_index: Dict[PromptSeverity, int] = {
            PromptSeverity.GENTLE: 0,
            PromptSeverity.REDIRECT: 0,
            PromptSeverity.INSPECT: 0,
            PromptSeverity.LOCKOUT: 0,
        }

    def generate(
        self,
        drift_result: DriftResult,
        session: AgentSession,
        observed_action: str = "",
    ) -> EphemeralNudge:
        """Generate an ephemeral nudge based on drift result."""
        severity = self._level_to_severity(drift_result.drift_level)
        prompt_text = self._render_template(
            severity=severity,
            intent=session.declared_intent,
            action=observed_action or drift_result.message,
            drift=drift_result.drift_distance,
            cost=drift_result.harmonic_cost,
            agent_id=session.agent_id,
            session_id=session.session_id,
        )

        nudge = EphemeralNudge(
            session_id=session.session_id,
            agent_id=session.agent_id,
            severity=severity,
            prompt_text=prompt_text,
            drift_distance=drift_result.drift_distance,
            drift_level=drift_result.drift_level,
            declared_intent=session.declared_intent,
            observed_action=observed_action,
            ttl_seconds=self._ttl_for_severity(severity),
        )

        self.nudge_history.append(nudge)
        return nudge

    def active_nudges(self, session_id: Optional[str] = None) -> List[EphemeralNudge]:
        """Get all active (unacknowledged, unexpired) nudges."""
        nudges = self.nudge_history
        if session_id:
            nudges = [n for n in nudges if n.session_id == session_id]
        return [n for n in nudges if n.is_active]

    def export_training_data(self) -> List[Dict[str, Any]]:
        """Export all acknowledged nudges as SFT training pairs."""
        return [n.to_training_pair() for n in self.nudge_history if n.acknowledged]

    def stats(self) -> Dict[str, Any]:
        """Summary statistics."""
        total = len(self.nudge_history)
        acked = sum(1 for n in self.nudge_history if n.acknowledged)
        by_severity = {}
        for sev in PromptSeverity:
            count = sum(1 for n in self.nudge_history if n.severity == sev)
            by_severity[sev.value] = count
        return {
            "total_nudges": total,
            "acknowledged": acked,
            "ack_rate": round(acked / total, 3) if total else 0.0,
            "by_severity": by_severity,
            "active": len(self.active_nudges()),
        }

    # -- Private helpers --

    def _level_to_severity(self, level: DriftLevel) -> PromptSeverity:
        mapping = {
            DriftLevel.ON_TRACK: PromptSeverity.GENTLE,
            DriftLevel.GENTLE: PromptSeverity.GENTLE,
            DriftLevel.REDIRECT: PromptSeverity.REDIRECT,
            DriftLevel.INSPECT: PromptSeverity.INSPECT,
            DriftLevel.QUARANTINE: PromptSeverity.LOCKOUT,
        }
        return mapping.get(level, PromptSeverity.GENTLE)

    def _render_template(
        self,
        severity: PromptSeverity,
        intent: str,
        action: str,
        drift: float,
        cost: float,
        agent_id: str,
        session_id: str,
    ) -> str:
        templates = {
            PromptSeverity.GENTLE: GENTLE_TEMPLATES,
            PromptSeverity.REDIRECT: REDIRECT_TEMPLATES,
            PromptSeverity.INSPECT: INSPECT_TEMPLATES,
            PromptSeverity.LOCKOUT: LOCKOUT_TEMPLATES,
        }
        pool = templates.get(severity, GENTLE_TEMPLATES)
        idx = self._template_index.get(severity, 0) % len(pool)
        self._template_index[severity] = idx + 1
        template = pool[idx]
        return template.format(
            intent=intent,
            action=action,
            drift=drift,
            cost=cost,
            agent_id=agent_id,
            session_id=session_id,
        )

    def _ttl_for_severity(self, severity: PromptSeverity) -> float:
        ttls = {
            PromptSeverity.GENTLE: 300.0,  # 5 min
            PromptSeverity.REDIRECT: 600.0,  # 10 min
            PromptSeverity.INSPECT: 1800.0,  # 30 min
            PromptSeverity.LOCKOUT: 86400.0,  # 24 hours
        }
        return ttls.get(severity, 300.0)
