"""Tarski sheaf utilities for SCBE/HYDRA temporal consensus.

Implements a finite lattice-valued sheaf formalism over triadic/tetradic temporal nodes,
with fixed-point computation for global intent consistency and fail-to-noise projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

LatticeValue = int
Restriction = Callable[[LatticeValue], LatticeValue]


@dataclass(frozen=True)
class TemporalSheaf:
    """Finite lattice-valued sheaf on a temporal graph.

    lattice_values: totally ordered finite chain, e.g. (0, 1) or (0, 1, 2)
    nodes: temporal sites (Ti, Tm, Tg, Tp)
    edges: directed edges used for local propagation constraints
    restrictions: edge maps r_{u->v}: F(u) -> F(v), monotone maps
    """

    lattice_values: Tuple[LatticeValue, ...]
    nodes: Tuple[str, ...]
    edges: Tuple[Tuple[str, str], ...]
    restrictions: Mapping[Tuple[str, str], Restriction]

    def bottom(self) -> LatticeValue:
        return self.lattice_values[0]

    def top(self) -> LatticeValue:
        return self.lattice_values[-1]


def identity_restriction(value: LatticeValue) -> LatticeValue:
    return value


def complement_boolean_restriction(value: LatticeValue) -> LatticeValue:
    if value not in (0, 1):
        raise ValueError("Complement restriction is only defined for Boolean lattice {0,1}")
    return 1 - value


def make_complete_temporal_edges(nodes: Sequence[str]) -> Tuple[Tuple[str, str], ...]:
    return tuple((u, v) for u in nodes for v in nodes if u != v)


def make_temporal_sheaf(
    nodes: Sequence[str],
    lattice_values: Sequence[LatticeValue] = (0, 1),
    twisted_edges: Mapping[Tuple[str, str], Restriction] | None = None,
) -> TemporalSheaf:
    edges = make_complete_temporal_edges(nodes)
    restrictions: Dict[Tuple[str, str], Restriction] = {edge: identity_restriction for edge in edges}
    if twisted_edges:
        for edge, fn in twisted_edges.items():
            if edge not in restrictions:
                raise ValueError(f"Twisted edge {edge} not in temporal graph")
            restrictions[edge] = fn

    return TemporalSheaf(
        lattice_values=tuple(sorted(lattice_values)),
        nodes=tuple(nodes),
        edges=edges,
        restrictions=restrictions,
    )


def _meet(values: Iterable[LatticeValue]) -> LatticeValue:
    return min(values)


def local_consensus_value(sheaf: TemporalSheaf, assignment: Mapping[str, LatticeValue], node: str) -> LatticeValue:
    incoming = [
        sheaf.restrictions[(neighbor, node)](assignment[neighbor])
        for neighbor in sheaf.nodes
        if neighbor != node
    ]
    if not incoming:
        return assignment[node]
    return _meet(incoming)


def tarski_operator(sheaf: TemporalSheaf, assignment: Mapping[str, LatticeValue]) -> Dict[str, LatticeValue]:
    return {
        node: min(assignment[node], local_consensus_value(sheaf, assignment, node))
        for node in sheaf.nodes
    }


def iterate_to_fixed_point(
    sheaf: TemporalSheaf,
    assignment: Mapping[str, LatticeValue],
    max_steps: int = 64,
) -> Dict[str, LatticeValue]:
    current = dict(assignment)
    for _ in range(max_steps):
        nxt = tarski_operator(sheaf, current)
        if nxt == current:
            return nxt
        current = nxt
    raise RuntimeError("Tarski operator did not converge within max_steps")


def is_global_intent_consistent(sheaf: TemporalSheaf, assignment: Mapping[str, LatticeValue]) -> bool:
    return tarski_operator(sheaf, assignment) == dict(assignment)


def enumerate_global_sections(sheaf: TemporalSheaf) -> List[Dict[str, LatticeValue]]:
    sections: List[Dict[str, LatticeValue]] = []

    def rec(idx: int, partial: Dict[str, LatticeValue]) -> None:
        if idx == len(sheaf.nodes):
            if is_global_intent_consistent(sheaf, partial):
                sections.append(dict(partial))
            return
        node = sheaf.nodes[idx]
        for value in sheaf.lattice_values:
            partial[node] = value
            rec(idx + 1, partial)

    rec(0, {})
    return sections


def obstruction_count(sheaf: TemporalSheaf, assignment: Mapping[str, LatticeValue]) -> int:
    """Count local violations where node value exceeds local propagated meet."""
    violations = 0
    for node in sheaf.nodes:
        if assignment[node] > local_consensus_value(sheaf, assignment, node):
            violations += 1
    return violations


def fail_to_noise_projection(sheaf: TemporalSheaf, assignment: Mapping[str, LatticeValue]) -> Dict[str, LatticeValue]:
    """Project any local intent pattern to nearest descending fixed point.

    In adversarial paths this converges to low lattice values (noise) unless
    assignment is globally consistent.
    """
    return iterate_to_fixed_point(sheaf, assignment)
