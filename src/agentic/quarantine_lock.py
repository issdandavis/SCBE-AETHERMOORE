"""Canonical quarantine lock for agentic SCBE workcells.

The lock is deliberately cheap: confirmed hostile flows get less model, fewer
tools, shorter timeouts, and an audit-ready receipt. It is not a punitive
token drain. It is a containment state that prevents execution while preserving
enough evidence for review.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .dcp import DeployConditionPacket, ToolScope, TrustState

DecisionTier = Literal["ALLOW", "REVIEW", "QUARANTINE", "ESCALATE", "DENY"]
LockMode = Literal["normal", "review", "quarantine_lock", "deny_closed"]

SCHEMA_VERSION = "scbe.quarantine_lock.v1"


@dataclass(frozen=True)
class QuarantineLockPolicy:
    """Operator tunables for quarantine lock behavior."""

    review_token_budget: int = 512
    quarantine_token_budget: int = 128
    deny_token_budget: int = 16
    review_timeout_seconds: int = 60
    quarantine_timeout_seconds: int = 15
    deny_timeout_seconds: int = 1
    quarantine_ttl_seconds: int = 86_400
    max_time_dilation_factor: int = 16
    free_tier_model: str = "free_or_local_only"
    inspect_only_tools: tuple[str, ...] = (
        "read",
        "scan",
        "verify",
        "explain",
        "status",
        "health",
    )
    blocked_tool_classes: tuple[str, ...] = (
        "shell",
        "write",
        "network",
        "deploy",
        "delete",
        "browser",
        "payment",
        "secrets",
    )


@dataclass(frozen=True)
class QuarantineLockReceipt:
    """Decision receipt returned to callers before any risky execution."""

    schema_version: str
    lock_id: str
    generated_at: float
    decision: DecisionTier
    mode: LockMode
    locked: bool
    block_execution: bool
    isolate: bool
    model_tier: str
    token_budget: int | None
    timeout_seconds: int | None
    ttl_seconds: int | None
    time_dilation_factor: int
    allowed_tool_classes: tuple[str, ...]
    blocked_tool_classes: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["allowed_tool_classes"] = list(self.allowed_tool_classes)
        data["blocked_tool_classes"] = list(self.blocked_tool_classes)
        data["reasons"] = list(self.reasons)
        return data


def _normalize_decision(decision: str) -> DecisionTier:
    normalized = str(decision or "").strip().upper()
    aliases = {
        "HOLD": "REVIEW",
        "INSPECT": "REVIEW",
        "LOCKOUT": "QUARANTINE",
        "BLOCK": "DENY",
        "KILL": "DENY",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"ALLOW", "REVIEW", "QUARANTINE", "ESCALATE", "DENY"}:
        return "REVIEW"
    return normalized  # type: ignore[return-value]


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _time_dilation_factor(
    *,
    mode: LockMode,
    suspicion: float,
    harmonic_cost: float,
    confirmed_malicious: bool,
    policy: QuarantineLockPolicy,
) -> int:
    """Compute a deterministic throttle multiplier without sleeping or spending tokens."""

    if mode == "normal":
        return 1
    pressure = max(_clamp01(suspicion), _clamp01((float(harmonic_cost) - 1.0) / 9.0))
    if confirmed_malicious:
        pressure = 1.0
    base = 2 if mode == "review" else 4
    factor = base + round(pressure * (policy.max_time_dilation_factor - base))
    return max(1, min(policy.max_time_dilation_factor, factor))


def create_quarantine_lock(
    decision: str,
    *,
    suspicion: float = 0.0,
    harmonic_cost: float = 1.0,
    confirmed_malicious: bool = False,
    reasons: list[str] | tuple[str, ...] = (),
    policy: QuarantineLockPolicy | None = None,
) -> QuarantineLockReceipt:
    """Create the canonical lock receipt for a governance decision.

    Confirmed malicious input upgrades to quarantine lock even if the upstream
    decision was softer. DENY stays the terminal closed state.
    """

    policy = policy or QuarantineLockPolicy()
    normalized = _normalize_decision(decision)
    receipt_reasons = list(reasons)

    if normalized == "DENY":
        mode: LockMode = "deny_closed"
    elif confirmed_malicious or normalized == "QUARANTINE":
        mode = "quarantine_lock"
    elif normalized in {"REVIEW", "ESCALATE"}:
        mode = "review"
    else:
        mode = "normal"

    if confirmed_malicious and normalized not in {"DENY", "QUARANTINE"}:
        receipt_reasons.append("confirmed_malicious_upgraded_to_quarantine_lock")

    dilation = _time_dilation_factor(
        mode=mode,
        suspicion=suspicion,
        harmonic_cost=harmonic_cost,
        confirmed_malicious=confirmed_malicious,
        policy=policy,
    )

    if mode == "normal":
        return QuarantineLockReceipt(
            schema_version=SCHEMA_VERSION,
            lock_id=uuid.uuid4().hex,
            generated_at=time.time(),
            decision=normalized,
            mode=mode,
            locked=False,
            block_execution=False,
            isolate=False,
            model_tier="normal",
            token_budget=None,
            timeout_seconds=None,
            ttl_seconds=None,
            time_dilation_factor=dilation,
            allowed_tool_classes=("*",),
            blocked_tool_classes=(),
            reasons=tuple(receipt_reasons),
        )

    if mode == "review":
        return QuarantineLockReceipt(
            schema_version=SCHEMA_VERSION,
            lock_id=uuid.uuid4().hex,
            generated_at=time.time(),
            decision=normalized,
            mode=mode,
            locked=False,
            block_execution=True,
            isolate=False,
            model_tier=policy.free_tier_model,
            token_budget=policy.review_token_budget,
            timeout_seconds=policy.review_timeout_seconds,
            ttl_seconds=None,
            time_dilation_factor=dilation,
            allowed_tool_classes=policy.inspect_only_tools,
            blocked_tool_classes=policy.blocked_tool_classes,
            reasons=tuple(receipt_reasons),
        )

    if mode == "quarantine_lock":
        return QuarantineLockReceipt(
            schema_version=SCHEMA_VERSION,
            lock_id=uuid.uuid4().hex,
            generated_at=time.time(),
            decision="QUARANTINE",
            mode=mode,
            locked=True,
            block_execution=True,
            isolate=True,
            model_tier=policy.free_tier_model,
            token_budget=policy.quarantine_token_budget,
            timeout_seconds=policy.quarantine_timeout_seconds,
            ttl_seconds=policy.quarantine_ttl_seconds,
            time_dilation_factor=dilation,
            allowed_tool_classes=policy.inspect_only_tools,
            blocked_tool_classes=policy.blocked_tool_classes,
            reasons=tuple(receipt_reasons),
        )

    return QuarantineLockReceipt(
        schema_version=SCHEMA_VERSION,
        lock_id=uuid.uuid4().hex,
        generated_at=time.time(),
        decision="DENY",
        mode="deny_closed",
        locked=True,
        block_execution=True,
        isolate=True,
        model_tier=policy.free_tier_model,
        token_budget=policy.deny_token_budget,
        timeout_seconds=policy.deny_timeout_seconds,
        ttl_seconds=policy.quarantine_ttl_seconds,
        time_dilation_factor=dilation,
        allowed_tool_classes=(),
        blocked_tool_classes=("*",),
        reasons=tuple(receipt_reasons),
    )


def apply_quarantine_lock_to_dcp(
    dcp: DeployConditionPacket,
    receipt: QuarantineLockReceipt,
) -> DeployConditionPacket:
    """Apply a lock receipt to a DCP in place and return the same packet.

    The DCP is already the sealed workcell, so the lock attaches as constraints
    rather than creating a second envelope.
    """

    if receipt.mode == "normal":
        return dcp

    constraint_prefix = f"quarantine_lock:{receipt.mode}"
    constraints = list(dcp.processing_space.constraints)
    for constraint in (
        constraint_prefix,
        f"model_tier:{receipt.model_tier}",
        f"token_budget:{receipt.token_budget}",
        f"timeout_seconds:{receipt.timeout_seconds}",
        f"time_dilation_factor:{receipt.time_dilation_factor}",
    ):
        if constraint not in constraints:
            constraints.append(constraint)
    dcp.processing_space.constraints = constraints

    for tool in dcp.tools:
        if receipt.mode == "deny_closed":
            tool.scope = ToolScope.DENIED
            tool.trust_state = TrustState.DENY
        elif tool.name in receipt.allowed_tool_classes:
            tool.scope = ToolScope.RESTRICTED
            if tool.trust_state == TrustState.ALLOW:
                tool.trust_state = TrustState.QUARANTINE
        else:
            tool.scope = ToolScope.DENIED
            tool.trust_state = TrustState.QUARANTINE

    for gate in dcp.completion_gates:
        if receipt.timeout_seconds is not None:
            gate.timeout_seconds = min(gate.timeout_seconds, receipt.timeout_seconds)

    return dcp
