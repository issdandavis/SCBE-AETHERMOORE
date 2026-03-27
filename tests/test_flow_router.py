from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_router import FlowExecutor, FlowStatus, FlowValidationError, InMemoryFlowCache, NodeRegistry


def build_executor(now_fn=None):
    registry = NodeRegistry.default()
    cache = InMemoryFlowCache(now_fn=now_fn)
    return FlowExecutor(registry=registry, cache=cache, now_fn=now_fn)


def minimal_spec():
    return {
        "workflow_id": "minimal-flow",
        "start_node_id": "start",
        "nodes": [
            {"id": "start", "type": "emit", "config": {"output": {"value": 1}}},
        ],
        "edges": [],
    }


def test_loads_minimal_valid_workflow():
    executor = build_executor()
    flow = executor.load_workflow(minimal_spec())

    assert flow.workflow_id == "minimal-flow"
    assert flow.start_node_id == "start"
    assert "start" in flow.nodes


def test_rejects_missing_start_node():
    executor = build_executor()
    spec = minimal_spec()
    spec["start_node_id"] = "missing"

    with pytest.raises(FlowValidationError, match="start node"):
        executor.load_workflow(spec)


def test_rejects_unknown_node_type():
    executor = build_executor()
    spec = minimal_spec()
    spec["nodes"][0]["type"] = "not-registered"

    with pytest.raises(FlowValidationError, match="Unknown node type"):
        executor.load_workflow(spec)


def test_interpolates_upstream_context_into_node_config():
    executor = build_executor()
    spec = {
        "workflow_id": "copy-flow",
        "start_node_id": "seed",
        "nodes": [
            {"id": "seed", "type": "emit", "config": {"output": {"body": "alpha"}}},
            {"id": "copy", "type": "emit", "config": {"output": {"copied": "@seed.body"}}},
        ],
        "edges": [{"source": "seed", "target": "copy"}],
    }

    run = executor.run(spec)

    assert run.status == FlowStatus.COMPLETED
    assert run.context["copy"]["copied"] == "alpha"
    assert run.executed_order == ["seed", "copy"]


def test_condition_true_routes_to_true_branch():
    executor = build_executor()
    spec = {
        "workflow_id": "branch-flow",
        "start_node_id": "gate",
        "nodes": [
            {
                "id": "gate",
                "type": "condition",
                "config": {"left": 5, "op": "eq", "right": 5},
            },
            {"id": "yes", "type": "emit", "config": {"output": {"route": "yes"}}},
            {"id": "no", "type": "emit", "config": {"output": {"route": "no"}}},
        ],
        "edges": [
            {"source": "gate", "target": "yes", "when": "true"},
            {"source": "gate", "target": "no", "when": "false"},
        ],
    }

    run = executor.run(spec)

    assert run.status == FlowStatus.COMPLETED
    assert run.executed_order == ["gate", "yes"]
    assert "no" not in run.node_records
    assert run.final_output == {"route": "yes"}


def test_missing_condition_path_quarantines():
    executor = build_executor()
    spec = {
        "workflow_id": "missing-branch",
        "start_node_id": "gate",
        "nodes": [
            {
                "id": "gate",
                "type": "condition",
                "config": {"left": 2, "op": "eq", "right": 3},
            },
            {"id": "yes", "type": "emit", "config": {"output": {"route": "yes"}}},
        ],
        "edges": [{"source": "gate", "target": "yes", "when": "true"}],
    }

    run = executor.run(spec)

    assert run.status == FlowStatus.QUARANTINE
    assert run.quarantine_reason is not None
    assert "missing route 'false'" in run.quarantine_reason
    assert run.executed_order == ["gate"]


def test_retry_succeeds_within_limit():
    executor = build_executor()
    attempts = {"count": 0}

    def flaky(config, context, state):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("try again")
        return {"ok": True, "attempt": attempts["count"]}

    executor.registry.register("flaky", flaky)
    spec = {
        "workflow_id": "retry-flow",
        "start_node_id": "job",
        "nodes": [
            {"id": "job", "type": "flaky", "max_retries": 2},
        ],
        "edges": [],
    }

    run = executor.run(spec)
    record = run.node_records["job"]

    assert run.status == FlowStatus.COMPLETED
    assert record.attempts == 2
    assert attempts["count"] == 2
    assert run.final_output == {"ok": True, "attempt": 2}


