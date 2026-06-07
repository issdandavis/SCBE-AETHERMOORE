"""Gate candidate tool calls from model token output.

This adapter treats model output as a stream that may contain a tool call. It
does not execute anything. It extracts the candidate call, relabels the output
with the semantic mirror-tunnel tokenizer, and runs the trajectory gate before a
caller decides whether to execute, sandbox, review, or deny the tool.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from src.security.trajectory_risk_gate import (
    AccessLevel,
    TrajectoryDecision,
    TrajectoryRiskGate,
)
from src.tokenizer.semantic_mirror_tunnel import analyze_mirror_tunnel


@dataclass(frozen=True)
class CandidateToolCall:
    tool_name: str | None
    arguments: Mapping[str, Any] = field(default_factory=dict)
    raw_output: str = ""


@dataclass(frozen=True)
class TokenToolGateDecision:
    action: str
    tool_name: str | None
    risk_score: float
    intent_label: str
    labels: tuple[str, ...]
    reason: str
    token_count: int
    trajectory_decision: TrajectoryDecision
    requested_access: AccessLevel
    candidate: CandidateToolCall

    @property
    def allowed_to_execute(self) -> bool:
        return self.action == "execute"


_TOOL_LINE_RE = re.compile(
    r"\btool(?:_name)?\s*[:=]\s*([A-Za-z0-9_.:-]+)", re.IGNORECASE
)
_ARGS_LINE_RE = re.compile(
    r"\b(?:arguments|args|parameters)\s*[:=]\s*(\{.*\})", re.IGNORECASE | re.DOTALL
)


def extract_tool_call_from_token_output(
    token_output: str,
    *,
    requested_tool: str | None = None,
    requested_args: Mapping[str, Any] | None = None,
) -> CandidateToolCall:
    """Extract a best-effort candidate tool call from model output."""

    text = token_output or ""
    if requested_tool or requested_args:
        return CandidateToolCall(requested_tool, dict(requested_args or {}), text)

    stripped = text.strip()
    if stripped:
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, Mapping):
            nested = payload.get("function_call") or payload.get("tool_call")
            if isinstance(nested, Mapping):
                name = (
                    nested.get("name") or nested.get("tool") or nested.get("tool_name")
                )
                args = (
                    nested.get("arguments")
                    or nested.get("args")
                    or nested.get("parameters")
                    or {}
                )
                return CandidateToolCall(
                    str(name) if name else None, _coerce_args(args), text
                )

            name = (
                payload.get("tool") or payload.get("tool_name") or payload.get("name")
            )
            args = (
                payload.get("arguments")
                or payload.get("args")
                or payload.get("parameters")
                or {}
            )
            return CandidateToolCall(
                str(name) if name else None, _coerce_args(args), text
            )

    tool_match = _TOOL_LINE_RE.search(text)
    args_match = _ARGS_LINE_RE.search(text)
    args: Mapping[str, Any] = {}
    if args_match:
        try:
            args = _coerce_args(json.loads(args_match.group(1)))
        except json.JSONDecodeError:
            args = {"_raw": args_match.group(1)}

    return CandidateToolCall(tool_match.group(1) if tool_match else None, args, text)


def gate_tool_call_token_output(
    token_output: str,
    *,
    session_goal: str = "",
    user_authority: str = "standard",
    requested_tool: str | None = None,
    requested_args: Mapping[str, Any] | None = None,
) -> TokenToolGateDecision:
    """Classify a candidate tool call produced by token output."""

    candidate = extract_tool_call_from_token_output(
        token_output,
        requested_tool=requested_tool,
        requested_args=requested_args,
    )
    call_text = _call_text(candidate)
    mirror = analyze_mirror_tunnel(call_text)
    access = _access_for_candidate(candidate, mirror.intent_label)
    gate = TrajectoryRiskGate(session_goal=session_goal, user_authority=user_authority)
    trajectory = gate.evaluate(
        call_text,
        requested_access=access,
        declared_need="candidate tool call emitted by model token output",
        static_risk=mirror.risk_pressure,
    )
    action = _action_for(trajectory.decision)
    labels = tuple(sorted(mirror.labels))
    reason = f"{trajectory.decision.value}: {mirror.intent_label}"
    return TokenToolGateDecision(
        action=action,
        tool_name=candidate.tool_name,
        risk_score=trajectory.risk_score,
        intent_label=mirror.intent_label,
        labels=labels,
        reason=reason,
        token_count=len(re.findall(r"\S+", token_output or "")),
        trajectory_decision=trajectory.decision,
        requested_access=access,
        candidate=candidate,
    )


class StreamingTokenToolGate:
    """Accumulate token chunks and gate the full candidate output on demand."""

    def __init__(
        self, *, session_goal: str = "", user_authority: str = "standard"
    ) -> None:
        self.session_goal = session_goal
        self.user_authority = user_authority
        self._chunks: list[str] = []

    def feed(self, token_chunk: str) -> None:
        self._chunks.append(token_chunk)

    def evaluate(self) -> TokenToolGateDecision:
        return gate_tool_call_token_output(
            "".join(self._chunks),
            session_goal=self.session_goal,
            user_authority=self.user_authority,
        )

    def reset(self) -> None:
        self._chunks.clear()


def _coerce_args(value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"_raw": value}
        return parsed if isinstance(parsed, Mapping) else {"_raw": value}
    return value if isinstance(value, Mapping) else {}


def _call_text(candidate: CandidateToolCall) -> str:
    args_text = json.dumps(candidate.arguments, sort_keys=True, default=str)
    return f"tool: {candidate.tool_name or 'none'}\narguments: {args_text}\noutput: {candidate.raw_output}"


def _access_for_candidate(
    candidate: CandidateToolCall, intent_label: str
) -> AccessLevel:
    tool = (candidate.tool_name or "").lower()
    args_text = json.dumps(candidate.arguments, sort_keys=True, default=str).lower()
    joined = f"{tool} {args_text}"

    if intent_label in {"credential_harvest", "data_exfiltration"}:
        return AccessLevel.SECRETS
    if intent_label in {"audit_evasion", "reward_hacking"}:
        return AccessLevel.TOOLS
    if any(
        marker in joined
        for marker in [".env", "secret", "token", "password", "credential", "keyring"]
    ):
        return AccessLevel.SECRETS
    if any(
        marker in tool
        for marker in ["shell", "powershell", "bash", "cmd", "exec", "system"]
    ):
        return AccessLevel.TOOLS
    if any(marker in tool for marker in ["file", "filesystem", "repo", "path"]):
        return AccessLevel.FILES
    if any(marker in tool for marker in ["http", "network", "webhook", "curl"]):
        return AccessLevel.TOOLS
    return AccessLevel.PUBLIC


def _action_for(decision: TrajectoryDecision) -> str:
    if decision == TrajectoryDecision.ALLOW:
        return "execute"
    if decision in {
        TrajectoryDecision.ALLOW_WITH_LIMITS,
        TrajectoryDecision.ASK_CLARIFYING_SCOPE,
        TrajectoryDecision.SANDBOX,
    }:
        return "sandbox"
    if decision == TrajectoryDecision.HOLD_FOR_REVIEW:
        return "review"
    return "deny"


__all__ = [
    "CandidateToolCall",
    "StreamingTokenToolGate",
    "TokenToolGateDecision",
    "extract_tool_call_from_token_output",
    "gate_tool_call_token_output",
]
