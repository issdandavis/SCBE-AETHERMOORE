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
TransitionOperation = Literal["hold", "attenuate", "advance", "repair"]
LiteralIntent = Literal[
    "ask_explain",
    "ask_build",
    "ask_test",
    "ask_route",
    "ask_access",
    "unknown",
]
SemanticIntent = Literal[
    "benign_explanation",
    "benign_build_or_test",
    "game_binary_interpretation",
    "access_control_change",
    "unauthorized_access_attempt",
    "ambiguous",
]
PolarityMode = Literal["positive", "negative", "negabinary", "inverse_gravity", "neutral"]


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


@dataclass(frozen=True)
class BoundedTransitionPolicy:
    """Constrain discrete operation choices into smooth state movement."""

    max_step: float = 0.1
    min_goal_alignment: float = 0.0
    allow_repair_without_alignment: bool = True


@dataclass(frozen=True)
class BoundedTransitionRecord:
    """Audit record for a discrete operation that produced continuous movement."""

    operation: TransitionOperation
    previous_state: float
    requested_target: float
    next_state: float
    delta: float
    goal_alignment: float
    decision: GateDecision
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "previous_state": self.previous_state,
            "requested_target": self.requested_target,
            "next_state": self.next_state,
            "delta": self.delta,
            "goal_alignment": self.goal_alignment,
            "decision": self.decision,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class IntentParameterMatrixRecord:
    """Literal-vs-semantic intent record for routing and red-team scoring.

    The matrix distinguishes what the user literally asked from the safer
    interpretation of what the request would do in context. Creative language
    can stay available for games/training, but access-bypass language cannot
    be normalized into a positive access decision.
    """

    literal_intent: LiteralIntent
    semantic_intent: SemanticIntent
    polarity_mode: PolarityMode
    decision: GateDecision
    risk: RiskLevel
    confidence: float
    matched_terms: tuple[str, ...]
    parameters: dict[str, float | str | bool]
    reason: str
    record_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "literal_intent": self.literal_intent,
            "semantic_intent": self.semantic_intent,
            "polarity_mode": self.polarity_mode,
            "decision": self.decision,
            "risk": self.risk,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "parameters": self.parameters,
            "reason": self.reason,
            "record_hash": self.record_hash,
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


