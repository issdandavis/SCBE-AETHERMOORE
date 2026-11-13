"""Bounded atomic-neighborhood context for frozen SCBE components.

This module connects the existing :mod:`atomic_tokenization` and
:mod:`chemical_fusion` runtimes without changing either frozen implementation.
It treats chemistry as a graph prior and a testable controller, not as a claim
that token states are physical atoms.

The semantic charge solve is inspired by charge equilibration, but uses a
positive graph-Laplacian coupling rather than a physical Coulomb kernel.  The
result is therefore named ``semantic_charge`` throughout.  Learned or derived
charges may propose fusion weights; they never receive execution authority.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

from .atomic_tokenization import AtomicTokenState, map_token_to_atomic_state
from .chemical_fusion import FusionParams, FusionResult, fuse_atomic_states
from .reaction_state import sha256_value

ATOMIC_CONTEXT_SCHEMA = "scbe_atomic_context_bundle_v1"
SEMANTIC_CHARGE_SCHEMA = "scbe_semantic_charge_equilibrium_v1"
DRIFT_CLOCK_SCHEMA = "scbe_computational_drift_clock_v1"


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value.lower()
    )


def _finite_tuple(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain at least one finite coordinate")
    return result


@dataclass(frozen=True, slots=True)
class AtomicNodeContext:
    """One immutable token-state node plus its local controller state."""

    node_id: str
    token_index: int
    atomic_state: AtomicTokenState
    position: tuple[float, ...]
    hardness: float
    initial_charge: float = 0.0
    representation_id: str = "atomic-token-state-v1"

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must not be empty")
        if self.token_index < 0:
            raise ValueError("token_index must be non-negative")
        object.__setattr__(
            self, "position", _finite_tuple(self.position, name="position")
        )
        if not math.isfinite(self.hardness) or self.hardness <= 0.0:
            raise ValueError("hardness must be finite and positive")
        if not math.isfinite(self.initial_charge):
            raise ValueError("initial_charge must be finite")
        if not self.representation_id:
            raise ValueError("representation_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AtomicEdgeContext:
    """A typed local relationship between two atomic token nodes."""

    source_id: str
    target_id: str
    relation: str
    coupling: float
    distance: float
    provenance: str

    def __post_init__(self) -> None:
        if not self.source_id or not self.target_id:
            raise ValueError("edge endpoints must not be empty")
        if self.source_id == self.target_id:
            raise ValueError("self effects belong in node hardness, not a self edge")
        if not self.relation or not self.provenance:
            raise ValueError("edge relation and provenance must not be empty")
        if not math.isfinite(self.coupling) or self.coupling < 0.0:
            raise ValueError("edge coupling must be finite and non-negative")
        if not math.isfinite(self.distance) or self.distance < 0.0:
            raise ValueError("edge distance must be finite and non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AtomicContextBundle:
    """Minimal context shared across the atomic, STISTA, and receipt seams."""

    bundle_id: str
    tokenizer_id: str
    token_table_sha256: str
    runtime_profile: str
    context_epoch: int
    step_clock: int
    total_charge: float
    nodes: tuple[AtomicNodeContext, ...]
    edges: tuple[AtomicEdgeContext, ...]
    parent_bundle_hash: str | None = None
    schema_version: str = ATOMIC_CONTEXT_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        if self.schema_version != ATOMIC_CONTEXT_SCHEMA:
            raise ValueError(
                f"unsupported atomic context schema: {self.schema_version!r}"
            )
        if not self.bundle_id or not self.tokenizer_id or not self.runtime_profile:
            raise ValueError(
                "bundle_id, tokenizer_id, and runtime_profile are required"
            )
        if not _is_sha256(self.token_table_sha256):
            raise ValueError("token_table_sha256 must be a 64-character SHA-256 digest")
        if self.parent_bundle_hash is not None and not _is_sha256(
            self.parent_bundle_hash
        ):
            raise ValueError(
                "parent_bundle_hash must be a SHA-256 digest when supplied"
            )
        if self.context_epoch < 0 or self.step_clock < 0:
            raise ValueError("context_epoch and step_clock must be non-negative")
        if not math.isfinite(self.total_charge):
            raise ValueError("total_charge must be finite")
        if not self.nodes:
            raise ValueError("an atomic context bundle requires at least one node")

        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node_id values must be unique")
        dimensions = {len(node.position) for node in self.nodes}
        if len(dimensions) != 1:
            raise ValueError("all node positions must have the same dimensionality")

        known = set(node_ids)
        undirected_pairs: set[tuple[str, str]] = set()
        for edge in self.edges:
            if edge.source_id not in known or edge.target_id not in known:
                raise ValueError("every edge endpoint must name a node in the bundle")
            pair = tuple(sorted((edge.source_id, edge.target_id)))
            if pair in undirected_pairs:
                raise ValueError(f"duplicate undirected edge: {pair}")
            undirected_pairs.add(pair)

    def content_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def bundle_hash(self) -> str:
        return sha256_value(self.content_dict())


@dataclass(frozen=True, slots=True)
class SemanticChargeEquilibrium:
    """Deterministic semantic-charge solution and its audit diagnostics."""

    bundle_hash: str
    charge_by_node: tuple[tuple[str, float], ...]
    edge_tension: tuple[tuple[str, str, float], ...]
    total_charge: float
    conservation_error: float
    projected_residual: float
    condition_number: float
    energy: float
    active_bound_count: int
    converged: bool
    method: str = "box-constrained-graph-laplacian-qeq-inspired-v2"
    schema_version: str = SEMANTIC_CHARGE_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "charge_by_node",
            tuple(
                (str(node_id), float(value)) for node_id, value in self.charge_by_node
            ),
        )
        object.__setattr__(
            self,
            "edge_tension",
            tuple(
                (str(source), str(target), float(value))
                for source, target, value in self.edge_tension
            ),
        )
        if self.active_bound_count < 0:
            raise ValueError("active_bound_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def charges(self) -> dict[str, float]:
        return dict(self.charge_by_node)

    @property
    def result_hash(self) -> str:
        return sha256_value(self.to_dict())


@dataclass(frozen=True, slots=True)
class ComputationalDriftClock:
    """Dimensionless scheduler telemetry; this is not relativistic time."""

    bundle_hash: str
    equilibrium_hash: str
    step_clock: int
    context_epoch: int
    mean_charge_motion: float
    congestion: float
    route_cost: float
    pressure: float
    model_time_increment: float
    wrapped_phase_radians: float
    schema_version: str = DRIFT_CLOCK_SCHEMA
    claim_boundary: str = (
        "scheduler telemetry only; not photon propagation or physical time dilation"
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _euclidean(left: Sequence[float], right: Sequence[float]) -> float:
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


def _knn_edges(
    nodes: Sequence[AtomicNodeContext], neighbor_count: int
) -> tuple[AtomicEdgeContext, ...]:
    if neighbor_count < 0:
        raise ValueError("neighbor_count must be non-negative")
    if len(nodes) <= 1 or neighbor_count == 0:
        return ()

    pair_distances: dict[tuple[int, int], float] = {}
    bounded_k = min(neighbor_count, len(nodes) - 1)
    for index, node in enumerate(nodes):
        candidates = sorted(
            (
                (_euclidean(node.position, other.position), other.node_id, other_index)
                for other_index, other in enumerate(nodes)
                if other_index != index
            ),
            key=lambda item: (item[0], item[1]),
        )
        for distance, _other_id, other_index in candidates[:bounded_k]:
            pair = tuple(sorted((index, other_index)))
            pair_distances[pair] = distance

    return tuple(
        AtomicEdgeContext(
            source_id=nodes[left].node_id,
            target_id=nodes[right].node_id,
            relation="local-knn",
            coupling=1.0 / (1.0 + distance),
            distance=distance,
            provenance="deterministic-euclidean-knn-v1",
        )
        for (left, right), distance in sorted(pair_distances.items())
    )


def build_atomic_context_bundle(
    tokens: Sequence[str],
    *,
    tokenizer_id: str,
    token_table_sha256: str,
    runtime_profile: str,
    positions: Sequence[Sequence[float]] | None = None,
    language: str | None = None,
    context_class: str | None = None,
    context_epoch: int = 0,
    step_clock: int = 0,
    total_charge: float = 0.0,
    neighbor_count: int = 2,
    parent_bundle_hash: str | None = None,
) -> AtomicContextBundle:
    """Build a deterministic local graph over exact atomic token states."""

    token_list = list(tokens)
    if not token_list:
        raise ValueError("tokens must not be empty")
    if positions is None:
        position_list = [(float(index),) for index in range(len(token_list))]
    else:
        if len(positions) != len(token_list):
            raise ValueError("positions length must match tokens length")
        position_list = [
            _finite_tuple(position, name="position") for position in positions
        ]

    nodes: list[AtomicNodeContext] = []
    for index, (token, position) in enumerate(zip(token_list, position_list)):
        state = map_token_to_atomic_state(
            token, language=language, context_class=context_class
        )
        # Positive and bounded. Adaptable nodes are softer; resilient nodes are
        # harder to move. This is a controller prior, not atomic hardness in eV.
        hardness = 0.5 + state.resilience + (0.5 * (1.0 - state.adaptivity))
        nodes.append(
            AtomicNodeContext(
                node_id=f"node-{index:04d}",
                token_index=index,
                atomic_state=state,
                position=tuple(position),
                hardness=hardness,
            )
        )

    edges = _knn_edges(nodes, neighbor_count)
    identity_seed = {
        "tokenizer_id": tokenizer_id,
        "token_table_sha256": token_table_sha256,
        "runtime_profile": runtime_profile,
        "context_epoch": context_epoch,
        "step_clock": step_clock,
        "total_charge": float(total_charge),
        "tokens": token_list,
        "positions": position_list,
        "language": language,
        "context_class": context_class,
        "neighbor_count": neighbor_count,
        "parent_bundle_hash": parent_bundle_hash,
    }
    return AtomicContextBundle(
        bundle_id=f"atomic-context:{sha256_value(identity_seed)[:24]}",
        tokenizer_id=tokenizer_id,
        token_table_sha256=token_table_sha256,
        runtime_profile=runtime_profile,
        context_epoch=context_epoch,
        step_clock=step_clock,
        total_charge=float(total_charge),
        nodes=tuple(nodes),
        edges=edges,
        parent_bundle_hash=parent_bundle_hash,
    )


def _solve_box_equality_qp(
    system: np.ndarray,
    linear_term: np.ndarray,
    *,
    total: float,
    cap: float,
    tolerance: float,
) -> tuple[np.ndarray, float, int, float]:
    """Solve a strictly convex equality-plus-box quadratic by active set.

    The objective is ``0.5*q.T@system@q + linear_term.T@q`` with
    ``sum(q)=total`` and ``-cap <= q_i <= cap``. Unlike radial clipping, this
    re-solves the coupled free variables whenever a bound activates and checks
    the bound KKT signs before returning.
    """

    if not math.isfinite(cap) or cap <= 0.0:
        raise ValueError("max_abs_charge must be finite and positive")
    count = int(system.shape[0])
    if count == 0 or system.shape != (count, count) or linear_term.shape != (count,):
        raise ValueError("invalid semantic-charge quadratic dimensions")
    if abs(float(total)) > (count * cap) + tolerance:
        raise ValueError(
            "max_abs_charge is incompatible with the requested total charge"
        )

    lower = -float(cap)
    upper = float(cap)
    active: dict[int, float] = {}
    solution = np.zeros(count, dtype=np.float64)
    lagrange = 0.0
    max_iterations = max(32, 20 * count * count)

    for _iteration in range(max_iterations):
        fixed = sorted(active)
        free = [index for index in range(count) if index not in active]
        solution.fill(0.0)
        for index, value in active.items():
            solution[index] = value

        if free:
            free_index = np.asarray(free, dtype=np.int64)
            fixed_index = np.asarray(fixed, dtype=np.int64)
            free_system = system[np.ix_(free_index, free_index)]
            right_hand = -linear_term[free_index]
            if fixed:
                right_hand = right_hand - (
                    system[np.ix_(free_index, fixed_index)] @ solution[fixed_index]
                )
            augmented = np.zeros((len(free) + 1, len(free) + 1), dtype=np.float64)
            augmented[:-1, :-1] = free_system
            augmented[:-1, -1] = 1.0
            augmented[-1, :-1] = 1.0
            constrained_rhs = np.zeros(len(free) + 1, dtype=np.float64)
            constrained_rhs[:-1] = right_hand
            constrained_rhs[-1] = float(total) - float(np.sum(solution[fixed_index]))
            free_solution = np.linalg.solve(augmented, constrained_rhs)
            solution[free_index] = free_solution[:-1]
            lagrange = float(free_solution[-1])
        else:
            difference = float(np.sum(solution)) - float(total)
            if difference > tolerance:
                # Every variable reached a bound, but the active face carries
                # too much charge. Re-open an upper-bound coordinate so the
                # next equality solve can move inward while preserving the
                # remaining active bounds.
                gradient = (system @ solution) + linear_term
                candidates = [
                    index for index, value in active.items() if value == upper
                ]
                if not candidates:
                    raise ValueError("active charge bounds cannot satisfy total charge")
                del active[max(candidates, key=lambda index: float(gradient[index]))]
                continue
            if difference < -tolerance:
                # The active face carries too little charge. Re-open the
                # lower-bound coordinate whose inward move has the smallest
                # first-order objective cost.
                gradient = (system @ solution) + linear_term
                candidates = [
                    index for index, value in active.items() if value == lower
                ]
                if not candidates:
                    raise ValueError("active charge bounds cannot satisfy total charge")
                del active[min(candidates, key=lambda index: float(gradient[index]))]
                continue
            gradient = (system @ solution) + linear_term
            lower_lambda = max(
                (
                    -float(gradient[index])
                    for index, value in active.items()
                    if value == lower
                ),
                default=-math.inf,
            )
            upper_lambda = min(
                (
                    -float(gradient[index])
                    for index, value in active.items()
                    if value == upper
                ),
                default=math.inf,
            )
            if lower_lambda > upper_lambda + tolerance:
                # Release the bound with the largest incompatible stationarity
                # value and let the next equality solve restore feasibility.
                candidate = max(
                    active,
                    key=lambda index: abs(float(gradient[index])),
                )
                del active[candidate]
                continue
            lagrange = min(max(0.0, lower_lambda), upper_lambda)

        violations = [
            (max(lower - solution[index], solution[index] - upper), index)
            for index in free
            if solution[index] < lower - tolerance
            or solution[index] > upper + tolerance
        ]
        if violations:
            _distance, index = max(violations)
            active[index] = lower if solution[index] < lower else upper
            continue

        gradient = (system @ solution) + linear_term
        stationarity = gradient + lagrange
        releases: list[tuple[float, int]] = []
        for index, value in active.items():
            if value == lower and stationarity[index] < -tolerance:
                releases.append((-float(stationarity[index]), index))
            elif value == upper and stationarity[index] > tolerance:
                releases.append((float(stationarity[index]), index))
        if releases:
            _violation, index = max(releases)
            del active[index]
            continue

        residual = np.asarray(stationarity, dtype=np.float64)
        for index, value in active.items():
            residual[index] = (
                min(0.0, float(stationarity[index]))
                if value == lower
                else max(0.0, float(stationarity[index]))
            )
        projected_residual = float(np.linalg.norm(residual))
        return solution.copy(), lagrange, len(active), projected_residual

    raise ValueError("box-constrained semantic charge solve did not converge")


def equilibrate_semantic_charge(
    bundle: AtomicContextBundle,
    *,
    coupling_scale: float = 0.25,
    max_abs_charge: float = 2.0,
    tolerance: float = 1e-9,
) -> SemanticChargeEquilibrium:
    """Solve a convex, constrained graph equilibration for semantic charge.

    ``sum(q_i) == bundle.total_charge`` is enforced by a Lagrange multiplier.
    The graph Laplacian lets local relationships change the equilibrium while
    node hardness prevents unbounded motion. No physical units are implied.
    """

    if not math.isfinite(coupling_scale) or coupling_scale < 0.0:
        raise ValueError("coupling_scale must be finite and non-negative")
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")

    count = len(bundle.nodes)
    index_by_id = {node.node_id: index for index, node in enumerate(bundle.nodes)}
    hardness = np.asarray([node.hardness for node in bundle.nodes], dtype=np.float64)
    initial = np.asarray(
        [node.initial_charge for node in bundle.nodes], dtype=np.float64
    )
    electronegativity = np.asarray(
        [node.atomic_state.element.electronegativity for node in bundle.nodes],
        dtype=np.float64,
    )

    system = np.diag(hardness)
    effective_couplings: list[tuple[int, int, float]] = []
    for edge in bundle.edges:
        left = index_by_id[edge.source_id]
        right = index_by_id[edge.target_id]
        coupling = coupling_scale * edge.coupling / (1.0 + edge.distance)
        effective_couplings.append((left, right, coupling))
        system[left, left] += coupling
        system[right, right] += coupling
        system[left, right] -= coupling
        system[right, left] -= coupling

    augmented = np.zeros((count + 1, count + 1), dtype=np.float64)
    augmented[:count, :count] = system
    augmented[:count, count] = 1.0
    augmented[count, :count] = 1.0
    linear_term = electronegativity - (hardness * initial)
    charges, _lagrange, active_bound_count, projected_residual = _solve_box_equality_qp(
        system,
        linear_term,
        total=bundle.total_charge,
        cap=max_abs_charge,
        tolerance=tolerance,
    )
    if not np.all(np.isfinite(charges)):
        raise ValueError("semantic charge solve produced non-finite values")

    conservation_error = abs(float(np.sum(charges)) - bundle.total_charge)
    energy = float(0.5 * charges @ system @ charges + linear_term @ charges)
    condition_number = float(np.linalg.cond(augmented))
    edge_tension = tuple(
        (
            bundle.nodes[left].node_id,
            bundle.nodes[right].node_id,
            float(coupling * (charges[left] - charges[right])),
        )
        for left, right, coupling in effective_couplings
    )

    return SemanticChargeEquilibrium(
        bundle_hash=bundle.bundle_hash,
        charge_by_node=tuple(
            (node.node_id, float(charges[index]))
            for index, node in enumerate(bundle.nodes)
        ),
        edge_tension=edge_tension,
        total_charge=float(np.sum(charges)),
        conservation_error=conservation_error,
        projected_residual=projected_residual,
        condition_number=condition_number,
        energy=energy,
        active_bound_count=active_bound_count,
        converged=bool(
            conservation_error <= tolerance and projected_residual <= tolerance
        ),
    )


def fuse_atomic_context(
    bundle: AtomicContextBundle,
    equilibrium: SemanticChargeEquilibrium,
    *,
    charge_gain: float = 0.25,
    params: FusionParams | None = None,
) -> FusionResult:
    """Apply a bounded stitch around the frozen chemical-fusion runtime.

    ``charge_gain=0`` is the exact frozen baseline for the same graph. Positive
    or negative gain is an intervention and must be evaluated against that
    baseline and a size-matched control before promotion.
    """

    if equilibrium.bundle_hash != bundle.bundle_hash:
        raise ValueError("equilibrium does not belong to this context bundle")
    if not math.isfinite(charge_gain) or abs(charge_gain) > 1.0:
        raise ValueError("charge_gain must be finite and within [-1, 1]")

    charges = equilibrium.charges
    weights = [
        max(0.05, 1.0 + (charge_gain * charges[node.node_id])) for node in bundle.nodes
    ]
    node_index = {node.node_id: index for index, node in enumerate(bundle.nodes)}
    edges = [
        (node_index[edge.source_id], node_index[edge.target_id])
        for edge in bundle.edges
    ]
    edge_weights = {
        (node_index[edge.source_id], node_index[edge.target_id]): edge.coupling
        for edge in bundle.edges
    }
    return fuse_atomic_states(
        [node.atomic_state for node in bundle.nodes],
        params=params,
        weights=weights,
        edges=edges,
        edge_weights=edge_weights,
    )


def compute_drift_clock(
    bundle: AtomicContextBundle,
    equilibrium: SemanticChargeEquilibrium,
    *,
    congestion: float = 0.0,
    route_cost: float = 0.0,
    drift_gain: float = 1.0,
    congestion_gain: float = 1.0,
    route_gain: float = 1.0,
    phase_frequency: float = 1.0 / 6.0,
) -> ComputationalDriftClock:
    """Convert token/route pressure into dimensionless scheduler telemetry."""

    if equilibrium.bundle_hash != bundle.bundle_hash:
        raise ValueError("equilibrium does not belong to this context bundle")
    scalars = (
        congestion,
        route_cost,
        drift_gain,
        congestion_gain,
        route_gain,
        phase_frequency,
    )
    if not all(math.isfinite(float(value)) for value in scalars):
        raise ValueError("drift clock inputs must be finite")
    if (
        congestion < 0.0
        or route_cost < 0.0
        or min(drift_gain, congestion_gain, route_gain) < 0.0
    ):
        raise ValueError("pressure inputs and gains must be non-negative")

    charges = equilibrium.charges
    mean_motion = sum(
        abs(charges[node.node_id] - node.initial_charge) for node in bundle.nodes
    ) / len(bundle.nodes)
    pressure = (
        drift_gain * mean_motion
        + congestion_gain * float(congestion)
        + route_gain * float(route_cost)
    )
    increment = 1.0 / (1.0 + pressure)
    phase = (2.0 * math.pi * phase_frequency * bundle.step_clock) % (2.0 * math.pi)
    return ComputationalDriftClock(
        bundle_hash=bundle.bundle_hash,
        equilibrium_hash=equilibrium.result_hash,
        step_clock=bundle.step_clock,
        context_epoch=bundle.context_epoch,
        mean_charge_motion=float(mean_motion),
        congestion=float(congestion),
        route_cost=float(route_cost),
        pressure=float(pressure),
        model_time_increment=float(increment),
        wrapped_phase_radians=float(phase),
    )