def test_retry_exhaustion_quarantines_fail_closed():
    executor = build_executor()

    def always_fail(config, context, state):
        raise RuntimeError("still broken")

    executor.registry.register("always_fail", always_fail)
    spec = {
        "workflow_id": "retry-fail-flow",
        "start_node_id": "job",
        "nodes": [
            {"id": "job", "type": "always_fail", "max_retries": 1},
        ],
        "edges": [],
    }

    run = executor.run(spec)
    record = run.node_records["job"]

    assert run.status == FlowStatus.QUARANTINE
    assert record.attempts == 2
    assert "failed after 2 attempt" in run.quarantine_reason


def test_cache_hit_skips_reexecution_for_identical_inputs():
    ticks = {"now": 100.0}
    executor = build_executor(now_fn=lambda: ticks["now"])
    invocations = {"count": 0}

    def counted(config, context, state):
        invocations["count"] += 1
        return {"value": config["value"], "count": invocations["count"]}

    executor.registry.register("counted", counted)
    spec = {
        "workflow_id": "cache-flow",
        "start_node_id": "job",
        "nodes": [
            {
                "id": "job",
                "type": "counted",
                "config": {"value": "@input.value"},
                "cache_ttl_seconds": 60,
            }
        ],
        "edges": [],
    }

    first = executor.run(spec, initial_context={"value": 7})
    second = executor.run(spec, initial_context={"value": 7})

    assert first.status == FlowStatus.COMPLETED
    assert second.status == FlowStatus.COMPLETED
    assert invocations["count"] == 1
    assert second.node_records["job"].from_cache is True
    assert second.final_output == first.final_output


def test_cache_miss_recomputes_when_input_changes():
    ticks = {"now": 100.0}
    executor = build_executor(now_fn=lambda: ticks["now"])
    invocations = {"count": 0}

    def counted(config, context, state):
        invocations["count"] += 1
        return {"value": config["value"], "count": invocations["count"]}

    executor.registry.register("counted", counted)
    spec = {
        "workflow_id": "cache-key-flow",
        "start_node_id": "job",
        "nodes": [
            {
                "id": "job",
                "type": "counted",
                "config": {"value": "@input.value"},
                "cache_ttl_seconds": 60,
            }
        ],
        "edges": [],
    }

    first = executor.run(spec, initial_context={"value": 1})
    second = executor.run(spec, initial_context={"value": 2})

    assert first.status == FlowStatus.COMPLETED
    assert second.status == FlowStatus.COMPLETED
    assert invocations["count"] == 2
    assert second.final_output["value"] == 2


def test_invalid_node_output_quarantines_immediately():
    executor = build_executor()

    def bad_output(config, context, state):
        return "not-an-object"

    executor.registry.register("bad_output", bad_output)
    spec = {
        "workflow_id": "bad-output-flow",
        "start_node_id": "job",
        "nodes": [{"id": "job", "type": "bad_output"}],
        "edges": [],
    }

    run = executor.run(spec)

    assert run.status == FlowStatus.QUARANTINE
    assert "non-object payload" in run.quarantine_reason


def test_end_to_end_success_path_with_branch_and_cache():
    ticks = {"now": 500.0}
    executor = build_executor(now_fn=lambda: ticks["now"])
    invocations = {"count": 0}

    def enrich(config, context, state):
        invocations["count"] += 1
        return {"payload": f"{config['prefix']}-{config['seed']}", "count": invocations["count"]}

    executor.registry.register("enrich", enrich)
    spec = {
        "workflow_id": "full-flow",
        "start_node_id": "seed",
        "nodes": [
            {"id": "seed", "type": "emit", "config": {"output": {"value": "@input.value"}}},
            {
                "id": "gate",
                "type": "condition",
                "config": {"left": "@seed.value", "op": "gt", "right": 3},
            },
            {
                "id": "enrich",
                "type": "enrich",
                "config": {"seed": "@seed.value", "prefix": "node"},
                "cache_ttl_seconds": 120,
            },
            {
                "id": "final",
                "type": "emit",
                "config": {"output": {"result": "@enrich.payload"}},
            },
            {"id": "reject", "type": "emit", "config": {"output": {"result": "reject"}}},
        ],
        "edges": [
            {"source": "seed", "target": "gate"},
            {"source": "gate", "target": "enrich", "when": "true"},
            {"source": "gate", "target": "reject", "when": "false"},
            {"source": "enrich", "target": "final"},
        ],
    }

    first = executor.run(spec, initial_context={"value": 6})
    second = executor.run(spec, initial_context={"value": 6})

    assert first.status == FlowStatus.COMPLETED
    assert second.status == FlowStatus.COMPLETED
    assert first.executed_order == ["seed", "gate", "enrich", "final"]
    assert first.final_output == {"result": "node-6"}
    assert second.node_records["enrich"].from_cache is True
    assert invocations["count"] == 1
