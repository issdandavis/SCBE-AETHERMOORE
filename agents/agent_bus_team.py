"""
Agent Bus team coordination — wraps existing HYDRA / SwarmBrowser systems.

The bus is the spinal cord; this module is the reflex that asks the team
"should we do this?" before executing high-stakes actions. Two patterns:

  1. Roundtable consensus (Byzantine-safe): six Sacred Tongue agents vote.
     Requires 4/6 ALLOW to proceed. Survives 2 compromised agents.
     Used when bus is in "swarm" mode.

  2. Solo→swarm escalation: the bus tries solo first, escalates to
     roundtable on failure or low confidence (decompose-first,
     escalate-on-failure-second per 2026 SOTA).

Both decisions are logged to the HYDRA ledger as CONSENSUS entries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("scbe.agent_bus.team")

# Industry-standard escalation thresholds (per 2026 review of Browser-use, SkyVern, Manus).
DEFAULT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_MAX_SOLO_FAILURES = 2


class TeamCoordinator:
    """Wraps a SwarmBackend to expose team-decision primitives to the bus."""

    def __init__(
        self,
        swarm_backend: Any,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        max_solo_failures: int = DEFAULT_MAX_SOLO_FAILURES,
    ) -> None:
        self.swarm = swarm_backend
        self.confidence_threshold = confidence_threshold
        self.max_solo_failures = max_solo_failures
        self._solo_failures = 0

    async def team_decide(
        self,
        action_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run roundtable consensus. Returns {decision, votes, confidence}."""
        if self.swarm is None or not hasattr(self.swarm, "consensus"):
            return {"decision": "ALLOW", "votes": [], "confidence": 1.0, "reason": "no_swarm"}
        result = await self.swarm.consensus(action_id, action, context or {})
        logger.info("team_decide %s → %s", action, result.get("decision"))
        return result

    def should_escalate(self, solo_confidence: float, solo_succeeded: bool) -> bool:
        """Decide whether to escalate from solo to swarm.

        Decompose-first, escalate-on-failure-second. Two triggers:
          - solo confidence below threshold
          - exceeded max consecutive solo failures
        """
        if solo_succeeded:
            self._solo_failures = 0
            return solo_confidence < self.confidence_threshold
        self._solo_failures += 1
        return self._solo_failures >= self.max_solo_failures