def parameterize_literal_semantic_intent(
    text: str,
    *,
    declared_intent: str = "",
    context: ExecutionContext = "routing",
) -> IntentParameterMatrixRecord:
    """Build a deterministic intent distinction matrix.

    This is a lightweight, auditable router signal. It is intentionally not an
    authentication authority. It borrows stable patterns from common NLU,
    policy, and access-control systems: literal action verbs, semantic effect,
    authority/access terms, context, confidence, and fail-closed risk handling.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    if not isinstance(declared_intent, str):
        raise ValueError("declared_intent must be a string")

    normalized = f"{text} {declared_intent}".lower()
    literal_intent, literal_hits = _classify_literal_intent(normalized)
    semantic_intent, semantic_hits = _classify_semantic_intent(normalized)
    polarity_mode, polarity_hits = _classify_polarity_mode(normalized)
    matched_terms = _ordered_unique_strings(
        [*literal_hits, *semantic_hits, *polarity_hits]
    )

    parameters = _intent_parameters(
        literal_intent=literal_intent,
        semantic_intent=semantic_intent,
        polarity_mode=polarity_mode,
        context=context,
    )
    decision, risk, reason = _intent_decision(
        semantic_intent=semantic_intent,
        polarity_mode=polarity_mode,
        context=context,
    )
    confidence = _intent_confidence(literal_hits, semantic_hits, polarity_hits)
    payload = {
        "literal_intent": literal_intent,
        "semantic_intent": semantic_intent,
        "polarity_mode": polarity_mode,
        "decision": decision,
        "risk": risk,
        "confidence": confidence,
        "matched_terms": matched_terms,
        "parameters": parameters,
        "reason": reason,
        "context": context,
    }
    return IntentParameterMatrixRecord(
        literal_intent=literal_intent,
        semantic_intent=semantic_intent,
        polarity_mode=polarity_mode,
        decision=decision,
        risk=risk,
        confidence=confidence,
        matched_terms=matched_terms,
        parameters=parameters,
        reason=reason,
        record_hash=_record_hash(payload),
    )


def apply_bounded_transition(
    *,
    previous_state: float,
    requested_target: float,
    operation: TransitionOperation,
    goal_alignment: float,
    policy: BoundedTransitionPolicy | None = None,
) -> BoundedTransitionRecord:
    """Apply a discrete operation as a bounded continuous state transition.

    Operational commands are discrete, but state movement is capped and filtered
    by goal alignment. This prevents analogy or operator clicks from causing
    hard jumps in action-critical coding state.
    """

    policy = policy or BoundedTransitionPolicy()
    _validate_transition_inputs(previous_state, requested_target, goal_alignment, policy)

    if operation == "hold":
        return BoundedTransitionRecord(
            operation=operation,
            previous_state=previous_state,
            requested_target=requested_target,
            next_state=previous_state,
            delta=0.0,
            goal_alignment=goal_alignment,
            decision="QUARANTINE",
            reason="hold operation preserves current state",
        )

    if goal_alignment < policy.min_goal_alignment and not (
        operation == "repair" and policy.allow_repair_without_alignment
    ):
        return BoundedTransitionRecord(
            operation=operation,
            previous_state=previous_state,
            requested_target=requested_target,
            next_state=previous_state,
            delta=0.0,
            goal_alignment=goal_alignment,
            decision="DENY",
            reason="goal alignment below transition threshold",
        )

    direction = _operation_direction(operation, previous_state, requested_target)
    raw_delta = requested_target - previous_state
    if operation == "attenuate":
        raw_delta = -abs(raw_delta) if raw_delta else -policy.max_step
    elif operation == "advance":
        raw_delta = abs(raw_delta) if raw_delta else policy.max_step

    capped_delta = max(-policy.max_step, min(policy.max_step, raw_delta))
    if direction < 0:
        capped_delta = -abs(capped_delta)
    elif direction > 0:
        capped_delta = abs(capped_delta)
    next_state = previous_state + capped_delta
    decision: GateDecision = "ALLOW" if operation in {"advance", "repair"} else "QUARANTINE"
    return BoundedTransitionRecord(
        operation=operation,
        previous_state=previous_state,
        requested_target=requested_target,
        next_state=next_state,
        delta=capped_delta,
        goal_alignment=goal_alignment,
        decision=decision,
        reason="bounded continuous transition applied",
    )


def _classify_literal_intent(text: str) -> tuple[LiteralIntent, list[str]]:
    patterns: list[tuple[LiteralIntent, tuple[str, ...]]] = [
        ("ask_test", ("test", "benchmark", "score", "verify", "red team")),
        ("ask_build", ("build", "make", "code", "implement", "add")),
        ("ask_explain", ("explain", "what is", "how does", "meaning")),
        ("ask_route", ("route", "bus", "dispatch", "send", "message")),
        ("ask_access", ("access", "auth", "credential", "permission", "login")),
    ]
    return _first_pattern(text, patterns, default="unknown")


def _classify_semantic_intent(text: str) -> tuple[SemanticIntent, list[str]]:
    unauthorized_terms = (
        "backdoor",
        "bypass",
        "stealth access",
        "discreet access",
        "secret access",
        "unauthorized",
        "privilege escalation",
        "hidden access",
    )
    access_terms = (
        "access control",
        "permission",
        "credential",
        "auth",
        "authorization",
        "login",
    )
    game_binary_terms = (
        "gaming",
        "game",
        "binary",
        "hex",
        "negabinary",
        "negative binary",
        "inverse gravity",
        "polarity",
    )
    build_terms = ("build", "code", "implement", "test", "matrix", "parameter")
    explain_terms = ("explain", "what is", "meaning", "distinction")
    patterns: list[tuple[SemanticIntent, tuple[str, ...]]] = [
        ("unauthorized_access_attempt", unauthorized_terms),
        ("access_control_change", access_terms),
        ("game_binary_interpretation", game_binary_terms),
        ("benign_build_or_test", build_terms),
        ("benign_explanation", explain_terms),
    ]
    return _first_pattern(text, patterns, default="ambiguous")


def _classify_polarity_mode(text: str) -> tuple[PolarityMode, list[str]]:
    patterns: list[tuple[PolarityMode, tuple[str, ...]]] = [
        ("negabinary", ("negabinary", "negative binary")),
        ("inverse_gravity", ("inverse gravity", "repulsion field", "gravity field")),
        ("negative", ("negative", "inverse", "downside")),
        ("positive", ("positive", "allow", "upside")),
    ]
    return _first_pattern(text, patterns, default="neutral")


def _first_pattern(
    text: str,
    patterns: Sequence[tuple[str, tuple[str, ...]]],
    *,
    default: str,
) -> tuple[str, list[str]]:
    for label, terms in patterns:
        hits = [term for term in terms if term in text]
        if hits:
            return label, hits
    return default, []


def _intent_parameters(
    *,
    literal_intent: LiteralIntent,
    semantic_intent: SemanticIntent,
    polarity_mode: PolarityMode,
    context: ExecutionContext,
) -> dict[str, float | str | bool]:
    access_pressure = 1.0 if semantic_intent in {"access_control_change", "unauthorized_access_attempt"} else 0.0
    bypass_pressure = 1.0 if semantic_intent == "unauthorized_access_attempt" else 0.0
    game_pressure = 1.0 if semantic_intent == "game_binary_interpretation" else 0.0
    polarity_pressure = {
        "neutral": 0.0,
        "positive": 0.25,
        "negative": -0.25,
        "negabinary": -0.5,
        "inverse_gravity": -0.75,
    }[polarity_mode]
    action_pressure = 1.0 if context == "action" else 0.0
    return {
        "literal_intent": literal_intent,
        "semantic_intent": semantic_intent,
        "context": context,
        "access_pressure": access_pressure,
        "bypass_pressure": bypass_pressure,
        "game_pressure": game_pressure,
        "polarity_pressure": polarity_pressure,
        "action_pressure": action_pressure,
        "can_lower_access_risk": False,
    }


def _intent_decision(
    *,
    semantic_intent: SemanticIntent,
    polarity_mode: PolarityMode,
    context: ExecutionContext,
) -> tuple[GateDecision, RiskLevel, str]:
    if semantic_intent == "unauthorized_access_attempt":
        return (
            "DENY",
            "critical",
            "access-bypass language cannot be normalized into positive access",
        )
    if semantic_intent == "access_control_change" and context == "action":
        return "ESCALATE", "high", "access-control change requires authority review"
    if semantic_intent == "access_control_change":
        return "QUARANTINE", "medium", "access-control language requires provenance"
    if polarity_mode in {"negabinary", "inverse_gravity"} and context == "action":
        return "QUARANTINE", "medium", "polarity transform is sandbox-only for action context"
    if semantic_intent == "game_binary_interpretation":
        return "ALLOW", "low", "game/binary interpretation allowed as non-authority signal"
    if semantic_intent == "ambiguous":
        return "QUARANTINE", "medium", "intent ambiguous pending clarification"
    return "ALLOW", "low", "benign intent parameters"


def _intent_confidence(
    literal_hits: Sequence[str],
    semantic_hits: Sequence[str],
    polarity_hits: Sequence[str],
) -> float:
    score = 0.35
    if literal_hits:
        score += 0.25
    if semantic_hits:
        score += 0.30
    if polarity_hits:
        score += 0.10
    return round(min(1.0, score), 4)


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


def _operation_direction(
    operation: TransitionOperation, previous_state: float, requested_target: float
) -> int:
    if operation == "attenuate":
        return -1
    if operation == "advance":
        return 1
    if requested_target > previous_state:
        return 1
    if requested_target < previous_state:
        return -1
    return 0


def _validate_transition_inputs(
    previous_state: float,
    requested_target: float,
    goal_alignment: float,
    policy: BoundedTransitionPolicy,
) -> None:
    for label, value in {
        "previous_state": previous_state,
        "requested_target": requested_target,
        "goal_alignment": goal_alignment,
        "max_step": policy.max_step,
        "min_goal_alignment": policy.min_goal_alignment,
    }.items():
        if not isinstance(value, Real) or isinstance(value, bool):
            raise ValueError(f"{label} must be numeric")
    if policy.max_step < 0:
        raise ValueError("max_step must be non-negative")
    if not -1.0 <= goal_alignment <= 1.0:
        raise ValueError("goal_alignment out of range")
    if not -1.0 <= policy.min_goal_alignment <= 1.0:
        raise ValueError("min_goal_alignment out of range")


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


def _ordered_unique_strings(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
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
