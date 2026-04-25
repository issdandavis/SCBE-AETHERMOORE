"""Provenance-aware semantic separation and controlled blending.

This module keeps facts, semantics, analogy, inference, and experimental
signals separate until a policy explicitly allows them to braid. It is an
AI-operations guardrail, not an authentication or cryptographic authority layer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Real
from typing import Iterable, Literal, Sequence

SignalSource = Literal["fact", "semantic", "analogy", "inference", "experimental"]
ExecutionContext = Literal["sandbox", "routing", "training", "action"]
RiskLevel = Literal["low", "medium", "high", "critical"]
GateDecision = Literal["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]


@dataclass(frozen=True)
class SemanticSignal:
    """A single value with explicit representation provenance."""

    label: str
    value: object
    source: SignalSource
    confidence: float
    provenance: str = ""


@dataclass(frozen=True)
class SemanticBlendPolicy:
    """Controls which representation layers can affect the current operation."""

    context: ExecutionContext
    risk: RiskLevel
    allow_analogy: bool = False
    allow_experimental: bool = False
    allow_inference: bool = True
    require_fact: bool = True
    min_confidence: float = 0.5


@dataclass(frozen=True)
class SemanticGateRecord:
    """Deterministic audit record for a semantic blending decision."""

    decision: GateDecision
    reason: str
    blended_value: float | None
    allowed_sources: tuple[SignalSource, ...]
    blocked_sources: tuple[SignalSource, ...]
    allowed_labels: tuple[str, ...]
    blocked_labels: tuple[str, ...]
    signal_count: int
    policy: SemanticBlendPolicy
    record_hash: str
    generated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "blended_value": self.blended_value,
            "allowed_sources": list(self.allowed_sources),
            "blocked_sources": list(self.blocked_sources),
            "allowed_labels": list(self.allowed_labels),
            "blocked_labels": list(self.blocked_labels),
            "signal_count": self.signal_count,
            "policy": {
                "context": self.policy.context,
                "risk": self.policy.risk,
                "allow_analogy": self.policy.allow_analogy,
                "allow_experimental": self.policy.allow_experimental,
                "allow_inference": self.policy.allow_inference,
                "require_fact": self.policy.require_fact,
                "min_confidence": self.policy.min_confidence,
            },
            "record_hash": self.record_hash,
            "generated_at": self.generated_at,
        }


def evaluate_semantic_gate(
    signals: Sequence[SemanticSignal], policy: SemanticBlendPolicy
) -> SemanticGateRecord:
    """Evaluate provenance separation and return a deterministic decision record."""

    _validate_policy(policy)
    for signal in signals:
        _validate_signal(signal)

    allowed: list[SemanticSignal] = []
    blocked: list[SemanticSignal] = []
    for signal in signals:
        if _signal_allowed(signal, policy):
            allowed.append(signal)
        else:
            blocked.append(signal)

    allowed_sources = _ordered_unique(signal.source for signal in allowed)
    blocked_sources = _ordered_unique(signal.source for signal in blocked)
    allowed_labels = tuple(signal.label for signal in allowed)
    blocked_labels = tuple(signal.label for signal in blocked)
    has_required_fact = any(signal.source == "fact" for signal in allowed)
    high_risk_action = policy.context == "action" and policy.risk in {
        "high",
        "critical",
    }

    if not signals:
        decision: GateDecision = "DENY" if policy.require_fact else "QUARANTINE"
        reason = "no signals supplied"
    elif policy.require_fact and not has_required_fact:
        decision = "DENY"
        reason = "required fact channel missing"
    elif not allowed:
        decision = "DENY"
        reason = "all signals blocked by policy"
    elif high_risk_action and blocked:
        decision = "ESCALATE"
        reason = "high-risk action excluded non-actionable representation layers"
    elif blocked and any(signal.source == "experimental" for signal in blocked):
        decision = "QUARANTINE"
        reason = "experimental signal blocked pending explicit policy"
    else:
        decision = "ALLOW"
        reason = "allowed sources satisfy policy"

    blended_value = _confidence_weighted_numeric_blend(allowed)
    record_hash = _record_hash(
        {
            "decision": decision,
            "reason": reason,
            "blended_value": blended_value,
            "allowed_sources": allowed_sources,
            "blocked_sources": blocked_sources,
            "allowed_labels": allowed_labels,
            "blocked_labels": blocked_labels,
            "signals": [_signal_digest(signal) for signal in signals],
            "policy": {
                "context": policy.context,
                "risk": policy.risk,
                "allow_analogy": policy.allow_analogy,
                "allow_experimental": policy.allow_experimental,
                "allow_inference": policy.allow_inference,
                "require_fact": policy.require_fact,
                "min_confidence": policy.min_confidence,
            },
        }
    )
    return SemanticGateRecord(
        decision=decision,
        reason=reason,
        blended_value=blended_value,
        allowed_sources=allowed_sources,
        blocked_sources=blocked_sources,
        allowed_labels=allowed_labels,
        blocked_labels=blocked_labels,
        signal_count=len(signals),
        policy=policy,
        record_hash=record_hash,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _signal_allowed(signal: SemanticSignal, policy: SemanticBlendPolicy) -> bool:
    if signal.confidence < policy.min_confidence:
        return False
    if signal.source == "analogy" and not policy.allow_analogy:
        return False
    if signal.source == "experimental" and not policy.allow_experimental:
        return False
    if signal.source == "inference" and not policy.allow_inference:
        return False
    if (
        policy.context == "action"
        and policy.risk in {"high", "critical"}
        and signal.source != "fact"
    ):
        return False
    return True


def _confidence_weighted_numeric_blend(
    signals: Sequence[SemanticSignal],
) -> float | None:
    numeric = [
        signal
        for signal in signals
        if isinstance(signal.value, Real) and not isinstance(signal.value, bool)
    ]
    if not numeric:
        return None
    total_weight = sum(signal.confidence for signal in numeric)
    if total_weight == 0:
        return None
    return (
        sum(float(signal.value) * signal.confidence for signal in numeric)
        / total_weight
    )


def _validate_signal(signal: SemanticSignal) -> None:
    if not signal.label:
        raise ValueError("signal label is required")
    if not 0.0 <= signal.confidence <= 1.0:
        raise ValueError(
            f"signal confidence out of range for {signal.label}: {signal.confidence}"
        )


def _validate_policy(policy: SemanticBlendPolicy) -> None:
    if not 0.0 <= policy.min_confidence <= 1.0:
        raise ValueError(f"policy min_confidence out of range: {policy.min_confidence}")


def _ordered_unique(values: Iterable[SignalSource]) -> tuple[SignalSource, ...]:
    seen: set[SignalSource] = set()
    result: list[SignalSource] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _record_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _signal_digest(signal: SemanticSignal) -> dict[str, object]:
    return {
        "label": signal.label,
        "source": signal.source,
        "confidence": signal.confidence,
        "value_repr": repr(signal.value),
        "provenance": signal.provenance,
    }
