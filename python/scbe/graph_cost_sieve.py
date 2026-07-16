"""Cost-aware relationship assembly for compact computational graphs.

The module is intentionally backend-neutral. Adapters can supply ONNX, compiler,
tokenizer, or workflow measurements as JSON records. The sieve converts those
measurements into ranked rewrite moves and encodes each move program in byte,
binary, hexadecimal, and balanced-trit forms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from python.scbe.atomic_tokenization import map_token_to_atomic_state
from python.scbe.bit_spine import bytes_to_bits, bytes_to_trits
from src.tokenizer.atomic_workflow_units import build_atomic_workflow_unit


SIEVE_OPCODES: dict[str, int] = {
    "MEASURE": 0x10,
    "EXTRACT": 0x11,
    "RELATE": 0x12,
    "FACTOR": 0x13,
    "FOLD": 0x14,
    "FILL": 0x15,
    "EMIT": 0x16,
    "VERIFY": 0x17,
    "HOLD": 0x18,
}


@dataclass(frozen=True, slots=True)
class CostTarget:
    score: float
    cost: float


def score_from_cost(cost: float) -> float:
    """Return the NeuroGolf-style logarithmic score for a positive cost."""
    value = max(float(cost), 1.0)
    return max(1.0, 25.0 - math.log(value))


def cost_from_score(score: float) -> float:
    """Invert the logarithmic score in the non-clamped region."""
    return math.exp(25.0 - float(score))


def _number(record: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return float(default)


def _task_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    if not isinstance(payload, Mapping):
        raise ValueError("ledger must be a JSON object or list")

    rows: Any = payload.get("tasks", payload.get("ledger", payload.get("records")))
    if rows is None:
        rows = payload
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, Mapping)]
    if isinstance(rows, Mapping):
        out: list[dict[str, Any]] = []
        for task, value in rows.items():
            if not isinstance(value, Mapping):
                continue
            row = dict(value)
            row.setdefault("task", str(task))
            out.append(row)
        return out
    raise ValueError("ledger does not contain task records")


def _bottleneck(record: Mapping[str, Any], cost: float, target_cost: float) -> str:
    if cost <= target_cost:
        return "hold"

    params = _number(record, "initializer_elements", "params", "parameter_elements")
    intermediate = _number(record, "intermediate_bytes", "tensor_bytes", "memory_bytes")
    full_grid = _number(record, "full_grid_bytes", "dense_state_bytes")
    nodes = int(_number(record, "node_count", "nodes"))
    denominator = max(cost, params + intermediate, 1.0)

    if params / denominator >= 0.55:
        return "factor_constants"
    if full_grid / max(intermediate, 1.0) >= 0.40:
        return "factor_state"
    if nodes >= 64:
        return "collapse_iterations"
    if intermediate / denominator >= 0.65:
        return "reduce_composition"
    return "factor_relationships"


def _assembly_for(bottleneck: str) -> list[str]:
    return {
        "hold": ["MEASURE", "HOLD", "VERIFY"],
        "factor_constants": ["MEASURE", "EXTRACT", "FACTOR", "EMIT", "VERIFY"],
        "factor_state": ["MEASURE", "EXTRACT", "RELATE", "FACTOR", "FILL", "EMIT", "VERIFY"],
        "collapse_iterations": ["MEASURE", "EXTRACT", "RELATE", "FOLD", "FILL", "EMIT", "VERIFY"],
        "reduce_composition": ["MEASURE", "EXTRACT", "RELATE", "FILL", "EMIT", "VERIFY"],
        "factor_relationships": ["MEASURE", "RELATE", "FACTOR", "FILL", "EMIT", "VERIFY"],
    }[bottleneck]


def encode_assembly(tokens: Iterable[str]) -> dict[str, Any]:
    normalized = [str(token).strip().upper() for token in tokens]
    try:
        program = bytes(SIEVE_OPCODES[token] for token in normalized)
    except KeyError as exc:
        raise ValueError(f"unknown sieve opcode: {exc.args[0]}") from exc
    return {
        "tokens": normalized,
        "hex": program.hex(),
        "binary": bytes_to_bits(program),
        "balanced_trits": bytes_to_trits(program, balanced=True),
        "byte_count": len(program),
    }


def _token_vocabulary() -> dict[str, Any]:
    vocabulary: dict[str, Any] = {}
    for token, opcode in SIEVE_OPCODES.items():
        word = token.lower()
        atomic = map_token_to_atomic_state(word, context_class="operator")
        workflow = build_atomic_workflow_unit(word)
        vocabulary[token] = {
            "opcode": opcode,
            "opcode_hex": f"{opcode:02x}",
            "semantic_class": atomic.semantic_class,
            "element": atomic.element.symbol,
            "tau": atomic.tau.as_dict(),
            "workflow_role": workflow["semantic_lane"]["role"],
            "resource_cost": workflow["resource_cost"],
        }
    return vocabulary


def build_sieve_report(payload: Any, *, target_score: float = 20.360475) -> dict[str, Any]:
    """Build a ranked cost-reduction move ledger from JSON-compatible data."""
    target = CostTarget(score=float(target_score), cost=cost_from_score(target_score))
    actions: list[dict[str, Any]] = []

    for index, record in enumerate(_task_records(payload)):
        task = str(record.get("task") or record.get("task_id") or f"item{index:03d}")
        cost = _number(record, "selected_cost", "cost", "static_cost", "estimated_cost", default=-1.0)
        if cost <= 0.0 or not math.isfinite(cost):
            continue
        current_score = score_from_cost(cost)
        ratio = cost / target.cost
        gain = max(0.0, target.score - current_score)
        bottleneck = _bottleneck(record, cost, target.cost)
        assembly = encode_assembly(_assembly_for(bottleneck))
        nodes = int(_number(record, "node_count", "nodes"))
        full_grid = int(_number(record, "full_grid_bytes", "dense_state_bytes"))
        params = int(_number(record, "initializer_elements", "params", "parameter_elements"))
        intermediate = int(_number(record, "intermediate_bytes", "tensor_bytes", "memory_bytes"))
        pressure = math.log(max(ratio, 1.0))
        priority = gain * (1.0 + pressure) / (1.0 + math.log1p(max(nodes, 0)))
        actions.append(
            {
                "task": task,
                "source": record.get("source"),
                "cost": round(cost, 6),
                "current_score": round(current_score, 6),
                "target_score": round(target.score, 6),
                "target_cost": round(target.cost, 6),
                "compression_ratio_required": round(max(ratio, 1.0), 6),
                "score_gain_ceiling": round(gain, 6),
                "priority": round(priority, 6),
                "bottleneck": bottleneck,
                "dimensions": {
                    "nodes": nodes,
                    "initializer_elements": params,
                    "intermediate_bytes": intermediate,
                    "full_grid_bytes": full_grid,
                },
                "assembly": assembly,
            }
        )

    actions.sort(key=lambda row: (-row["priority"], -row["score_gain_ceiling"], row["task"]))
    costs = [float(row["cost"]) for row in actions]
    scores = [float(row["current_score"]) for row in actions]
    over_target = sum(float(row["cost"]) > target.cost for row in actions)
    geometric_cost = math.exp(sum(math.log(max(cost, 1.0)) for cost in costs) / len(costs)) if costs else 0.0

    return {
        "schema_version": "scbe-graph-cost-sieve-v1",
        "target": {"score": round(target.score, 6), "cost": round(target.cost, 6)},
        "summary": {
            "task_count": len(actions),
            "tasks_over_target": over_target,
            "known_score_sum": round(sum(scores), 6),
            "geometric_mean_cost": round(geometric_cost, 6),
            "projected_gain_if_all_hit_target": round(
                sum(float(row["score_gain_ceiling"]) for row in actions), 6
            ),
        },
        "opcode_vocabulary": _token_vocabulary(),
        "actions": actions,
    }


__all__ = [
    "CostTarget",
    "SIEVE_OPCODES",
    "build_sieve_report",
    "cost_from_score",
    "encode_assembly",
    "score_from_cost",
]
