"""AetherBrowse action validator.
Wires browser action intent to PHDM + bounds checks before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from agents.browser.bounds_checker import ActionContext, BoundsChecker
from agents.browser.phdm_brain import SafetyDecision, SimplePHDM, create_phdm_brain
from agents.browser.vision_embedding import VisionEmbedder


class ValidationDecision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass
class ActionValidationResult:
    action: str
    target: str
    decision: ValidationDecision
    phdm_decision: SafetyDecision
    sensitivity: float
    phdm_radius: float
    phdm_hyperbolic_distance: float
    phdm_risk: float
    bounds_decision: str
    bounds_violations: List[str]
    explanation: str
    embedding: list[float]

    @property
    def can_execute(self) -> bool:
        return self.decision in (ValidationDecision.ALLOW, ValidationDecision.QUARANTINE)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "decision": self.decision.value,
            "phdm_decision": self.phdm_decision.value,
            "sensitivity": self.sensitivity,
            "phdm_radius": self.phdm_radius,
            "phdm_hyperbolic_distance": self.phdm_hyperbolic_distance,
            "phdm_risk": self.phdm_risk,
            "bounds_decision": self.bounds_decision,
            "bounds_violations": self.bounds_violations,
            "explanation": self.explanation,
            "embedding": self.embedding,
        }


@dataclass
class ValidationPolicy:
    safe_radius: float = 0.92
    phdm_dim: int = 16
    sensitivity_factor: float = 1.0
    escalate_on_quarantine: bool = False
    deny_threshold: float = 0.9


class ActionValidator:
    """Combines action embedding -> PHDM containment -> optional bounds check."""

    ACTION_BASE_RISK = {
        "navigate": 0.30,
        "click": 0.40,
        "type": 0.50,
        "extract": 0.20,
        "scroll": 0.10,
        "screenshot": 0.15,
        "snapshot": 0.20,
    }

    DOMAIN_RISK = {
        "banking": 0.95,
        "finance": 0.9,
        "pay": 0.85,
        "crypto": 0.9,
        "admin": 0.8,
        "login": 0.7,
        "gov": 0.8,
        "health": 0.75,
        "default": 0.45,
    }

    def __init__(self, policy: Optional[ValidationPolicy] = None):
        self.policy = policy or ValidationPolicy()
        self.phdm: SimplePHDM = create_phdm_brain(
            safe_radius=self.policy.safe_radius,
            dim=self.policy.phdm_dim,
        )
        self.bounds_checker = BoundsChecker()
        self.embedder: Optional[VisionEmbedder] = None

    def _sensitivity(self, action: str, target: str, context: Optional[Dict[str, Any]] = None) -> float:
        target_lower = (target or "").lower()
        base = self.ACTION_BASE_RISK.get(action.lower(), 0.5)

        domain = self.DOMAIN_RISK["default"]
        for token, risk in self.DOMAIN_RISK.items():
            if token == "default":
                continue
            if token in target_lower:
                domain = max(domain, risk)

        context_bias = 0.0
        if context:
            context_bias += float(context.get("sensitivity_override", 0.0))
            if context.get("touches_secrets"):
                context_bias += 0.2

        score = min(1.0, 0.6 * base + 0.4 * domain + context_bias)
        return min(1.0, score * self.policy.sensitivity_factor)

    @staticmethod
    def _contains_sensitive_pattern(target: str) -> bool:
        marker = (target or "").lower()
        return any(token in marker for token in ("password", "token", "secret", "api_key", "private_key"))

    async def _embed(self, action: str, target: str, context_embedding: Optional[np.ndarray] = None) -> tuple[np.ndarray, np.ndarray]:
        if self.embedder is None:
            self.embedder = VisionEmbedder(target_dim=self.policy.phdm_dim)
            # initialize is cheap if fallback mode is active
            await self.embedder.initialize()

        result = await self.embedder.embed_action(
            action_type=action,
            target=target,
            context_embedding=context_embedding,
        )
        return result.poincare_embedding, result.euclidean_embedding

    async def validate(
        self,
        action: str,
        target: str,
        *,
        context_embedding: Optional[np.ndarray] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionValidationResult:
        action = action.strip().lower()
        target = target.strip()
        if not action:
            raise ValueError("Action name required.")

        sensitivity = self._sensitivity(action, target, context)
        embedding, euclid_embedding = await self._embed(action, target, context_embedding)

        # Layer 13/9 governance
        containment = self.phdm.check_containment(embedding)

        # Layer 5/8/10 geometric + operational bounds check
        bounds_ctx = ActionContext(
            risk_score=sensitivity,
            scope_delta=float(context.get("scope_delta", 0.0)) if context else 0.0,
            provenance_score=float(context.get("provenance_score", 0.75)) if context else 0.75,
            touches_secrets=(
                bool(context.get("touches_secrets", False)) if context else False
            )
            or self._contains_sensitive_pattern(target),
            tool_class=action,
            coherence=float(context.get("coherence", 0.82)) if context else 0.82,
            votes=context.get("votes") if context else None,
            agent_states=np.array(context.get("agent_states"))
            if context and context.get("agent_states") is not None else None,
        )

        bounds = self.bounds_checker.check_all_bounds(bounds_ctx)
        bounds_violation_count = len(bounds.violations)
        bounds_decision = bounds.decision.value

        # Merge governance layers:
        decision = containment.decision.value
        if decision == SafetyDecision.DENY.value:
            decision = ValidationDecision.DENY.value
        elif bounds_decision == "DENY":
            decision = ValidationDecision.DENY.value
        elif bounds_decision == "QUARANTINE":
            if decision in (SafetyDecision.ALLOW.value, SafetyDecision.QUARANTINE.value):
                decision = ValidationDecision.QUARANTINE.value
            if self.policy.escalate_on_quarantine and sensitivity >= self.policy.deny_threshold:
                decision = ValidationDecision.ESCALATE.value
        elif decision == SafetyDecision.QUARANTINE.value:
            decision = ValidationDecision.QUARANTINE.value
        elif sensitivity >= self.policy.deny_threshold:
            # high sensitivity actions get human/next-hop attention
            decision = ValidationDecision.ESCALATE.value
        else:
            decision = ValidationDecision.ALLOW.value

        explanation = (
            f"{action} target='{target}' | "
            f"sensitivity={sensitivity:.3f} "
            f"phdm={containment.decision.value}/{containment.risk_score:.3f} "
            f"bounds={bounds_decision}/{bounds_violation_count}"
        )

        return ActionValidationResult(
            action=action,
            target=target,
            decision=ValidationDecision(decision),
            phdm_decision=containment.decision,
            sensitivity=sensitivity,
            phdm_radius=containment.radius,
            phdm_hyperbolic_distance=containment.hyperbolic_distance,
            phdm_risk=containment.risk_score,
            bounds_decision=bounds_decision,
            bounds_violations=bounds.violations,
            explanation=explanation,
            embedding=(euclid_embedding.astype(float).tolist() if isinstance(euclid_embedding, np.ndarray) else []),
        )

    async def validate_many(
        self,
        actions: list[tuple[str, str]],
        *,
        context_embedding: Optional[np.ndarray] = None,
    ) -> list[ActionValidationResult]:
        results = []
        last_embedding = context_embedding
        for action, target in actions:
            r = await self.validate(action, target, context_embedding=last_embedding)
            last_embedding = np.array(r.embedding)
            results.append(r)
        return results
