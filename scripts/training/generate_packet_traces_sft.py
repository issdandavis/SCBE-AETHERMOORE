#!/usr/bin/env python3
"""generate_packet_traces_sft.py — record real packet-graph runs as SFT.

Replaces ``generate_agentic_sft.py``'s fabricated tool-call prose with
structured executable traces from the SCBE packet graph runner.

Each canonical seed AgentPacketV1 is run through the default
plan -> verify -> merge graph (validate-only handlers, no model calls).
The runner's GraphCheckpoints and the final GraphRunResult are emitted
as SFT pairs whose ``response`` field is a stable JSON document
(sort_keys=True, indent=2) — never prose, never fabricated tool args.

Two pair categories per seed run:
  - ``agentic-merge-verdict``  (one per checkpoint, response = MergeReport)
  - ``agentic-packet-trace``   (one per run,        response = GraphRunResult)

Determinism: task_id, created_at, and time.time() are all pinned. Two
invocations of this generator must produce byte-identical JSONL output.

Output: training-data/agentic_coding/packet_traces.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent_comms import (  # noqa: E402
    AgentPacketV1,
    Budget,
    ContextRef,
    Route,
    build_default_packet_graph,
    fingerprint,
    hash_state,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "training-data" / "agentic_coding" / "packet_traces.jsonl"

GENERATOR_NAME = "generate_packet_traces_sft.py"
GENERATOR_VERSION = "1"

# Pinning created_at to 0.0 makes the packet (and downstream MergeReport
# that the validate handler stamps) byte-stable across invocations.
PINNED_CREATED_AT = 0.0


def _seed_packets() -> list[AgentPacketV1]:
    """Canonical seed corpus — six packets covering tongues, phases, and refs.

    Each packet has a fixed task_id and created_at=0.0 so the generator
    emits identical bytes on every run. The seeds intentionally span the
    six Sacred Tongues and the four packet phases so the resulting trace
    corpus is not skewed toward one route.
    """

    return [
        AgentPacketV1(
            task_id="seed-ko-plan-readme",
            phase="plan",
            route=Route(tongue="KO", domain="code", permission="read"),
            context_refs=[ContextRef(kind="path", value="README.md")],
            state_hash=hash_state("seed:ko-plan", "repo:main"),
            budget=Budget(max_input_tokens=2048, max_output_tokens=512),
            request="Plan the patch from the README skeleton.",
            expected_output="delta",
            created_at=PINNED_CREATED_AT,
        ),
        AgentPacketV1(
            task_id="seed-av-verify-manifest",
            phase="verify",
            route=Route(tongue="AV", domain="docs", permission="read"),
            context_refs=[
                ContextRef(kind="manifest_id", value="2026-05-02-aligned-foundations-v2"),
            ],
            state_hash=hash_state("seed:av-verify", "manifest:aligned-v2"),
            budget=Budget(max_input_tokens=4096, max_output_tokens=512),
            request="Verify the aligned-foundations manifest summary.",
            expected_output="verdict",
            created_at=PINNED_CREATED_AT,
        ),
        AgentPacketV1(
            task_id="seed-ru-edit-tokenizer",
            phase="edit",
            route=Route(tongue="RU", domain="tokenizer", permission="edit"),
            context_refs=[ContextRef(kind="path", value="src/tokenizer/index.ts")],
            state_hash=hash_state("seed:ru-edit", "module:tokenizer"),
            budget=Budget(max_input_tokens=3072, max_output_tokens=1024),
            request="Apply the tongue-routing patch to the tokenizer.",
            expected_output="patch",
            created_at=PINNED_CREATED_AT,
        ),
        AgentPacketV1(
            task_id="seed-ca-merge-harmonic",
            phase="merge",
            route=Route(tongue="CA", domain="harmonic", permission="merge"),
            context_refs=[ContextRef(kind="path", value="src/harmonic/pipeline14.ts")],
            state_hash=hash_state("seed:ca-merge", "module:harmonic"),
            budget=Budget(max_input_tokens=2048, max_output_tokens=256),
            request="Merge the validated harmonic-pipeline change.",
            expected_output="verdict",
            created_at=PINNED_CREATED_AT,
        ),
        AgentPacketV1(
            task_id="seed-um-plan-fleet",
            phase="plan",
            route=Route(tongue="UM", domain="fleet", permission="read"),
            context_refs=[
                ContextRef(kind="path", value="src/fleet/juggling-scheduler.ts"),
                ContextRef(kind="path", value="hydra/juggling_scheduler.py"),
            ],
            state_hash=hash_state("seed:um-plan", "module:fleet"),
            budget=Budget(max_input_tokens=4096, max_output_tokens=512),
            request="Plan the dual-language scheduler review.",
            expected_output="delta",
            created_at=PINNED_CREATED_AT,
        ),
        AgentPacketV1(
            task_id="seed-dr-verify-governance",
            phase="verify",
            route=Route(tongue="DR", domain="governance", permission="read"),
            context_refs=[ContextRef(kind="path", value="src/governance/decision.ts")],
            state_hash=hash_state("seed:dr-verify", "module:governance"),
            budget=Budget(max_input_tokens=2048, max_output_tokens=256),
            request="Verify the L13 governance decision contract.",
            expected_output="verdict",
            created_at=PINNED_CREATED_AT,
        ),
    ]


def _strip_created_at(obj: Any) -> Any:
    """Remove every ``created_at`` field from a nested dict/list payload.

    The graph runner stamps ``created_at`` on GraphCheckpoint and the
    validate handler stamps one on MergeReport via ``time.time()``. To get
    byte-stable JSONL we drop those clocks at serialization time rather
    than fork the runner just for SFT export.
    """

    if isinstance(obj, dict):
        return {k: _strip_created_at(v) for k, v in obj.items() if k != "created_at"}
    if isinstance(obj, list):
        return [_strip_created_at(v) for v in obj]
    return obj


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, indent=2)


def _verdict_pair(
    *,
    packet: AgentPacketV1,
    graph_id: str,
    node_id: str,
    step_index: int,
    packet_fingerprint: str,
    state_hash: str,
    merge_report: dict[str, Any],
) -> dict[str, Any]:
    instruction = (
        f"Run packet {packet.task_id} at node {node_id!r} of graph "
        f"{graph_id!r}. Phase: {packet.phase}. Route: "
        f"{packet.route.tongue}/{packet.route.domain}/{packet.route.permission}. "
        f"Expected output: {packet.expected_output}. "
        "Return the MergeReport that the runtime would produce."
    )
    response = _stable_json(_strip_created_at(merge_report))
    return {
        "id": f"trace-verdict-{packet.task_id}-{node_id}",
        "category": "agentic-merge-verdict",
        "instruction": instruction,
        "response": response,
        "metadata": {
            "source": "scbe_packet_graph_runner_v1",
            "generator": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "graph_id": graph_id,
            "node_id": node_id,
            "step_index": step_index,
            "task_id": packet.task_id,
            "phase": packet.phase,
            "tongue": packet.route.tongue,
            "domain": packet.route.domain,
            "permission": packet.route.permission,
            "expected_output": packet.expected_output,
            "packet_fingerprint": packet_fingerprint,
            "state_hash": state_hash,
        },
    }


def _trace_pair(*, packet: AgentPacketV1, run_result: dict[str, Any]) -> dict[str, Any]:
    instruction = (
        f"Execute packet {packet.task_id} on graph "
        f"{run_result['graph_id']!r} starting at node "
        f"{run_result['start_node']!r}. Return the full GraphRunResult "
        "trace including every checkpoint."
    )
    response = _stable_json(_strip_created_at(run_result))
    return {
        "id": f"trace-run-{packet.task_id}",
        "category": "agentic-packet-trace",
        "instruction": instruction,
        "response": response,
        "metadata": {
            "source": "scbe_packet_graph_runner_v1",
            "generator": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "graph_id": run_result["graph_id"],
            "task_id": packet.task_id,
            "phase": packet.phase,
            "tongue": packet.route.tongue,
            "domain": packet.route.domain,
            "start_node": run_result["start_node"],
            "final_node": run_result["final_node"],
            "final_decision": run_result["final_decision"],
            "halted_reason": run_result["halted_reason"],
            "checkpoints": len(run_result.get("checkpoints", [])),
        },
    }


def generate_pairs() -> list[dict[str, Any]]:
    """Run every seed packet through the default graph and emit SFT pairs."""

    pairs: list[dict[str, Any]] = []
    for seed in _seed_packets():
        # One graph per seed so per-seed runs are independent. The runner
        # is deterministic given pinned task_id + state_hash + graph_id.
        runner = build_default_packet_graph(
            route_tongue=seed.route.tongue,
            route_domain=seed.route.domain,
        )
        result = runner.run(seed)
        result_dict = result.to_dict()
        for cp in result_dict["checkpoints"]:
            pairs.append(
                _verdict_pair(
                    packet=seed,
                    graph_id=cp["graph_id"],
                    node_id=cp["node_id"],
                    step_index=cp["step_index"],
                    packet_fingerprint=cp["packet_fingerprint"],
                    state_hash=cp["state_hash"],
                    merge_report=deepcopy(cp["merge_report"]),
                )
            )
        pairs.append(_trace_pair(packet=seed, run_result=deepcopy(result_dict)))
    return pairs


def write_jsonl(pairs: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for pair in pairs:
            fh.write(json.dumps(pair, sort_keys=True))
            fh.write("\n")


def recompute_fingerprint_from_metadata(meta: dict[str, Any]) -> str | None:
    """Reconstruct a verdict-pair's per-node packet fingerprint from metadata.

    The runner derives a per-node packet via ``hash_state(base.state_hash,
    graph_id, node_id)`` and replaces phase/route/request/expected_output
    from the GraphNode. This helper mirrors that derivation so a test can
    prove ``metadata.packet_fingerprint`` came from a real run, not a
    synthesized string.
    """

    seeds = {p.task_id: p for p in _seed_packets()}
    seed = seeds.get(meta.get("task_id", ""))
    if seed is None:
        return None
    graph_id = meta.get("graph_id")
    node_id = meta.get("node_id")
    if not graph_id or not node_id:
        return None

    runner = build_default_packet_graph(
        route_tongue=seed.route.tongue,
        route_domain=seed.route.domain,
    )
    node = runner.nodes.get(node_id)
    if node is None or runner.graph_id != graph_id:
        return None

    derived = AgentPacketV1(
        task_id=seed.task_id,
        phase=node.phase,
        route=node.route,
        context_refs=list(seed.context_refs),
        state_hash=hash_state(seed.state_hash, graph_id, node_id),
        budget=node.budget or seed.budget,
        request=node.request or seed.request,
        expected_output=node.expected_output,
        created_at=seed.created_at,
    )
    return fingerprint(derived)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    pairs = generate_pairs()
    write_jsonl(pairs, args.output)
    print(f"wrote {len(pairs)} SFT pairs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
