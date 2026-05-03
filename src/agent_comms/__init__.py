"""
Agent Communications Module
============================

AI-to-AI agent communication system using Sacred Tongues encoding
and SCBE governance for message routing and authorization.

Components:
- Message: Structured agent messages with tongue encoding
- Channel: Communication channels between agents
- Registry: Agent discovery and registration
- Router: Message routing with governance checks

@module agent_comms
@layer L13 (Risk decision), L14 (Telemetry)
"""

from .message import AgentMessage, MessagePriority, MessageType
from .channel import Channel, ChannelState
from .registry import AgentRegistry, AgentInfo
from .router import MessageRouter
from .packet import (
    AgentPacketV1,
    Budget,
    BudgetExceeded,
    ContextRef,
    MergeReport,
    Route,
    enforce_budget,
    hash_state,
    new_task_id,
    pack,
    packet_input_tokens,
    unpack,
)
from .ledger import LedgerEntry, PacketLedger, fingerprint
from .graph_runner import (
    GraphCheckpoint,
    GraphEdge,
    GraphNode,
    GraphRunResult,
    PacketGraphRunner,
    build_default_packet_graph,
    validate_only_handler,
)
from .lane_grid import (
    LANE_GRID_SCHEMA_VERSION,
    LaneCell,
    LaneGridResult,
    LaneGridScheduler,
    LaneSpec,
    SideStep,
    build_six_tongue_lane_grid,
    default_lane_handler,
)
from .harness_providers import (
    HarnessProvider,
    LaneSwitchVerdict,
    compact_system_prompt,
    default_provider_id,
    evaluate_lane_switch,
    lane_switch_cost,
    parse_model_ref,
    provider_registry,
    resolve_provider_model,
)
from .secure_handoff import (
    DecodeAgreement,
    HandoffIntegrityError,
    compactness_report,
    open_handoff,
    seal_handoff,
    semantic_shadow,
)
from .triadic_handoff import (
    TriBundleReceipt,
    TriadicHandoffGateResult,
    build_tri_bundle_receipt,
    evaluate_triadic_handoff,
)

__all__ = [
    "AgentMessage",
    "MessagePriority",
    "MessageType",
    "Channel",
    "ChannelState",
    "AgentRegistry",
    "AgentInfo",
    "MessageRouter",
    "AgentPacketV1",
    "Budget",
    "BudgetExceeded",
    "ContextRef",
    "MergeReport",
    "Route",
    "enforce_budget",
    "hash_state",
    "new_task_id",
    "pack",
    "packet_input_tokens",
    "unpack",
    "LedgerEntry",
    "PacketLedger",
    "fingerprint",
    "GraphCheckpoint",
    "GraphEdge",
    "GraphNode",
    "GraphRunResult",
    "PacketGraphRunner",
    "build_default_packet_graph",
    "validate_only_handler",
    "LANE_GRID_SCHEMA_VERSION",
    "LaneCell",
    "LaneGridResult",
    "LaneGridScheduler",
    "LaneSpec",
    "SideStep",
    "build_six_tongue_lane_grid",
    "default_lane_handler",
    "HarnessProvider",
    "LaneSwitchVerdict",
    "compact_system_prompt",
    "default_provider_id",
    "evaluate_lane_switch",
    "lane_switch_cost",
    "parse_model_ref",
    "provider_registry",
    "resolve_provider_model",
    "DecodeAgreement",
    "HandoffIntegrityError",
    "compactness_report",
    "open_handoff",
    "seal_handoff",
    "semantic_shadow",
    "TriBundleReceipt",
    "TriadicHandoffGateResult",
    "build_tri_bundle_receipt",
    "evaluate_triadic_handoff",
]
