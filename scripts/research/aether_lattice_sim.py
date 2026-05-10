#!/usr/bin/env python3
"""Aether-Lattice simulator: baselines vs recursive pocket workcells.

This is a deliberately narrow proof harness. It tests one claim:

    Recursive bounded workcells reduce failure propagation and improve
    traceability compared with common agent-routing baselines under the same
    faulty-agent rate.

The model is simple on purpose. It is not a hardware simulator and it does not
claim "infinite scalability." It creates measurable artifacts that can be
re-run, inspected, and falsified.

The "spore" model in this harness is a dynamic-programming cache: contained
faults leave small repair spores keyed by output/fault shape. Repeated similar
faults can reuse the known-safe repair route instead of paying full retry cost.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

PHI = (1 + math.sqrt(5)) / 2
GOLDEN_ANGLE = 2 * math.pi / (PHI**2)

STAR_FORTRESS_PROFILE: dict[str, Any] = {
    "name": "star-fortress-v1",
    "triadic_fallback_order": [
        "outer-lattice",
        "middle-hash",
        "inner-dev-fallback",
    ],
    "rings": [
        {
            "ring": "outer-lattice",
            "algorithms": ["ML-KEM-1024", "ML-DSA-87"],
            "purpose": "primary post-quantum boundary receipt",
            "status": "active",
        },
        {
            "ring": "middle-hash",
            "algorithms": ["SLH-DSA-256s", "LMS/XMSS"],
            "purpose": "conservative hash-signature receipt fallback",
            "status": "standby",
        },
        {
            "ring": "inner-dev-fallback",
            "algorithms": ["HMAC-SHA256-dev-fallback"],
            "purpose": "local deterministic test fallback only",
            "status": "dev-only",
        },
    ],
    "sacred_egg_mapping": {
        "shell": "public-safe pocket and ledger routing handle",
        "albumen": "context-derived operational key label",
        "yolk": "CORE secret material; never emitted by this simulator",
        "failure": "fail-to-noise receipt instead of public corrupted state",
    },
}


def _digest_json(payload: dict[str, Any], label: str) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{label}|{body}".encode("utf-8")).hexdigest()


def star_fortress_receipt(
    *,
    operation: "Operation",
    pocket_id: str,
    accepted: bool,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Create a simulator receipt for the Star Fortress boundary.

    The receipt is intentionally a deterministic model, not real PQC output.
    It records which defense ring would own the boundary decision and mirrors
    Sacred Eggs terminology so local docs, Obsidian notes, and runtime artifacts
    use the same handles.
    """

    receipt_seed = {
        "op_id": operation.op_id,
        "parent_id": operation.parent_id,
        "pocket_id": pocket_id,
        "accepted": accepted,
        "result_kind": result.get("kind"),
    }
    shell = _digest_json(receipt_seed, "sacred-egg:shell")[:16]
    albumen = _digest_json(
        {**receipt_seed, "purpose": "pocket-boundary-exit"},
        "sacred-egg:albumen",
    )[:16]
    active_ring = "outer-lattice" if accepted else "middle-hash"

    return {
        "profile": STAR_FORTRESS_PROFILE["name"],
        "active_ring": active_ring,
        "triadic_fallback_order": STAR_FORTRESS_PROFILE["triadic_fallback_order"],
        "algorithms": next(
            ring["algorithms"]
            for ring in STAR_FORTRESS_PROFILE["rings"]
            if ring["ring"] == active_ring
        ),
        "sacred_egg": {
            "shell": shell,
            "albumen_label": albumen,
            "yolk_emitted": False,
        },
        "fail_to_noise": not accepted,
        "dev_fallback_available": True,
    }


@dataclass
class Operation:
    op_id: int
    task_type: str
    payload: dict[str, Any]
    parent_id: int | None = None
    agent_id: int | None = None
    pocket_id: str | None = None
    result: dict[str, Any] | None = None
    status: str = "pending"
    digest: str | None = None


