#!/usr/bin/env python3
"""Regression tests for directed Hamiltonicity in TLCFI.

The original implementation applied Dirac's criterion and Ore's theorem — both
theorems about simple UNDIRECTED graphs — to a control-flow graph, which is
directed by construction (jumps, calls, returns, fallthroughs are one-way). It
also summed in-degree and out-degree before comparing to the n/2 threshold,
where the correct directed condition (Ghouila-Houri) constrains the two degrees
SEPARATELY.

The consequence was a false positive that failed OPEN: ``lift_to_hamiltonian``
runs only when a graph is found non-Hamiltonian, so a graph wrongly declared
Hamiltonian skipped the lift, produced no principal curve, and left runtime
deviation with no baseline to measure against.

The canonical failing case is two sinks: a Hamiltonian path has exactly one
final vertex, so two vertices with out-degree 0 make one impossible — and it is
not exotic, it is any function with two ``return`` statements.
"""

import sys
from itertools import permutations
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from symphonic_cipher.topological_cfi import (  # noqa: E402
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
    HamiltonianTester,
)


def build(n: int, edges) -> ControlFlowGraph:
    """Build a CFG with ``n`` vertices and the given directed edges."""
    cfg = ControlFlowGraph()
    for i in range(n):
        cfg.add_vertex(BasicBlock(id=i, instructions=[f"block_{i}"], entry_point=i, exit_point=i))
    for source, target in edges:
        cfg.add_edge(CFGEdge(source=source, target=target, edge_type="jump"))
    return cfg


def brute_force_has_path(n: int, edges) -> bool:
    """Ground truth by exhaustive search. Only for tiny graphs."""
    adjacency = {i: set() for i in range(n)}
    for source, target in edges:
        adjacency[source].add(target)
    return any(all(perm[i + 1] in adjacency[perm[i]] for i in range(n - 1)) for perm in permutations(range(n)))


class TestCFGEdgeConstruction:
    """CFGEdge lacked @dataclass, so no edge could be constructed at all."""

    def test_edge_accepts_arguments(self):
        edge = CFGEdge(source=0, target=1, edge_type="jump")
        assert edge.source == 0
        assert edge.target == 1
        assert edge.edge_type == "jump"

    def test_edge_is_hashable(self):
        assert len({CFGEdge(0, 1, "jump"), CFGEdge(0, 1, "fallthrough")}) == 1


class TestDirectedHamiltonicity:
    def test_two_sinks_is_rejected(self):
        """THE regression case. Old code returned (True, 'dirac'); truth is False."""
        edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3)]
        cfg = build(4, edges)

        # Every vertex clears the old summed-degree threshold of n/2 = 2.0,
        # which is exactly why the old test passed it.
        assert all(cfg.get_degree(v) >= 2.0 for v in cfg.vertices)

        assert brute_force_has_path(4, edges) is False
        is_ham, reason = HamiltonianTester(cfg).is_hamiltonian()
        assert is_ham is False
        assert reason.startswith("necessary:multiple_sinks")

    def test_single_sink_is_accepted(self):
        """A lone sink is fine — it is simply the last vertex of the path."""
        edges = [(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)]
        assert brute_force_has_path(4, edges) is True
        is_ham, _ = HamiltonianTester(build(4, edges)).is_hamiltonian()
        assert is_ham is True

    def test_two_sources_is_rejected(self):
        """Mirror case: a path has exactly one starting vertex."""
        edges = [(0, 2), (1, 2), (2, 3)]
        assert brute_force_has_path(4, edges) is False
        is_ham, reason = HamiltonianTester(build(4, edges)).is_hamiltonian()
        assert is_ham is False
        assert reason.startswith("necessary:multiple_sources")

    def test_disconnected_is_rejected(self):
        edges = [(0, 1), (2, 3)]
        assert brute_force_has_path(4, edges) is False
        is_ham, reason = HamiltonianTester(build(4, edges)).is_hamiltonian()
        assert is_ham is False
        assert "disconnected" in reason or "sink" in reason or "source" in reason

    def test_simple_chain_is_hamiltonian(self):
        edges = [(0, 1), (1, 2), (2, 3)]
        assert brute_force_has_path(4, edges) is True
        is_ham, _ = HamiltonianTester(build(4, edges)).is_hamiltonian()
        assert is_ham is True

    def test_complete_digraph_accepted_by_ghouila_houri(self):
        n = 5
        edges = [(i, j) for i in range(n) for j in range(n) if i != j]
        is_ham, reason = HamiltonianTester(build(n, edges)).is_hamiltonian()
        assert is_ham is True
        assert reason == "ghouila_houri"

    def test_directed_cycle_is_hamiltonian(self):
        n = 6
        edges = [(i, (i + 1) % n) for i in range(n)]
        assert brute_force_has_path(n, edges) is True
        is_ham, _ = HamiltonianTester(build(n, edges)).is_hamiltonian()
        assert is_ham is True

    def test_edge_direction_decides_it(self):
        """A ring with radial branches: one edge direction flips the answer.

        Branches feeding the NEXT ring node admit a Hamiltonian path; branches
        returning to their OWN ring node create 2-cycles and do not.
        """
        works = []
        fails = []
        for i in range(4):
            works += [(i, 4 + i), (4 + i, (i + 1) % 4)]
            fails += [(i, 4 + i), (4 + i, i)]
        fails += [(i, (i + 1) % 4) for i in range(4)]

        assert HamiltonianTester(build(8, works)).is_hamiltonian()[0] is True
        assert HamiltonianTester(build(8, fails)).is_hamiltonian()[0] is False


class TestExactAgreesWithBruteForce:
    @pytest.mark.parametrize(
        "n,edges",
        [
            (4, [(0, 1), (1, 2), (2, 3)]),
            (4, [(0, 1), (0, 2), (1, 3), (2, 3)]),
            (4, [(0, 1), (1, 0), (2, 3), (3, 2), (1, 2)]),
            (5, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]),
            (5, [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)]),
            (5, [(0, 1), (1, 2), (0, 3), (3, 4)]),
        ],
    )
    def test_matches_ground_truth(self, n, edges):
        expected = brute_force_has_path(n, edges)
        actual, _ = HamiltonianTester(build(n, edges)).is_hamiltonian()
        assert actual == expected, f"n={n} edges={edges} reason mismatch"


class TestFailsClosed:
    def test_unknown_reports_non_hamiltonian(self):
        """Undecided must route to the lift, never skip it."""
        tester = HamiltonianTester(build(3, [(0, 1), (1, 2), (2, 0)]))
        assert isinstance(tester.is_hamiltonian(), tuple)
        # Anything not provably Hamiltonian must return False so the caller lifts.
        big = build(2, [(0, 1)])
        assert HamiltonianTester(big).is_hamiltonian()[0] is True  # trivial, n < 3
