from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from .builtins import condition_node, emit_node
from .schema import (
    FlowDefinition,
    FlowEdgeDefinition,
    FlowExecutionState,
    FlowNodeDefinition,
    FlowQuarantineError,
    FlowRun,
    FlowStatus,
    FlowValidationError,
    NodeExecutionRecord,
    NodeStatus,
)

NodeHandler = Callable[
    [dict[str, Any], dict[str, Any], FlowExecutionState], dict[str, Any]
]


@dataclass
class _CacheEntry:
    output: dict[str, Any]
    expires_at: float | None


class InMemoryFlowCache:
    """Simple cache for deterministic node outputs."""

    def __init__(self, now_fn: Callable[[], float] | None = None) -> None:
        self._entries: dict[str, _CacheEntry] = {}
        self._now_fn = now_fn or time.time

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at <= self._now_fn():
            self._entries.pop(key, None)
            return None
        return copy.deepcopy(entry.output)

    def set(self, key: str, output: dict[str, Any], ttl_seconds: int | None) -> None:
        expires_at = None if ttl_seconds is None else self._now_fn() + ttl_seconds
        self._entries[key] = _CacheEntry(
            output=copy.deepcopy(output), expires_at=expires_at
        )


class NodeRegistry:
    """Registry of node handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, NodeHandler] = {}

    @classmethod
    def default(cls) -> "NodeRegistry":
        registry = cls()
        registry.register("emit", emit_node)
        registry.register("condition", condition_node)
        return registry

    def register(self, node_type: str, handler: NodeHandler) -> None:
        self._handlers[node_type] = handler

    def has(self, node_type: str) -> bool:
        return node_type in self._handlers

    def get(self, node_type: str) -> NodeHandler:
        try:
            return self._handlers[node_type]
        except KeyError as exc:
            raise FlowValidationError(f"Unknown node type '{node_type}'.") from exc


class FlowExecutor:
    """Fail-closed workflow runner for local node graphs."""

    def __init__(
        self,
        registry: NodeRegistry | None = None,
        cache: InMemoryFlowCache | None = None,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self.registry = registry or NodeRegistry.default()
        self.now_fn = now_fn or time.time
        self.cache = cache or InMemoryFlowCache(now_fn=self.now_fn)

    def load_workflow(self, payload: dict[str, Any]) -> FlowDefinition:
        workflow_id = str(payload.get("workflow_id") or payload.get("id") or "").strip()
        start_node_id = str(
            payload.get("start_node_id") or payload.get("start_at") or ""
        ).strip()
        if not workflow_id:
            raise FlowValidationError("Workflow id is required.")
        node_payloads = payload.get("nodes")
        if not isinstance(node_payloads, list) or not node_payloads:
            raise FlowValidationError("Workflow must define at least one node.")

        nodes: dict[str, FlowNodeDefinition] = {}
        for raw_node in node_payloads:
            node = FlowNodeDefinition.from_dict(raw_node)
            if node.node_id in nodes:
                raise FlowValidationError(f"Duplicate node id '{node.node_id}'.")
            if not self.registry.has(node.node_type):
                raise FlowValidationError(f"Unknown node type '{node.node_type}'.")
            nodes[node.node_id] = node

        if start_node_id not in nodes:
            raise FlowValidationError(
                f"Workflow start node '{start_node_id}' does not exist."
            )

        edges = tuple(
            FlowEdgeDefinition.from_dict(edge_payload)
            for edge_payload in payload.get("edges", [])
        )
        for edge in edges:
            if edge.source not in nodes:
                raise FlowValidationError(
                    f"Edge source '{edge.source}' does not exist."
                )
            if edge.target not in nodes:
                raise FlowValidationError(
                    f"Edge target '{edge.target}' does not exist."
                )

        return FlowDefinition(
            workflow_id=workflow_id,
            start_node_id=start_node_id,
            nodes=nodes,
            edges=edges,
        )

    def run(
        self,
        workflow_or_payload: FlowDefinition | dict[str, Any],
        initial_context: dict[str, Any] | None = None,
    ) -> FlowRun:
        workflow = (
            workflow_or_payload
            if isinstance(workflow_or_payload, FlowDefinition)
            else self.load_workflow(workflow_or_payload)
        )
        run = FlowRun(
            workflow_id=workflow.workflow_id,
            status=FlowStatus.RUNNING,
            context={"input": copy.deepcopy(initial_context or {})},
        )

        current_node_id = workflow.start_node_id
        while current_node_id:
            node = workflow.nodes[current_node_id]
            record = run.node_records.setdefault(
                current_node_id, NodeExecutionRecord(node_id=current_node_id)
            )
            try:
                output = self._execute_node(workflow, node, run, record)
            except FlowQuarantineError as exc:
                record.status = NodeStatus.QUARANTINED
                record.error = str(exc)
                run.status = FlowStatus.QUARANTINE
                run.quarantine_reason = str(exc)
                return run

            run.context[current_node_id] = copy.deepcopy(output)
            run.executed_order.append(current_node_id)
            run.final_output = copy.deepcopy(output)

            try:
                current_node_id = self._next_node_id(workflow, node, output)
            except FlowQuarantineError as exc:
                record.status = NodeStatus.QUARANTINED
                record.error = str(exc)
                run.status = FlowStatus.QUARANTINE
                run.quarantine_reason = str(exc)
                return run

        run.status = FlowStatus.COMPLETED
        return run

    def _execute_node(
        self,
        workflow: FlowDefinition,
        node: FlowNodeDefinition,
        run: FlowRun,
        record: NodeExecutionRecord,
    ) -> dict[str, Any]:
        resolved_config = self._resolve_value(node.config, run.context)
        cache_key = self._cache_key(workflow.workflow_id, node, resolved_config)
        cached_output = None
        if node.cache_ttl_seconds is not None:
            cached_output = self.cache.get(cache_key)

        if cached_output is not None:
            record.attempts += 1
            record.status = NodeStatus.COMPLETED
            record.output = copy.deepcopy(cached_output)
            record.from_cache = True
            return cached_output

        handler = self.registry.get(node.node_type)
        attempts_allowed = node.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts_allowed + 1):
            record.attempts = attempt
            record.status = NodeStatus.RUNNING
            state = FlowExecutionState(workflow=workflow, run=run, attempt=attempt)
            try:
                output = handler(copy.deepcopy(resolved_config), run.context, state)
                if not isinstance(output, dict):
                    raise FlowQuarantineError(
                        f"Node '{node.node_id}' returned a non-object payload."
                    )
                record.status = NodeStatus.COMPLETED
                record.output = copy.deepcopy(output)
                record.error = None
                if node.cache_ttl_seconds is not None:
                    self.cache.set(cache_key, output, node.cache_ttl_seconds)
                return output
            except FlowQuarantineError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                record.error = str(exc)
                if not node.retryable or attempt >= attempts_allowed:
                    break

        raise FlowQuarantineError(
            f"Node '{node.node_id}' failed after {record.attempts} attempt(s): {last_error}"
        )

    def _next_node_id(
        self,
        workflow: FlowDefinition,
        node: FlowNodeDefinition,
        output: dict[str, Any],
    ) -> str | None:
        outgoing = workflow.outgoing(node.node_id)
        if not outgoing:
            return None

        branch_edges = [edge for edge in outgoing if edge.when in {"true", "false"}]
        if branch_edges:
            result = output.get("result")
            if not isinstance(result, bool):
                raise FlowQuarantineError(
                    f"Condition node '{node.node_id}' did not return a boolean result."
                )
            route = "true" if result else "false"
            matches = [edge for edge in branch_edges if edge.when == route]
            if len(matches) != 1:
                raise FlowQuarantineError(
                    f"Condition node '{node.node_id}' is missing route '{route}'."
                )
            return matches[0].target

        if len(outgoing) > 1:
            raise FlowQuarantineError(
                f"Node '{node.node_id}' has ambiguous outgoing edges."
            )
        return outgoing[0].target

    def _resolve_value(self, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, str) and value.startswith("@"):
            return self._resolve_reference(value, context)
        if isinstance(value, list):
            return [self._resolve_value(item, context) for item in value]
        if isinstance(value, dict):
            return {
                key: self._resolve_value(item, context) for key, item in value.items()
            }
        return value

    def _resolve_reference(self, token: str, context: dict[str, Any]) -> Any:
        path = token[1:].split(".")
        current: Any = context
        for segment in path:
            if isinstance(current, dict) and segment in current:
                current = current[segment]
                continue
            raise FlowQuarantineError(f"Unresolved workflow reference '{token}'.")
        return current

    def _cache_key(
        self,
        workflow_id: str,
        node: FlowNodeDefinition,
        resolved_config: dict[str, Any],
    ) -> str:
        payload = json.dumps(
            {
                "workflow_id": workflow_id,
                "node_id": node.node_id,
                "node_type": node.node_type,
                "config": resolved_config,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
