"""Stateful trajectory risk gate for AI operation requests.

This module complements one-shot prompt-injection recall with a small,
deterministic state machine that evaluates where a conversation is moving over
time. A benign user redirect should not be treated like an attacker telling the
system to ignore safety controls, but repeated movement toward secrets, tools,
or core instructions should accumulate risk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional, Sequence


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class AccessLevel(str, Enum):
    """Normalized access pressure requested or implied by a turn."""

    PUBLIC = "PUBLIC"
    USER_CONTEXT = "USER_CONTEXT"
    FILES = "FILES"
    TOOLS = "TOOLS"
    SECRETS = "SECRETS"
    SYSTEM = "SYSTEM"


class IntentClass(str, Enum):
    """High-level intent class inferred from a request."""

    BENIGN_USER_REDIRECT = "BENIGN_USER_REDIRECT"
    BENIGN_TASK_WORK = "BENIGN_TASK_WORK"
    AUTHORITY_OVERRIDE = "AUTHORITY_OVERRIDE"
    TOOL_OR_SECRET_ESCALATION = "TOOL_OR_SECRET_ESCALATION"
    PROTECTED_CORE_PROBING = "PROTECTED_CORE_PROBING"
    UNKNOWN = "UNKNOWN"


class TrajectoryDecision(str, Enum):
    """Decision exposed to callers."""

    ALLOW = "ALLOW"
    ALLOW_WITH_LIMITS = "ALLOW_WITH_LIMITS"
    ASK_CLARIFYING_SCOPE = "ASK_CLARIFYING_SCOPE"
    SANDBOX = "SANDBOX"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class RiskSignal:
    """One explainable contribution to a risk decision."""

    name: str
    score: float
    evidence: str


@dataclass(frozen=True)
class TrajectoryRiskDecision:
    """Structured output for audit logs and user-facing gates."""

    decision: TrajectoryDecision
    risk_score: float
    intent_class: IntentClass
    access_level: AccessLevel
    static_risk: float
    trajectory_risk: float
    access_pressure: float
    legitimate_need: float
    continuity_score: float
    signals: Sequence[RiskSignal] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return self.decision in {
            TrajectoryDecision.ALLOW,
            TrajectoryDecision.ALLOW_WITH_LIMITS,
            TrajectoryDecision.ASK_CLARIFYING_SCOPE,
            TrajectoryDecision.SANDBOX,
        }


_BENIGN_REDIRECT = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(ignore|forget|skip|drop)\s+(my\s+)?(previous|prior|last)\s+(question|request|task|message)\b",
        r"\bnew\s+(topic|task|question)\b",
        r"\bstart\s+over\b",
        r"\breset\s+(the\s+)?(conversation|task|thread)\b",
        r"\bchange\s+topics?\b",
    ]
]

_AUTHORITY_OVERRIDE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(ignore|disregard|bypass|override|supersede)\b.*\b(system|developer|safety|security|policy|policies|rules|instructions)\b",
        r"\bdisable\b.*\b(safety|security|policy|filter|guardrail|governance)\b",
        r"\bno\s+(rules|restrictions|policy|policies|ethics)\b",
        r"\bunrestricted\s+(mode|assistant|access|output)\b",
        r"\bdeveloper\s+mode\b",
        r"\bjailbreak\b",
    ]
]

_SECRET_OR_TOOL = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(api[_ -]?keys?|tokens?|secrets?|passwords?|credentials?|private\s+keys?|ssh\s+keys?)\b",
        r"\b(env|environment)\s+(vars?|variables?)\b",
        r"\b\.env\b",
        r"\bread\b.*\b(file|filesystem|disk|repo|home\s+directory)\b",
        r"\bwrite\b.*\b(file|filesystem|repo)\b",
        r"\b(run|execute|shell|powershell|bash|cmd)\b",
        r"\bexfiltrat",
        r"\bdump\b.*\b(data|secrets?|credentials?|files?)\b",
    ]
]

_PROTECTED_CORE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(system\s+prompt|developer\s+message|hidden\s+instructions?|internal\s+instructions?)\b",
        r"\bchain\s+of\s+thought|private\s+reasoning|inner\s+thoughts?\b",
        r"\bgovernance\s+(layer|rules|config|bypass|override)\b",
        r"\bsafety\s+(standard|policy|rules|protocol|instructions?)\b",
        r"\bmodel\s+(weights?|system\s+card|alignment|policy)\b",
    ]
]

_LEGITIMATE_NEED = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(test|tests|pytest|unit\s+test|regression|benchmark|evaluate|audit|review)\b",
        r"\bfix\b.*\b(bug|error|failure|test|ci)\b",
        r"\bimplement|build|refactor|document|summari[sz]e\b",
        r"\bwith\s+(mock|dummy|redacted|sample|synthetic)\b",
        r"\bno\s+secrets?\b|\bredacted\b|\bsafe\b",
    ]
]


_ACCESS_SCORES = {
    AccessLevel.PUBLIC: 0.0,
    AccessLevel.USER_CONTEXT: 0.15,
    AccessLevel.FILES: 0.35,
    AccessLevel.TOOLS: 0.45,
    AccessLevel.SECRETS: 0.85,
    AccessLevel.SYSTEM: 0.9,
}


class TrajectoryRiskGate:
    """Evaluate AI operation risk across time, intent, access, and need."""

    def __init__(
        self, session_goal: str = "", user_authority: str = "standard"
    ) -> None:
        self.session_goal = session_goal
        self.user_authority = user_authority
        self._history: List[TrajectoryRiskDecision] = []

    @property
    def history(self) -> Sequence[TrajectoryRiskDecision]:
        return tuple(self._history)

    def reset(self) -> None:
        self._history.clear()

    def evaluate(
        self,
        message: str,
        *,
        requested_access: AccessLevel | str | None = None,
        declared_need: str = "",
        static_risk: Optional[float] = None,
    ) -> TrajectoryRiskDecision:
        text = message or ""
        access = self._normalize_access(requested_access, text)
        intent = self._classify_intent(text)
        signals: List[RiskSignal] = []

        static_score = _clamp(
            static_risk if static_risk is not None else self._static_risk(text, intent)
        )
        if static_score:
            signals.append(
                RiskSignal("static_lookup", static_score, "one-shot lexical/core risk")
            )

        access_pressure = _ACCESS_SCORES[access]
        if access_pressure >= 0.35:
            signals.append(RiskSignal("access_pressure", access_pressure, access.value))

        need_score = self._legitimate_need(text, declared_need)
        if need_score:
            signals.append(
                RiskSignal(
                    "legitimate_need",
                    -need_score,
                    "task need reduces but cannot erase risk",
                )
            )

        continuity = self._continuity_score(text)
        if continuity:
            signals.append(
                RiskSignal(
                    "task_continuity", -continuity, "request aligns with session work"
                )
            )

        trajectory = self._trajectory_pressure(intent, access)
        if trajectory:
            signals.append(
                RiskSignal(
                    "trajectory_pressure",
                    trajectory,
                    "risk accumulated across recent turns",
                )
            )

        authority = self._authority_credit()
        if authority:
            signals.append(
                RiskSignal("user_authority", -authority, self.user_authority)
            )

        risk = _clamp(
            static_score
            + access_pressure
            + trajectory
            - 0.35 * need_score
            - 0.25 * continuity
            - authority
        )

        # Hard floor rules: high need may send risky operations to sandbox, but
        # it should not allow core prompt, policy, or secret extraction.
        if intent in {
            IntentClass.AUTHORITY_OVERRIDE,
            IntentClass.PROTECTED_CORE_PROBING,
        } and access in {
            AccessLevel.SECRETS,
            AccessLevel.SYSTEM,
        }:
            risk = max(risk, 0.92)
        if (
            intent == IntentClass.TOOL_OR_SECRET_ESCALATION
            and access == AccessLevel.SECRETS
        ):
            risk = max(risk, 0.9)

        decision = self._decision_for(risk, intent, access, need_score)
        result = TrajectoryRiskDecision(
            decision=decision,
            risk_score=round(risk, 4),
            intent_class=intent,
            access_level=access,
            static_risk=round(static_score, 4),
            trajectory_risk=round(trajectory, 4),
            access_pressure=round(access_pressure, 4),
            legitimate_need=round(need_score, 4),
            continuity_score=round(continuity, 4),
            signals=tuple(signals),
        )
        self._history.append(result)
        return result

    def _normalize_access(
        self, requested_access: AccessLevel | str | None, text: str
    ) -> AccessLevel:
        if isinstance(requested_access, AccessLevel):
            return requested_access
        if requested_access:
            value = str(requested_access).strip().upper()
            if value in AccessLevel.__members__:
                return AccessLevel[value]
            for level in AccessLevel:
                if value == level.value:
                    return level

        lower = text.lower()
        if any(p.search(text) for p in _PROTECTED_CORE):
            return AccessLevel.SYSTEM
        if re.search(
            r"(\.env\b|\b(api[_ -]?keys?|tokens?|secrets?|passwords?|credentials?|private\s+keys?)\b)",
            lower,
        ):
            return AccessLevel.SECRETS
        if re.search(
            r"\b(shell|powershell|bash|cmd|execute|run command|tool)\b", lower
        ):
            return AccessLevel.TOOLS
        if re.search(r"\b(file|filesystem|repo|directory|path)\b", lower):
            return AccessLevel.FILES
        if re.search(
            r"\b(my|our|this)\s+(conversation|project|repo|account|data)\b", lower
        ):
            return AccessLevel.USER_CONTEXT
        return AccessLevel.PUBLIC

    def _classify_intent(self, text: str) -> IntentClass:
        if any(p.search(text) for p in _AUTHORITY_OVERRIDE):
            return IntentClass.AUTHORITY_OVERRIDE
        if any(p.search(text) for p in _PROTECTED_CORE):
            return IntentClass.PROTECTED_CORE_PROBING
        if any(p.search(text) for p in _SECRET_OR_TOOL):
            return IntentClass.TOOL_OR_SECRET_ESCALATION
        if any(p.search(text) for p in _BENIGN_REDIRECT):
            return IntentClass.BENIGN_USER_REDIRECT
        if any(p.search(text) for p in _LEGITIMATE_NEED):
            return IntentClass.BENIGN_TASK_WORK
        return IntentClass.UNKNOWN

    def _static_risk(self, text: str, intent: IntentClass) -> float:
        if intent == IntentClass.AUTHORITY_OVERRIDE:
            return 0.7
        if intent == IntentClass.PROTECTED_CORE_PROBING:
            return 0.65
        if intent == IntentClass.TOOL_OR_SECRET_ESCALATION:
            return 0.45
        if intent == IntentClass.BENIGN_USER_REDIRECT:
            return 0.05
        return 0.0

    def _legitimate_need(self, text: str, declared_need: str) -> float:
        joined = f"{text}\n{declared_need}"
        hits = sum(1 for pattern in _LEGITIMATE_NEED if pattern.search(joined))
        if not hits:
            return 0.0
        return _clamp(0.25 + min(hits, 4) * 0.12)

    def _continuity_score(self, text: str) -> float:
        if not self.session_goal:
            return 0.0
        goal_words = _important_words(self.session_goal)
        text_words = _important_words(text)
        if not goal_words or not text_words:
            return 0.0
        overlap = len(goal_words.intersection(text_words)) / max(1, len(goal_words))
        return _clamp(overlap)

    def _trajectory_pressure(self, intent: IntentClass, access: AccessLevel) -> float:
        if not self._history:
            return 0.0
        recent = self._history[-5:]
        pressure = 0.0
        for item in recent:
            if item.intent_class in {
                IntentClass.AUTHORITY_OVERRIDE,
                IntentClass.TOOL_OR_SECRET_ESCALATION,
                IntentClass.PROTECTED_CORE_PROBING,
            }:
                pressure += 0.12
            if item.access_pressure >= 0.35:
                pressure += 0.08
            if item.decision in {
                TrajectoryDecision.HOLD_FOR_REVIEW,
                TrajectoryDecision.BLOCK,
            }:
                pressure += 0.1

        if intent in {
            IntentClass.AUTHORITY_OVERRIDE,
            IntentClass.TOOL_OR_SECRET_ESCALATION,
            IntentClass.PROTECTED_CORE_PROBING,
        }:
            pressure += 0.1
        if access in {AccessLevel.TOOLS, AccessLevel.SECRETS, AccessLevel.SYSTEM}:
            pressure += 0.08
        return _clamp(pressure)

    def _authority_credit(self) -> float:
        authority = self.user_authority.lower().strip()
        if authority in {"owner", "admin", "developer"}:
            return 0.08
        if authority in {"trusted", "operator"}:
            return 0.04
        return 0.0

    def _decision_for(
        self,
        risk: float,
        intent: IntentClass,
        access: AccessLevel,
        need_score: float,
    ) -> TrajectoryDecision:
        if risk >= 0.9:
            return TrajectoryDecision.BLOCK
        if risk >= 0.72:
            return TrajectoryDecision.HOLD_FOR_REVIEW
        if risk >= 0.55:
            if need_score >= 0.45 and access not in {
                AccessLevel.SECRETS,
                AccessLevel.SYSTEM,
            }:
                return TrajectoryDecision.SANDBOX
            return TrajectoryDecision.HOLD_FOR_REVIEW
        if risk >= 0.35:
            if need_score >= 0.45 and access in {AccessLevel.FILES, AccessLevel.TOOLS}:
                return TrajectoryDecision.SANDBOX
            if intent in {
                IntentClass.TOOL_OR_SECRET_ESCALATION,
                IntentClass.PROTECTED_CORE_PROBING,
            }:
                return TrajectoryDecision.ASK_CLARIFYING_SCOPE
            return TrajectoryDecision.ALLOW_WITH_LIMITS
        return TrajectoryDecision.ALLOW


def _important_words(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "our",
        "you",
        "your",
        "are",
        "can",
        "need",
        "using",
    }
    words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower()))
    return {word for word in words if word not in stop}


def evaluate_sequence(
    messages: Iterable[str],
    *,
    session_goal: str = "",
    user_authority: str = "standard",
) -> List[TrajectoryRiskDecision]:
    """Convenience helper for tests and benchmark scripts."""

    gate = TrajectoryRiskGate(session_goal=session_goal, user_authority=user_authority)
    return [gate.evaluate(message) for message in messages]
