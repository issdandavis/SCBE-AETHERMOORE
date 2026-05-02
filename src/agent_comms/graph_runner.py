"""
SCBE packet graph runner
========================

Small SCBE-native state-graph runner for AI-to-AI packet workflows.

This intentionally borrows the useful LangGraph-shaped idea (typed state,
checkpoint, conditional edge) without adopting a generic agent stack. The
runtime unit stays AgentPacketV1 and the judgment unit stays MergeReport.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from .ledger import PacketLedger, fingerprint
from .packet import AgentPacketV1, Budget, MergeReport, Route, enforce_budget, hash_state

SCHEMA_VERSION = "scbe_packet_graph_runner_v1"

NodeHandler = Callable[[AgentPacketV1], MergeReport]


@dataclass(frozen=True)
class GraphNode:
    """One packet execution phase."""

    node_id: str
    phase: str
    route: Route
    expected_output: str
    request: str | None = None
    budget: Budget | None = None
    handler_id: str = "validate_only"

    def validate(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must be non-empty")
        probe = AgentPacketV1(
            task_id="graph-node-probe",
            phase=self.phase,
            route=self.route,
            context_refs=[],
            state_hash=hash_state(self.node_id),
            budget=self.budget or Budget(max_input_tokens=128, max_output_tokens=64),
            request=self.request or "validate graph node",
            expected_output=self.expected_output,
        )
        probe.validate()


@dataclass(frozen=True)
class GraphEdge:
    """Decision-conditioned graph transition."""

    from_node: str
    to_node: str
    on_decision: str = "promote"

    def validate(self, node_ids: set[str]) -> None:
        if self.from_node not in node_ids:
            raise ValueError(f"edge.from_node {self.from_node!r} is not a graph node")
        if self.to_node not in node_ids:
            raise ValueError(f"edge.to_node {self.to_node!r} is not a graph node")
        if self.on_decision not in {"promote", "hold", "reject"}:
            raise ValueError("edge.on_decision must be promote, hold, or reject")


@dataclass(frozen=True)
class GraphCheckpoint:
    """Durable step record."""

    schema_version: str
    task_id: str
    graph_id: str
    node_id: str
    step_index: int
    packet_fingerprint: str
    state_hash: str
    decision: str
    merge_report: dict[str, Any]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GraphRunResult:
    """Complete graph execution trace."""

    schema_version: str
    graph_id: str
    task_id: str
    start_node: str
    final_node: str
    final_decision: str
    checkpoints: list[dict[str, Any]]
    path: list[str]
    halted_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_only_handler(packet: AgentPacketV1) -> MergeReport:
    """Default handler: validate packet shape and budget, then promote."""

    packet.validate()
    enforce_budget(packet)
    return MergeReport(
        claim=f"{packet.phase} packet validated",
        delta={
            "phase": packet.phase,
            "route": packet.route.tongue,
            "expected_output": packet.expected_output,
        },
        evidence=["packet:validated", "budget:within_limit"],
        contact_points=[f"hard:{packet.phase}", f"near:{packet.route.domain}"],
        decision="promote",
        task_id=packet.task_id,
    )


class PacketGraphRunner:
    """Deterministic graph executor for AgentPacketV1 workflows."""

    def __init__(
        self,
        *,
        graph_id: str,
        nodes: Iterable[GraphNode],
        edges: Iterable[GraphEdge],
        start_node: str,
        handlers: Optional[dict[str, NodeHandler]] = None,
        ledger: PacketLedger | None = None,
        checkpoint_path: Path | None = None,
    ) -> None:
        if not graph_id:
            raise ValueError("graph_id must be non-empty")
        self.graph_id = graph_id
        self.nodes = {node.node_id: node for node in nodes}
        if not self.nodes:
            raise ValueError("graph must contain at least one node")
        if start_node not in self.nodes:
            raise ValueError(f"start_node {start_node!r} is not a graph node")
        self.start_node = start_node
        for node in self.nodes.values():
            node.validate()
        node_ids = set(self.nodes)
        self.edges = list(edges)
        for edge in self.edges:
            edge.validate(node_ids)
        self.handlers = {"validate_only": validate_only_handler}
        self.handlers.update(handlers or {})
        self.ledger = ledger
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path is not None else None

    def _packet_for_node(self, base: AgentPacketV1, node: GraphNode) -> AgentPacketV1:
        packet = AgentPacketV1(
            task_id=base.task_id,
            phase=node.phase,
            route=node.route,
            context_refs=list(base.context_refs),
            state_hash=hash_state(base.state_hash, self.graph_id, node.node_id),
            budget=node.budget or base.budget,
            request=node.request or base.request,
            expected_output=node.expected_output,
            created_at=base.created_at,
        )
        packet.validate()
        return packet

    def _next_node(self, node_id: str, decision: str) -> str | None:
        for edge in self.edges:
            if edge.from_node == node_id and edge.on_decision == decision:
                return edge.to_node
        return None

    def _record_checkpoint(self, checkpoint: GraphCheckpoint) -> None:
        if self.checkpoint_path is None:
            return
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with self.checkpoint_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(checkpoint.to_dict(), sort_keys=True))
            fh.write("\n")

    def run(self, base_packet: AgentPacketV1, *, max_steps: int = 16) -> GraphRunResult:
        if max_steps <= 0:
            raise ValueError("max_steps must be > 0")
        base_packet.validate()
        current = self.start_node
        path: list[str] = []
        checkpoints: list[dict[str, Any]] = []
        final_decision = "hold"
        halted_reason = "max_steps"

        for step_index in range(max_steps):
            node = self.nodes[current]
            handler = self.handlers.get(node.handler_id)
            if handler is None:
                raise ValueError(f"no handler registered for {node.handler_id!r}")
            packet = self._packet_for_node(base_packet, node)
            cached = self.ledger.seen(packet) if self.ledger is not None else None
            report = cached or handler(packet)
            report.validate()
            if cached is None and self.ledger is not None:
                self.ledger.record(packet, report)

            checkpoint = GraphCheckpoint(
                schema_version=SCHEMA_VERSION,
                task_id=packet.task_id,
                graph_id=self.graph_id,
                node_id=current,
                step_index=step_index,
                packet_fingerprint=fingerprint(packet),
                state_hash=packet.state_hash,
                decision=report.decision,
                merge_report=report.to_dict(),
            )
            self._record_checkpoint(checkpoint)
            checkpoints.append(checkpoint.to_dict())
            path.append(current)
            final_decision = report.decision

            nxt = self._next_node(current, report.decision)
            if nxt is None:
                halted_reason = "terminal_decision"
                break
            current = nxt

        return GraphRunResult(
            schema_version=SCHEMA_VERSION,
            graph_id=self.graph_id,
            task_id=base_packet.task_id,
            start_node=self.start_node,
            final_node=path[-1] if path else self.start_node,
            final_decision=final_decision,
            checkpoints=checkpoints,
            path=path,
            halted_reason=halted_reason,
        )


def build_default_packet_graph(
    *,
    route_tongue: str = "KO",
    route_domain: str = "code",
    checkpoint_path: Path | None = None,
) -> PacketGraphRunner:
    """Default safe graph: plan -> verify -> merge, all validation-only."""

    nodes = [
        GraphNode(
            node_id="plan",
            phase="plan",
            route=Route(tongue=route_tongue, domain=route_domain, permission="read"),
            expected_output="delta",
            request="Build a compact implementation plan from the packet refs.",
        ),
        GraphNode(
            node_id="verify",
            phase="verify",
            route=Route(tongue=route_tongue, domain=route_domain, permission="read"),
            expected_output="verdict",
            request="Verify the packet refs and evidence before promotion.",
        ),
        GraphNode(
            node_id="merge",
            phase="merge",
            route=Route(tongue=route_tongue, domain=route_domain, permission="merge"),
            expected_output="verdict",
            request="Promote only if the hard and near contact points agree.",
        ),
    ]
    edges = [
        GraphEdge(from_node="plan", to_node="verify", on_decision="promote"),
        GraphEdge(from_node="verify", to_node="merge", on_decision="promote"),
    ]
    return PacketGraphRunner(
        graph_id="scbe-default-packet-graph-v1",
        nodes=nodes,
        edges=edges,
        start_node="plan",
        checkpoint_path=checkpoint_path,
    )


__all__ = [
    "SCHEMA_VERSION",
    "GraphCheckpoint",
    "GraphEdge",
    "GraphNode",
    "GraphRunResult",
    "PacketGraphRunner",
    "build_default_packet_graph",
    "validate_only_handler",
]
