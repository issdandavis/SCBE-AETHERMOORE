"""Triadic gate for compact agent handoff packets.

This module binds the existing secure handoff shape to the repo's triadic
surfaces:

1. Tri-Bundle packet receipt for compact payload provenance.
2. Lane-change signaling for provider/model handoff discipline.
3. Sheaf consensus over fast, memory, and governance signals.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from src.crypto.tri_bundle import encode_bytes
from src.harmonic.sheaf_consensus_gate import sheaf_gate

from .harness_providers import LaneSwitchVerdict, evaluate_lane_switch
from .packet import AgentPacketV1
from .secure_handoff import CANONICAL_SEPARATORS, semantic_shadow


SCHEMA = "agent_triadic_handoff_gate_v1"


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=CANONICAL_SEPARATORS, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class TriBundleReceipt:
    """Compact receipt proving the packet was projected into Tri-Bundle space."""

    schema: str
    tongue: str
    packet_sha256: str
    cluster_count: int
    first_cluster_id: str
    last_cluster_id: str
    mean_energy: float
    mean_synchronization: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TriadicHandoffGateResult:
    """Decision packet for an AI-to-AI handoff before or after sealing."""

    schema: str
    task_id: str
    decision: str
    lane_switch: LaneSwitchVerdict
    tri_bundle: TriBundleReceipt
    sheaf_gate: dict[str, Any]
    shadow: dict[str, Any]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "decision": self.decision,
            "lane_switch": self.lane_switch.to_dict(),
            "tri_bundle": self.tri_bundle.to_dict(),
            "sheaf_gate": self.sheaf_gate,
            "shadow": self.shadow,
            "reason": self.reason,
        }


def build_tri_bundle_receipt(packet: AgentPacketV1) -> TriBundleReceipt:
    """Encode a packet into Tri-Bundle clusters and return a compact receipt."""

    packet.validate()
    packet_bytes = _canonical_bytes(packet.to_dict())
    tongue = packet.route.tongue.lower()
    clusters = encode_bytes(packet_bytes, tongue)
    if not clusters:
        raise ValueError("tri-bundle receipt requires at least one encoded cluster")
    mean_energy = sum(cluster.energy() for cluster in clusters) / len(clusters)
    mean_sync = sum(cluster.synchronization_score() for cluster in clusters) / len(clusters)
    return TriBundleReceipt(
        schema="tri_bundle_receipt_v1",
        tongue=tongue,
        packet_sha256=f"sha256:{hashlib.sha256(packet_bytes).hexdigest()}",
        cluster_count=len(clusters),
        first_cluster_id=clusters[0].cluster_id_hex(),
        last_cluster_id=clusters[-1].cluster_id_hex(),
        mean_energy=round(float(mean_energy), 6),
        mean_synchronization=round(float(mean_sync), 6),
    )


def evaluate_triadic_handoff(
    packet: AgentPacketV1,
    *,
    model_refs: list[str] | None = None,
    lane_signal: str | None = None,
    fast_signal: float = 0.0,
    memory_signal: float = 0.0,
    governance_signal: float = 0.0,
    pqc_valid: float = 1.0,
    harm_score: float = 1.0,
    drift_factor: float = 1.0,
    spectral_score: float = 1.0,
) -> TriadicHandoffGateResult:
    """Evaluate a compact handoff using triadic packet, lane, and sheaf checks."""

    packet.validate()
    refs = model_refs or []
    lane = evaluate_lane_switch(refs, signal=lane_signal) if refs else evaluate_lane_switch([], signal=lane_signal)
    receipt = build_tri_bundle_receipt(packet)
    sheaf = sheaf_gate(
        fast_signal=fast_signal,
        memory_signal=memory_signal,
        governance_signal=governance_signal,
        pqc_valid=pqc_valid,
        harm_score=harm_score,
        drift_factor=drift_factor,
        spectral_score=spectral_score,
    ).to_dict()

    if not lane.ok:
        decision = "DENY"
        reason = "lane switch missing valid signal"
    elif sheaf["decision"] == "DENY":
        decision = "DENY"
        reason = "sheaf consensus denied handoff"
    elif sheaf["decision"] == "QUARANTINE":
        decision = "QUARANTINE"
        reason = "sheaf consensus requires quarantine"
    else:
        decision = "ALLOW"
        reason = "triadic handoff checks passed"

    return TriadicHandoffGateResult(
        schema=SCHEMA,
        task_id=packet.task_id,
        decision=decision,
        lane_switch=lane,
        tri_bundle=receipt,
        sheaf_gate=sheaf,
        shadow=semantic_shadow(packet),
        reason=reason,
    )


__all__ = [
    "SCHEMA",
    "TriBundleReceipt",
    "TriadicHandoffGateResult",
    "build_tri_bundle_receipt",
    "evaluate_triadic_handoff",
]