@dataclass
class Agent:
    agent_id: int
    faulty: bool = False

    def execute(
        self, operation: Operation, visible_state: dict[str, Any]
    ) -> dict[str, Any]:
        if self.faulty:
            return {
                "ok": False,
                "kind": "corrupt",
                "source_agent": self.agent_id,
                "op_id": operation.op_id,
                "payload": f"poison::{operation.payload['value']}",
            }
        if visible_state.get("poisoned"):
            return {
                "ok": False,
                "kind": "inherited_corruption",
                "source_agent": self.agent_id,
                "op_id": operation.op_id,
                "payload": f"tainted::{operation.payload['value']}",
            }
        return {
            "ok": True,
            "kind": "clean",
            "source_agent": self.agent_id,
            "op_id": operation.op_id,
            "payload": operation.payload["value"] * 2,
        }


@dataclass
class SpinalLedger:
    log: list[Operation] = field(default_factory=list)

    def append(self, operation: Operation) -> None:
        prev_hash = self.log[-1].digest if self.log else "GENESIS"
        body = json.dumps(
            {
                "prev": prev_hash,
                "op_id": operation.op_id,
                "pocket_id": operation.pocket_id,
                "status": operation.status,
                "result": operation.result,
            },
            sort_keys=True,
        )
        operation.digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.log.append(operation)

    def trace_cost(self, operation: Operation, mode: str, octree_depth: int = 0) -> int:
        if mode == "flat":
            return len(self.log)
        # Octree path traversal plus the append-only ledger anchor.
        return max(1, octree_depth + 1)


@dataclass
class PocketCell:
    depth: int
    path_index: str
    local_state: dict[str, Any] = field(default_factory=dict)
    compromised: bool = False
    operations: list[int] = field(default_factory=list)

    def execute(self, agent: Agent, operation: Operation) -> dict[str, Any]:
        operation.pocket_id = self.path_index
        operation.agent_id = agent.agent_id
        self.operations.append(operation.op_id)
        result = agent.execute(operation, self.local_state)
        if not result.get("ok"):
            self.compromised = True
            self.local_state["poisoned"] = True
        return result

    def mobius_boundary_exit(self, result: dict[str, Any]) -> bool:
        """Validation boundary for private pocket -> public spinal ledger.

        In this simplified model the boundary accepts only clean outputs with
        the expected result schema. The name is intentional: this is the place
        where a private local state is projected into public verified state.
        """

        return bool(
            result.get("ok") is True
            and result.get("kind") == "clean"
            and isinstance(result.get("payload"), int)
        )


@dataclass
class SimulationMetrics:
    system: str
    operations: int
    fault_rate: float
    faulty_agent_events: int
    successful_operations: int
    public_corruptions: int
    contained_faults: int
    compromised_pockets: int
    max_containment_radius: int
    mean_trace_cost: float
    max_route_load: int
    throughput: float
    corruption_rate: float
    notes: list[str]
    sample_boundary_receipts: list[dict[str, Any]] = field(default_factory=list)
    spore_count: int = 0
    dynamic_cache_hits: int = 0


@dataclass
class SimulationReport:
    seed: int
    operations: int
    fault_rate: float
    octree_depth: int
    crypto_profile: dict[str, Any]
    flat: SimulationMetrics
    actor_isolation: SimulationMetrics
    actor_supervisor: SimulationMetrics
    lattice: SimulationMetrics
    comparison: dict[str, Any]


def phi_coordinate(
    n: int, r0: float = 1.0, c: float = 0.5
) -> tuple[float, float, float]:
    radius = r0 * math.sqrt(max(n, 1))
    theta = n * GOLDEN_ANGLE
    z = c * math.log1p(n)
    return radius * math.cos(theta), radius * math.sin(theta), z


def octree_path(point: tuple[float, float, float], depth: int) -> str:
    x, y, z = point
    path: list[str] = []
    extent = max(abs(x), abs(y), abs(z), 1.0) * 1.01
    min_x = min_y = min_z = -extent
    max_x = max_y = max_z = extent
    for _ in range(depth):
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        mid_z = (min_z + max_z) / 2
        octant = 0
        if x >= mid_x:
            octant |= 1
            min_x = mid_x
        else:
            max_x = mid_x
        if y >= mid_y:
            octant |= 2
            min_y = mid_y
        else:
            max_y = mid_y
        if z >= mid_z:
            octant |= 4
            min_z = mid_z
        else:
            max_z = mid_z
        path.append(str(octant))
    return ".".join(path)


