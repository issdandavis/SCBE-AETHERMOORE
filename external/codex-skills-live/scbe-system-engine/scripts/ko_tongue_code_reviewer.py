#!/usr/bin/env python3
"""KO-tongue compliance reviewer for SCBE diffs."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import List
from enum import Enum


class Action(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


@dataclass
class StateVector:
    risk_score: float
    layer_hits: List[int]
    hard_constants: int
    dimensional_issues: int


@dataclass
class DecisionRecord:
    action: str
    signature: str
    timestamp: str
    reason: str
    tongue: str = "KO"


@dataclass
class AgentOutput:
    state_vector: StateVector
    decision_record: DecisionRecord


class KOTongueCodeReviewer:
    tongue = "KO"
    model = "claude-opus-4-6"

    _CONSTANT_RE = re.compile(r"(?<![A-Za-z0-9_])(0x[0-9A-Fa-f]+|\d{3,})(?![A-Za-z0-9_])")
    _DIM_FUNC_RE = re.compile(r"\b(log|ln|exp|sqrt|sin|cos)\s*\(")
    _DUAL_STATE_RE = re.compile(r"\bStateVector\b")
    _DUAL_DECISION_RE = re.compile(r"\bDecisionRecord\b")

    def review(self, diff_text: str) -> AgentOutput:
        issues: List[str] = []
        lines = diff_text.splitlines()

        has_state = bool(self._DUAL_STATE_RE.search(diff_text))
        has_decision = bool(self._DUAL_DECISION_RE.search(diff_text))
        if not (has_state and has_decision):
            issues.append("Dual-output pattern missing (StateVector + DecisionRecord).")

        constants = len(self._CONSTANT_RE.findall(diff_text))
        if constants > 2:
            issues.append(
                "Hard-coded constants detected. Prefer named constants or config-backed parameters."
            )

        math_lines = [ln for ln in lines if self._DIM_FUNC_RE.search(ln)]
        if any("Dimension" not in ln and not re.search(r"\[", ln) for ln in math_lines):
            issues.append("Potential dimensional expression check required around transform argument.")

        action = Action.ALLOW.value
        if issues:
            action = Action.DENY.value if not has_state else Action.QUARANTINE.value

        sv = StateVector(
            risk_score=min(1.0, 0.15 * len(issues)),
            layer_hits=[7, 12] if has_state else [12],
            hard_constants=constants,
            dimensional_issues=len(math_lines),
        )

        signature = sha256(diff_text.encode("utf-8")).hexdigest()
        decision = DecisionRecord(
            action=action,
            signature=signature,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="; ".join(issues) if issues else "No blocking issues.",
        )
        return AgentOutput(state_vector=sv, decision_record=decision)


def test_mock_diff() -> None:
    good = """
diff --git a/src/core.py b/src/core.py
@@
def route_response(ctx):
    vector = StateVector(risk_score=0.1, layer_hits=[7, 12], hard_constants=0, dimensional_issues=0)
    record = DecisionRecord(action=\"ALLOW\", signature=\"\", timestamp=\"\", reason=\"ok\")
    return vector, record
"""
    bad = """
diff --git a/src/core.py b/src/core.py
@@
def bad(ctx):
    return 3.14 * len(ctx)
"""
    agent = KOTongueCodeReviewer()
    ok = agent.review(good)
    fail = agent.review(bad)
    assert ok.decision_record.action == Action.ALLOW.value
    assert fail.decision_record.action in {Action.DENY.value, Action.QUARANTINE.value}
    assert isinstance(ok.state_vector.hard_constants, int)
    assert isinstance(asdict(fail), dict)
    print("OK", ok.decision_record.action, "| BAD", fail.decision_record.action)


if __name__ == "__main__":
    test_mock_diff()
