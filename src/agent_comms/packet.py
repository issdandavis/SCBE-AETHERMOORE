"""
Agent Packet v1
===============

Compact AI-to-AI task packet that rides inside AgentMessage.payload.

Designed against four observed slacks in this repo:
  1. /harness/pair fans the full prompt to two models — token cost scales
     with prose length, not task complexity.
  2. AgentMessage carries an opaque payload dict — no shared semantics for
     budget, artifact references, state hashes, or expected output shape.
  3. Swarm coordination tends toward consensus echoes rather than
     compressed quorum verdicts.
  4. Agentic SFT risks training verbose chain-of-thought when the runtime
     contract only needs a structured delta.

The packet is a typed payload-shape, not a replacement for AgentMessage.
Transport (HMAC, TTL, hops, tongue, channel_id) stays in AgentMessage;
this module adds the semantics on top.

@module agent_comms/packet
@layer L13 (Risk decision)
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .message import AgentMessage, MessagePriority, MessageType

SCHEMA = "agent_packet_v1"

VALID_PHASES = ("plan", "edit", "verify", "merge")
VALID_PERMISSIONS = ("read", "edit", "merge")
VALID_EXPECTED = ("delta", "vote", "patch", "verdict")
VALID_REF_KINDS = ("sha256", "path", "url", "manifest_id")
VALID_DECISIONS = ("promote", "hold", "reject")
VALID_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


@dataclass
class Route:
    tongue: str
    domain: str
    permission: str

    def validate(self) -> None:
        if self.tongue not in VALID_TONGUES:
            raise ValueError(f"tongue must be one of {VALID_TONGUES}, got {self.tongue!r}")
        if self.permission not in VALID_PERMISSIONS:
            raise ValueError(f"permission must be one of {VALID_PERMISSIONS}, got {self.permission!r}")
        if not self.domain:
            raise ValueError("domain must be non-empty")


@dataclass
class ContextRef:
    kind: str
    value: str
    bytes: Optional[int] = None

    def validate(self) -> None:
        if self.kind not in VALID_REF_KINDS:
            raise ValueError(f"context_ref.kind must be one of {VALID_REF_KINDS}, got {self.kind!r}")
        if not self.value:
            raise ValueError("context_ref.value must be non-empty")


@dataclass
class Budget:
    max_input_tokens: int
    max_output_tokens: int

    def validate(self) -> None:
        if self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be > 0")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be > 0")


@dataclass
class AgentPacketV1:
    """
    Compact AI-to-AI task packet.

    request is a *minimal instruction*, not a full prompt. Heavy content
    must be referenced via context_refs (sha256 of the artifact, repo path,
    or manifest id) and dereferenced by the receiver against shared storage.
    """

    task_id: str
    phase: str
    route: Route
    context_refs: List[ContextRef]
    state_hash: str
    budget: Budget
    request: str
    expected_output: str
    schema: str = SCHEMA
    created_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError(f"schema must be {SCHEMA!r}, got {self.schema!r}")
        if self.phase not in VALID_PHASES:
            raise ValueError(f"phase must be one of {VALID_PHASES}, got {self.phase!r}")
        if self.expected_output not in VALID_EXPECTED:
            raise ValueError(f"expected_output must be one of {VALID_EXPECTED}, got {self.expected_output!r}")
        if not self.task_id:
            raise ValueError("task_id must be non-empty")
        if not self.state_hash:
            raise ValueError("state_hash must be non-empty")
        if not self.request:
            raise ValueError("request must be non-empty (use a context_ref for heavy content)")
        self.route.validate()
        self.budget.validate()
        for ref in self.context_refs:
            ref.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "phase": self.phase,
            "route": asdict(self.route),
            "context_refs": [asdict(r) for r in self.context_refs],
            "state_hash": self.state_hash,
            "budget": asdict(self.budget),
            "request": self.request,
            "expected_output": self.expected_output,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPacketV1":
        route = Route(**data["route"])
        budget = Budget(**data["budget"])
        refs = [ContextRef(**r) for r in data.get("context_refs", [])]
        return cls(
            task_id=data["task_id"],
            phase=data["phase"],
            route=route,
            context_refs=refs,
            state_hash=data["state_hash"],
            budget=budget,
            request=data["request"],
            expected_output=data["expected_output"],
            schema=data.get("schema", SCHEMA),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class MergeReport:
    """
    Compact verdict object returned by an agent finishing a packet.

    evidence and contact_points are short tagged strings, not prose. Format:
      evidence:        "<channel>:<value>"   e.g. "test:passed", "hash:matched"
      contact_points:  "<class>:<surface>"   e.g. "hard:pytest", "near:router"
    """

    claim: str
    delta: Dict[str, Any]
    evidence: List[str]
    contact_points: List[str]
    decision: str
    schema: str = "merge_report_v1"
    task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        if self.decision not in VALID_DECISIONS:
            raise ValueError(f"decision must be one of {VALID_DECISIONS}, got {self.decision!r}")
        if not self.claim:
            raise ValueError("claim must be non-empty")
        for tag in self.evidence + self.contact_points:
            if ":" not in tag:
                raise ValueError(f"tag {tag!r} must be 'channel:value' format")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergeReport":
        return cls(**data)


def new_task_id(prefix: str = "task") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def hash_state(*parts: str) -> str:
    """Deterministic state hash from string parts. Sorted to be order-stable."""
    h = hashlib.sha256()
    for part in sorted(parts):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return f"sha256:{h.hexdigest()[:32]}"


def pack(
    packet: AgentPacketV1,
    *,
    sender_id: str,
    recipient_id: str,
    action: str = "execute_packet",
    priority: MessagePriority = MessagePriority.NORMAL,
) -> AgentMessage:
    """
    Wrap an AgentPacketV1 in a transport AgentMessage.

    The packet's tongue routes the AgentMessage tongue field; the packet's
    expected ttl is bounded by AgentMessage default (300s).
    """
    packet.validate()
    return AgentMessage(
        sender_id=sender_id,
        recipient_id=recipient_id,
        message_type=MessageType.REQUEST,
        priority=priority,
        action=action,
        target=packet.route.domain,
        payload=packet.to_dict(),
        tongue=packet.route.tongue,
    )


def unpack(message: AgentMessage) -> AgentPacketV1:
    """Extract an AgentPacketV1 from a transport AgentMessage."""
    payload = message.payload or {}
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"message payload is not {SCHEMA} (got {payload.get('schema')!r})")
    packet = AgentPacketV1.from_dict(payload)
    packet.validate()
    return packet


def estimate_tokens(text: str) -> int:
    """Cheap token-count proxy. ~4 chars per token is the rough OpenAI heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def packet_input_tokens(packet: AgentPacketV1) -> int:
    """Estimate tokens this packet costs as input on the receiving side."""
    request_cost = estimate_tokens(packet.request)
    overhead_per_ref = 8
    refs_cost = sum(overhead_per_ref + estimate_tokens(r.value) for r in packet.context_refs)
    fixed_overhead = 32
    return request_cost + refs_cost + fixed_overhead


def enforce_budget(packet: AgentPacketV1) -> None:
    """
    Pre-flight check before sending. Raises BudgetExceeded if the packet
    itself already overruns its own input budget; there's nothing to gain
    by paying for the round-trip in that case.
    """
    cost = packet_input_tokens(packet)
    if cost > packet.budget.max_input_tokens:
        raise BudgetExceeded(
            f"packet {packet.task_id} input ~{cost} tokens "
            f"exceeds budget {packet.budget.max_input_tokens}; "
            "trim request or move content into a context_ref"
        )


class BudgetExceeded(Exception):
    """Raised when a packet's estimated input cost exceeds its declared budget."""


__all__ = [
    "SCHEMA",
    "VALID_PHASES",
    "VALID_PERMISSIONS",
    "VALID_EXPECTED",
    "VALID_REF_KINDS",
    "VALID_DECISIONS",
    "VALID_TONGUES",
    "Route",
    "ContextRef",
    "Budget",
    "AgentPacketV1",
    "MergeReport",
    "BudgetExceeded",
    "new_task_id",
    "hash_state",
    "pack",
    "unpack",
    "estimate_tokens",
    "packet_input_tokens",
    "enforce_budget",
]