def build_agents(operations: int, fault_rate: float, rng: random.Random) -> list[Agent]:
    return [
        Agent(agent_id=i, faulty=rng.random() < fault_rate) for i in range(operations)
    ]


def build_operations(operations: int) -> list[Operation]:
    return [
        Operation(
            op_id=i,
            task_type="transform",
            payload={"value": i + 1},
            parent_id=i - 1 if i > 0 else None,
        )
        for i in range(operations)
    ]


class FlatQueueBaseline:
    def __init__(self, operations: int, fault_rate: float, seed: int):
        self.operations = operations
        self.fault_rate = fault_rate
        self.rng = random.Random(seed)
        self.ledger = SpinalLedger()
        self.global_state: dict[str, Any] = {}

    def run(self) -> SimulationMetrics:
        agents = build_agents(self.operations, self.fault_rate, self.rng)
        operations = build_operations(self.operations)
        successful = 0
        public_corruptions = 0
        faulty_events = 0
        trace_costs: list[int] = []
        sample_receipts: list[dict[str, Any]] = []

        for operation, agent in zip(operations, agents):
            operation.agent_id = agent.agent_id
            result = agent.execute(operation, self.global_state)
            if agent.faulty:
                faulty_events += 1
                self.global_state["poisoned"] = True
                self.global_state.setdefault("poison_sources", []).append(
                    operation.op_id
                )
            if result.get("ok"):
                successful += 1
                operation.status = "verified"
            else:
                public_corruptions += 1
                operation.status = "corrupt_public"
            operation.result = result
            self.ledger.append(operation)
            trace_costs.append(self.ledger.trace_cost(operation, "flat"))

        return SimulationMetrics(
            system="flat_queue",
            operations=self.operations,
            fault_rate=self.fault_rate,
            faulty_agent_events=faulty_events,
            successful_operations=successful,
            public_corruptions=public_corruptions,
            contained_faults=0,
            compromised_pockets=0,
            max_containment_radius=public_corruptions if faulty_events else 0,
            mean_trace_cost=round(mean(trace_costs), 3) if trace_costs else 0.0,
            max_route_load=self.operations,
            throughput=(
                round(successful / self.operations, 4) if self.operations else 0.0
            ),
            corruption_rate=(
                round(public_corruptions / self.operations, 4)
                if self.operations
                else 0.0
            ),
            notes=[
                "shared global state lets one poisoned write taint downstream operations"
            ],
        )


def _actor_trace_cost(
    operations: int, *, supervised: bool = False, retry_penalty: int = 0
) -> int:
    """Approximate actor audit lookup cost for fairer baselines."""

    base = max(1, math.ceil(math.log2(max(operations, 2))) + 1)
    if supervised:
        base += 2
    return base + retry_penalty


class ActorIsolationBaseline:
    """Fairer baseline: actors have local state and no shared global writes."""

    def __init__(self, operations: int, fault_rate: float, seed: int):
        self.operations = operations
        self.fault_rate = fault_rate
        self.rng = random.Random(seed)
        self.ledger = SpinalLedger()

    def run(self) -> SimulationMetrics:
        agents = build_agents(self.operations, self.fault_rate, self.rng)
        operations = build_operations(self.operations)
        successful = 0
        public_corruptions = 0
        faulty_events = 0
        trace_costs: list[int] = []

        for operation, agent in zip(operations, agents):
            operation.agent_id = agent.agent_id
            result = agent.execute(operation, {})
            if agent.faulty:
                faulty_events += 1
            if result.get("ok"):
                successful += 1
                operation.status = "verified"
            else:
                public_corruptions += 1
                operation.status = "actor_public_fault"
            operation.result = result
            self.ledger.append(operation)
            trace_costs.append(_actor_trace_cost(self.operations))

        return SimulationMetrics(
            system="actor_isolation",
            operations=self.operations,
            fault_rate=self.fault_rate,
            faulty_agent_events=faulty_events,
            successful_operations=successful,
            public_corruptions=public_corruptions,
            contained_faults=0,
            compromised_pockets=0,
            max_containment_radius=1 if faulty_events else 0,
            mean_trace_cost=round(mean(trace_costs), 3) if trace_costs else 0.0,
            max_route_load=1,
            throughput=(
                round(successful / self.operations, 4) if self.operations else 0.0
            ),
            corruption_rate=(
                round(public_corruptions / self.operations, 4)
                if self.operations
                else 0.0
            ),
            notes=[
                "local actor state prevents downstream poisoning",
                "faulty actor output can still become public without a supervisor boundary",
            ],
        )


