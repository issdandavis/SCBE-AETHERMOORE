from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FlowValidationError(ValueError):
    """Raised when a flow definition is malformed."""


class FlowQuarantineError(RuntimeError):
    """Raised when execution must fail closed."""


class FlowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    QUARANTINE = "quarantine"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class FlowNodeDefinition:
    node_id: str
    node_type: str
    config: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 0
    retryable: bool = True
    cache_ttl_seconds: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FlowNodeDefinition":
        node_id = str(payload.get("id") or payload.get("node_id") or "").strip()
        node_type = str(payload.get("type") or payload.get("node_type") or "").strip()
        if not node_id:
            raise FlowValidationError("Node id is required.")
        if not node_type:
            raise FlowValidationError(f"Node '{node_id}' is missing a type.")
        config = payload.get("config") or payload.get("with") or {}
        if not isinstance(config, dict):
            raise FlowValidationError(f"Node '{node_id}' config must be an object.")
        max_retries = int(payload.get("max_retries", 0))
        cache_ttl_seconds = payload.get("cache_ttl_seconds")
        if cache_ttl_seconds is not None:
            cache_ttl_seconds = int(cache_ttl_seconds)
        return cls(
            node_id=node_id,
            node_type=node_type,
            config=config,
            max_retries=max_retries,
            retryable=bool(payload.get("retryable", True)),
            cache_ttl_seconds=cache_ttl_seconds,
        )


@dataclass(frozen=True)
class FlowEdgeDefinition:
    source: str
    target: str
    when: str = "always"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FlowEdgeDefinition":
        source = str(payload.get("source") or payload.get("from") or "").strip()
        target = str(payload.get("target") or payload.get("to") or "").strip()
        when = str(payload.get("when") or "always").strip().lower()
        if not source or not target:
            raise FlowValidationError("Edges must include source and target ids.")
        if when not in {"always", "true", "false"}:
            raise FlowValidationError(
                f"Edge '{source}' -> '{target}' uses unsupported route '{when}'."
            )
        return cls(source=source, target=target, when=when)


@dataclass(frozen=True)
class FlowDefinition:
    workflow_id: str
    start_node_id: str
    nodes: dict[str, FlowNodeDefinition]
    edges: tuple[FlowEdgeDefinition, ...]

    def outgoing(self, node_id: str) -> list[FlowEdgeDefinition]:
        return [edge for edge in self.edges if edge.source == node_id]


@dataclass
class NodeExecutionRecord:
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    output: dict[str, Any] | None = None
    error: str | None = None
    from_cache: bool = False


@dataclass
class FlowRun:
    workflow_id: str
    status: FlowStatus = FlowStatus.PENDING
    executed_order: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    node_records: dict[str, NodeExecutionRecord] = field(default_factory=dict)
    final_output: dict[str, Any] | None = None
    quarantine_reason: str | None = None


@dataclass(frozen=True)
class FlowExecutionState:
    workflow: FlowDefinition
    run: FlowRun
    attempt: int
