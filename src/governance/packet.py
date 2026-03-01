"""Canonical packet contract for automation actions."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, Iterable):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _coerce_scalar(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()


def _coerce_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


@dataclass
class PacketPolicy:
    decision: str = "UNKNOWN"
    reasons: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risk_score: float = 0.0


@dataclass
class PacketCost:
    estimate_usd: float = 0.0
    actual_usd: float = 0.0


@dataclass
class PacketReceipt:
    signature: str = ""
    pointer: str = ""
    signed_at: str = field(default_factory=_utc_iso_now)


@dataclass
class GovernancePacket:
    packet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_utc_iso_now)
    actor_id: str = ""
    agent_id: str = ""
    intent: str = ""
    category: str = ""
    targets: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""
    policy: PacketPolicy = field(default_factory=PacketPolicy)
    cost: PacketCost = field(default_factory=PacketCost)
    evidence: List[str] = field(default_factory=list)
    receipts: List[PacketReceipt] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if "policy" in payload and isinstance(self.policy, PacketPolicy):
            payload["policy"] = asdict(self.policy)
        if "cost" in payload and isinstance(self.cost, PacketCost):
            payload["cost"] = asdict(self.cost)
        payload["receipts"] = [asdict(r) for r in self.receipts]
        return payload

    @property
    def idempotency_token(self) -> str:
        if self.idempotency_key:
            return self.idempotency_key
        raw = "|".join([self.packet_id, self.intent, self.category, ",".join(self.targets)])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def packet_from_request(
    payload: Mapping[str, Any] | None,
    *,
    headers: Mapping[str, str] | None = None,
    defaults: Optional[Mapping[str, Any]] = None,
) -> GovernancePacket:
    """Build a governance packet from body payload and optional headers."""
    merged: Dict[str, Any] = {}
    if defaults:
        merged.update({k: v for k, v in defaults.items()})
    if payload:
        merged.update(payload)

    headers = headers or {}
    header_map = {
        "x-packet-id": "packet_id",
        "x-idempotency-key": "idempotency_key",
        "x-actor-id": "actor_id",
        "x-agent-id": "agent_id",
        "x-intent": "intent",
        "x-category": "category",
        "x-targets": "targets",
    }
    for header_key, target_key in header_map.items():
        raw = headers.get(header_key)
        if raw:
            merged[target_key] = raw if target_key != "targets" else _coerce_str_list(raw)

    policy_input = merged.get("policy") or {}
    if isinstance(policy_input, Mapping):
        policy = PacketPolicy(
            decision=_coerce_scalar(policy_input.get("decision"), "UNKNOWN"),
            reasons=_coerce_str_list(policy_input.get("reasons")),
            constraints=_coerce_str_list(policy_input.get("constraints")),
            risk_score=_coerce_float(policy_input.get("risk_score"), 0.0),
        )
    else:
        policy = PacketPolicy()

    cost_input = merged.get("cost") or {}
    if isinstance(cost_input, Mapping):
        cost = PacketCost(
            estimate_usd=_coerce_float(cost_input.get("estimate_usd"), 0.0),
            actual_usd=_coerce_float(cost_input.get("actual_usd"), 0.0),
        )
    else:
        cost = PacketCost()

    receipts_input = merged.get("receipts") or []
    receipts: List[PacketReceipt] = []
    if isinstance(receipts_input, list):
        for entry in receipts_input:
            if isinstance(entry, Mapping):
                receipts.append(
                    PacketReceipt(
                        signature=_coerce_scalar(entry.get("signature")),
                        pointer=_coerce_scalar(entry.get("pointer")),
                        signed_at=_coerce_scalar(entry.get("signed_at"), _utc_iso_now()),
                    )
                )

    return GovernancePacket(
        packet_id=_coerce_scalar(merged.get("packet_id"), str(uuid.uuid4())),
        created_at=_coerce_scalar(merged.get("created_at"), _utc_iso_now()),
        actor_id=_coerce_scalar(merged.get("actor_id")),
        agent_id=_coerce_scalar(merged.get("agent_id")),
        intent=_coerce_scalar(merged.get("intent")),
        category=_coerce_scalar(merged.get("category")),
        targets=_coerce_str_list(merged.get("targets", [])),
        inputs=dict(merged.get("inputs") or {}),
        idempotency_key=_coerce_scalar(merged.get("idempotency_key")),
        policy=policy,
        cost=cost,
        evidence=_coerce_str_list(merged.get("evidence", [])),
        receipts=receipts,
    )