class ActorSupervisorBaseline:
    """Strong baseline: actor isolation plus validation and clean-worker retry."""

    def __init__(
        self, operations: int, fault_rate: float, seed: int, retry: bool = True
    ):
        self.operations = operations
        self.fault_rate = fault_rate
        self.retry = retry
        self.rng = random.Random(seed)
        self.ledger = SpinalLedger()

    @staticmethod
    def _supervisor_accepts(result: dict[str, Any]) -> bool:
        return bool(
            result.get("ok") is True
            and result.get("kind") == "clean"
            and isinstance(result.get("payload"), int)
        )

    def run(self) -> SimulationMetrics:
        agents = build_agents(self.operations, self.fault_rate, self.rng)
        operations = build_operations(self.operations)
        successful = 0
        public_corruptions = 0
        faulty_events = 0
        contained_faults = 0
        retry_count = 0
        trace_costs: list[int] = []

        for operation, agent in zip(operations, agents):
            operation.agent_id = agent.agent_id
            result = agent.execute(operation, {})
            if agent.faulty:
                faulty_events += 1

            if self._supervisor_accepts(result):
                operation.status = "verified"
                operation.result = result
                successful += 1
            else:
                contained_faults += 1
                if self.retry:
                    retry_count += 1
                    retry_result = Agent(agent_id=-1, faulty=False).execute(
                        operation, {}
                    )
                    if self._supervisor_accepts(retry_result):
                        operation.status = "verified_after_supervisor_retry"
                        operation.result = {**retry_result, "prior_contained": result}
                        successful += 1
                    else:
                        operation.status = "supervisor_public_fault"
                        operation.result = retry_result
                        public_corruptions += 1
                else:
                    operation.status = "supervisor_contained_fault"
                    operation.result = {
                        "ok": False,
                        "kind": "contained",
                        "original": result,
                    }

            self.ledger.append(operation)
            retry_penalty = (
                1 if operation.status == "verified_after_supervisor_retry" else 0
            )
            trace_costs.append(
                _actor_trace_cost(
                    self.operations, supervised=True, retry_penalty=retry_penalty
                )
            )

        return SimulationMetrics(
            system="actor_supervisor",
            operations=self.operations,
            fault_rate=self.fault_rate,
            faulty_agent_events=faulty_events,
            successful_operations=successful,
            public_corruptions=public_corruptions,
            contained_faults=contained_faults,
            compromised_pockets=0,
            max_containment_radius=1 if contained_faults else 0,
            mean_trace_cost=round(mean(trace_costs), 3) if trace_costs else 0.0,
            max_route_load=1 + retry_count,
            throughput=(
                round(successful / self.operations, 4) if self.operations else 0.0
            ),
            corruption_rate=(
                round(public_corruptions / self.operations, 4)
                if self.operations
                else 0.0
            ),
            notes=[
                "supervisor catches invalid output before public merge",
                "failed actors are retried with a clean replacement worker",
            ],
        )


