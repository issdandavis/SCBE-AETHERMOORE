from __future__ import annotations

from typing import Any

from .schema import FlowQuarantineError, FlowExecutionState


def emit_node(
    config: dict[str, Any], context: dict[str, Any], state: FlowExecutionState
) -> dict[str, Any]:
    output = config.get("output", {})
    if not isinstance(output, dict):
        raise FlowQuarantineError(
            f"Node '{state.run.executed_order[-1] if state.run.executed_order else state.workflow.start_node_id}' "
            "resolved emit output to a non-object."
        )
    return output


def condition_node(
    config: dict[str, Any], context: dict[str, Any], state: FlowExecutionState
) -> dict[str, Any]:
    if "value" in config:
        value = config["value"]
        if not isinstance(value, bool):
            raise FlowQuarantineError("Condition nodes require a boolean 'value'.")
        return {"result": value}

    if "left" not in config:
        raise FlowQuarantineError("Condition nodes require 'value' or 'left'.")

    left = config["left"]
    op = str(config.get("op", "eq")).lower()
    right = config.get("right")

    operations = {
        "eq": lambda a, b: a == b,
        "neq": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
    }
    if op not in operations:
        raise FlowQuarantineError(f"Unsupported condition operator '{op}'.")

    return {"result": operations[op](left, right)}