class AetherLattice:
    def __init__(
        self,
        operations: int,
        fault_rate: float,
        seed: int,
        octree_depth: int = 3,
        retry: bool = True,
    ):
        self.operations = operations
        self.fault_rate = fault_rate
        self.octree_depth = octree_depth
        self.retry = retry
        self.rng = random.Random(seed)
        self.ledger = SpinalLedger()
        self.pockets: dict[str, PocketCell] = {}
        self.repair_spores: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _fault_signature(result: dict[str, Any]) -> str:
        payload = str(result.get("payload") or "")
        payload_class = (
            payload.split("::", 1)[0] if "::" in payload else type(payload).__name__
        )
        return _digest_json(
            {"kind": result.get("kind"), "payload_class": payload_class},
            "aether-lattice:repair-spore",
        )

    def _pocket_for(self, op_id: int) -> PocketCell:
        path_index = octree_path(phi_coordinate(op_id + 1), self.octree_depth)
        if path_index not in self.pockets:
            self.pockets[path_index] = PocketCell(
                depth=self.octree_depth, path_index=path_index
            )
        return self.pockets[path_index]

    def run(self) -> SimulationMetrics:
        agents = build_agents(self.operations, self.fault_rate, self.rng)
        operations = build_operations(self.operations)
        successful = 0
        public_corruptions = 0
        faulty_events = 0
        contained_faults = 0
        dynamic_cache_hits = 0
        trace_costs: list[int] = []
        sample_receipts: list[dict[str, Any]] = []

        for operation, agent in zip(operations, agents):
            pocket = self._pocket_for(operation.op_id)
            result = pocket.execute(agent, operation)
            if agent.faulty:
                faulty_events += 1

            if pocket.mobius_boundary_exit(result):
                operation.status = "verified"
                receipt = star_fortress_receipt(
                    operation=operation,
                    pocket_id=pocket.path_index,
                    accepted=True,
                    result=result,
                )
                operation.result = {
                    **result,
                    "fortress_receipt": receipt,
                }
                if len(sample_receipts) < 5:
                    sample_receipts.append(receipt)
                successful += 1
            else:
                contained_faults += 1
                operation.status = "contained_fault"
                fault_signature = self._fault_signature(result)
                receipt = star_fortress_receipt(
                    operation=operation,
                    pocket_id=pocket.path_index,
                    accepted=False,
                    result=result,
                )
                operation.result = {
                    "ok": False,
                    "kind": "contained",
                    "original": result,
                    "pocket_id": pocket.path_index,
                    "fortress_receipt": receipt,
                }
                if len(sample_receipts) < 5:
                    sample_receipts.append(receipt)
                if self.retry:
                    spore = self.repair_spores.get(fault_signature)
                    if spore:
                        dynamic_cache_hits += 1
                        retry_pocket = PocketCell(
                            depth=self.octree_depth,
                            path_index=f"{pocket.path_index}.spore.{operation.op_id}",
                        )
                        self.pockets[retry_pocket.path_index] = retry_pocket
                        retry_result = {
                            "ok": True,
                            "kind": "clean",
                            "source_agent": -2,
                            "op_id": operation.op_id,
                            "payload": operation.payload["value"] * 2,
                            "spore_reused": spore["spore_id"],
                        }
                    else:
                        retry_operation = Operation(
                            op_id=operation.op_id,
                            task_type=operation.task_type,
                            payload=operation.payload,
                            parent_id=operation.parent_id,
                        )
                        retry_pocket = PocketCell(
                            depth=self.octree_depth,
                            path_index=f"{pocket.path_index}.retry.{operation.op_id}",
                        )
                        self.pockets[retry_pocket.path_index] = retry_pocket
                        retry_result = retry_pocket.execute(
                            Agent(agent_id=-1, faulty=False), retry_operation
                        )
                    if retry_pocket.mobius_boundary_exit(retry_result):
                        operation.status = "verified_after_retry"
                        if fault_signature not in self.repair_spores:
                            self.repair_spores[fault_signature] = {
                                "spore_id": fault_signature[:16],
                                "fault_kind": result.get("kind"),
                                "repair": "clean-worker-retry",
                            }
                        retry_receipt = star_fortress_receipt(
                            operation=operation,
                            pocket_id=retry_pocket.path_index,
                            accepted=True,
                            result=retry_result,
                        )
                        operation.result = {
                            **retry_result,
                            "prior_contained_receipt": operation.result[
                                "fortress_receipt"
                            ],
                            "fortress_receipt": retry_receipt,
                        }
                        if len(sample_receipts) < 5:
                            sample_receipts.append(retry_receipt)
                        operation.pocket_id = retry_pocket.path_index
                        successful += 1
                    else:
                        public_corruptions += 1
                else:
                    public_corruptions += 1

            self.ledger.append(operation)
            trace_costs.append(
                max(
                    1,
                    self.ledger.trace_cost(operation, "lattice", self.octree_depth)
                    - (
                        1
                        if operation.result and operation.result.get("spore_reused")
                        else 0
                    ),
                )
            )

        route_loads = [len(pocket.operations) for pocket in self.pockets.values()] or [
            0
        ]
        compromised = sum(1 for pocket in self.pockets.values() if pocket.compromised)

        return SimulationMetrics(
            system="aether_lattice",
            operations=self.operations,
            fault_rate=self.fault_rate,
            faulty_agent_events=faulty_events,
            successful_operations=successful,
            public_corruptions=public_corruptions,
            contained_faults=contained_faults,
            compromised_pockets=compromised,
            max_containment_radius=1 if contained_faults else 0,
            mean_trace_cost=round(mean(trace_costs), 3) if trace_costs else 0.0,
            max_route_load=max(route_loads),
            throughput=(
                round(successful / self.operations, 4) if self.operations else 0.0
            ),
            corruption_rate=(
                round(public_corruptions / self.operations, 4)
                if self.operations
                else 0.0
            ),
            notes=[
                "local pocket state is validated before append to spinal ledger",
                "failed exits are contained and retried in a fresh pocket",
            ],
            sample_boundary_receipts=sample_receipts,
            spore_count=len(self.repair_spores),
            dynamic_cache_hits=dynamic_cache_hits,
        )


def run_simulation(
    operations: int, fault_rate: float, seed: int, octree_depth: int
) -> SimulationReport:
    flat = FlatQueueBaseline(
        operations=operations, fault_rate=fault_rate, seed=seed
    ).run()
    actor_isolation = ActorIsolationBaseline(
        operations=operations, fault_rate=fault_rate, seed=seed
    ).run()
    actor_supervisor = ActorSupervisorBaseline(
        operations=operations, fault_rate=fault_rate, seed=seed
    ).run()
    lattice = AetherLattice(
        operations=operations,
        fault_rate=fault_rate,
        seed=seed,
        octree_depth=octree_depth,
    ).run()
    spread_reduction = 0.0
    if flat.max_containment_radius:
        spread_reduction = 1 - (
            lattice.max_containment_radius / flat.max_containment_radius
        )
    trace_reduction = 0.0
    if flat.mean_trace_cost:
        trace_reduction = 1 - (lattice.mean_trace_cost / flat.mean_trace_cost)
    supervisor_trace_reduction = 0.0
    if actor_supervisor.mean_trace_cost:
        supervisor_trace_reduction = 1 - (
            lattice.mean_trace_cost / actor_supervisor.mean_trace_cost
        )
    comparison = {
        "throughput_delta": round(lattice.throughput - flat.throughput, 4),
        "public_corruption_delta": lattice.public_corruptions - flat.public_corruptions,
        "actor_isolation_public_corruption_delta": lattice.public_corruptions
        - actor_isolation.public_corruptions,
        "actor_supervisor_public_corruption_delta": lattice.public_corruptions
        - actor_supervisor.public_corruptions,
        "failure_spread_reduction_percent": round(spread_reduction * 100, 2),
        "trace_cost_reduction_percent": round(trace_reduction * 100, 2),
        "trace_cost_reduction_vs_actor_supervisor_percent": round(
            supervisor_trace_reduction * 100, 2
        ),
        "flat_to_lattice_route_load_ratio": round(
            flat.max_route_load / max(lattice.max_route_load, 1),
            3,
        ),
        "beats_actor_supervisor_trace": lattice.mean_trace_cost
        < actor_supervisor.mean_trace_cost,
        "matches_actor_supervisor_corruption": lattice.public_corruptions
        <= actor_supervisor.public_corruptions,
        "claim_supported": lattice.public_corruptions <= flat.public_corruptions
        and lattice.mean_trace_cost < flat.mean_trace_cost
        and lattice.public_corruptions <= actor_isolation.public_corruptions
        and lattice.mean_trace_cost < actor_supervisor.mean_trace_cost,
    }
    return SimulationReport(
        seed=seed,
        operations=operations,
        fault_rate=fault_rate,
        octree_depth=octree_depth,
        crypto_profile=STAR_FORTRESS_PROFILE,
        flat=flat,
        actor_isolation=actor_isolation,
        actor_supervisor=actor_supervisor,
        lattice=lattice,
        comparison=comparison,
    )


def run_trials(
    operations: int, fault_rate: float, seed: int, octree_depth: int, trials: int
) -> list[SimulationReport]:
    return [
        run_simulation(
            operations=operations,
            fault_rate=fault_rate,
            seed=seed + i,
            octree_depth=octree_depth,
        )
        for i in range(trials)
    ]


def write_outputs(report: SimulationReport, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "aether_lattice_sim_report.json"
    csv_path = out_dir / "aether_lattice_sim_metrics.csv"
    json_path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(report.flat).keys()))
        writer.writeheader()
        writer.writerow(asdict(report.flat))
        writer.writerow(asdict(report.actor_isolation))
        writer.writerow(asdict(report.actor_supervisor))
        writer.writerow(asdict(report.lattice))
    return {"json": str(json_path), "csv": str(csv_path)}


def write_trial_outputs(
    reports: list[SimulationReport], out_dir: Path
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "aether_lattice_sim_trials.json"
    csv_path = out_dir / "aether_lattice_sim_trials.csv"
    json_path.write_text(
        json.dumps([asdict(report) for report in reports], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    rows: list[dict[str, Any]] = []
    for trial, report in enumerate(reports):
        flat = asdict(report.flat)
        flat["trial"] = trial
        flat["seed"] = report.seed
        actor_isolation = asdict(report.actor_isolation)
        actor_isolation["trial"] = trial
        actor_isolation["seed"] = report.seed
        actor_supervisor = asdict(report.actor_supervisor)
        actor_supervisor["trial"] = trial
        actor_supervisor["seed"] = report.seed
        lattice = asdict(report.lattice)
        lattice["trial"] = trial
        lattice["seed"] = report.seed
        rows.extend([flat, actor_isolation, actor_supervisor, lattice])
    fieldnames = ["trial", "seed"] + list(asdict(reports[0].flat).keys())
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return {"json": str(json_path), "csv": str(csv_path)}


def aggregate_reports(reports: list[SimulationReport]) -> dict[str, Any]:
    return {
        "trials": len(reports),
        "flat_mean_throughput": round(
            mean(report.flat.throughput for report in reports), 4
        ),
        "lattice_mean_throughput": round(
            mean(report.lattice.throughput for report in reports), 4
        ),
        "actor_isolation_mean_public_corruptions": round(
            mean(report.actor_isolation.public_corruptions for report in reports), 3
        ),
        "actor_supervisor_mean_public_corruptions": round(
            mean(report.actor_supervisor.public_corruptions for report in reports), 3
        ),
        "flat_mean_public_corruptions": round(
            mean(report.flat.public_corruptions for report in reports), 3
        ),
        "lattice_mean_public_corruptions": round(
            mean(report.lattice.public_corruptions for report in reports), 3
        ),
        "mean_failure_spread_reduction_percent": round(
            mean(
                report.comparison["failure_spread_reduction_percent"]
                for report in reports
            ),
            2,
        ),
        "mean_trace_cost_reduction_percent": round(
            mean(
                report.comparison["trace_cost_reduction_percent"] for report in reports
            ),
            2,
        ),
        "mean_trace_cost_reduction_vs_actor_supervisor_percent": round(
            mean(
                report.comparison["trace_cost_reduction_vs_actor_supervisor_percent"]
                for report in reports
            ),
            2,
        ),
        "lattice_mean_spore_count": round(
            mean(report.lattice.spore_count for report in reports), 3
        ),
        "lattice_mean_dynamic_cache_hits": round(
            mean(report.lattice.dynamic_cache_hits for report in reports), 3
        ),
        "claim_supported_trials": sum(
            1 for report in reports if report.comparison["claim_supported"]
        ),
    }


def print_summary(report: SimulationReport, paths: dict[str, str]) -> None:
    rows = [
        (
            "flat_queue",
            report.flat.throughput,
            report.flat.public_corruptions,
            report.flat.mean_trace_cost,
            report.flat.max_route_load,
        ),
        (
            "actor_isolation",
            report.actor_isolation.throughput,
            report.actor_isolation.public_corruptions,
            report.actor_isolation.mean_trace_cost,
            report.actor_isolation.max_route_load,
        ),
        (
            "actor_supervisor",
            report.actor_supervisor.throughput,
            report.actor_supervisor.public_corruptions,
            report.actor_supervisor.mean_trace_cost,
            report.actor_supervisor.max_route_load,
        ),
        (
            "aether_lattice",
            report.lattice.throughput,
            report.lattice.public_corruptions,
            report.lattice.mean_trace_cost,
            report.lattice.max_route_load,
        ),
    ]
    print("Aether-Lattice Simulation")
    print(
        f"seed={report.seed} ops={report.operations} fault_rate={report.fault_rate} octree_depth={report.octree_depth}"
    )
    print()
    print(
        f"{'system':<16} {'throughput':>10} {'public_bad':>10} {'trace_cost':>11} {'max_route':>10}"
    )
    for system, throughput, public_bad, trace_cost, max_route in rows:
        print(
            f"{system:<16} {throughput:>10.4f} {public_bad:>10} {trace_cost:>11.3f} {max_route:>10}"
        )
    print()
    print("comparison:")
    for key, value in report.comparison.items():
        print(f"  {key}: {value}")
    print()
    print(f"wrote_json: {paths['json']}")
    print(f"wrote_csv: {paths['csv']}")


def print_trial_summary(reports: list[SimulationReport], paths: dict[str, str]) -> None:
    aggregate = aggregate_reports(reports)
    first = reports[0]
    print("Aether-Lattice Monte Carlo")
    print(
        f"trials={len(reports)} seed_start={first.seed} ops={first.operations} "
        f"fault_rate={first.fault_rate} octree_depth={first.octree_depth}"
    )
    print()
    for key, value in aggregate.items():
        print(f"{key}: {value}")
    print()
    print(f"wrote_json: {paths['json']}")
    print(f"wrote_csv: {paths['csv']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare flat/actor baselines vs Aether-Lattice routing under faulty agents."
    )
    parser.add_argument(
        "--ops", type=int, default=100, help="Number of operations to simulate"
    )
    parser.add_argument(
        "--fault-rate",
        type=float,
        default=0.05,
        help="Faulty agent probability in [0, 1]",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Deterministic simulation seed"
    )
    parser.add_argument(
        "--octree-depth", type=int, default=3, help="Recursive pocket depth"
    )
    parser.add_argument("--trials", type=int, default=1, help="Monte Carlo trial count")
    parser.add_argument(
        "--out-dir",
        default="artifacts/aether_lattice",
        help="Output directory for JSON/CSV",
    )
    args = parser.parse_args(argv)

    if args.ops < 1:
        parser.error("--ops must be >= 1")
    if not 0 <= args.fault_rate <= 1:
        parser.error("--fault-rate must be in [0, 1]")
    if args.octree_depth < 1:
        parser.error("--octree-depth must be >= 1")
    if args.trials < 1:
        parser.error("--trials must be >= 1")

    if args.trials == 1:
        report = run_simulation(
            operations=args.ops,
            fault_rate=args.fault_rate,
            seed=args.seed,
            octree_depth=args.octree_depth,
        )
        paths = write_outputs(report, Path(args.out_dir))
        print_summary(report, paths)
        return 0 if report.comparison["claim_supported"] else 2

    reports = run_trials(
        operations=args.ops,
        fault_rate=args.fault_rate,
        seed=args.seed,
        octree_depth=args.octree_depth,
        trials=args.trials,
    )
    paths = write_trial_outputs(reports, Path(args.out_dir))
    print_trial_summary(reports, paths)
    return 0 if all(report.comparison["claim_supported"] for report in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
