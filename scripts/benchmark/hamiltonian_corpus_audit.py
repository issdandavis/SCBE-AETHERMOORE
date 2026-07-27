#!/usr/bin/env python3
"""Measure the real-world impact of the TLCFI directed-Hamiltonicity defect.

    PYTHONPATH=. python scripts/benchmark/hamiltonian_corpus_audit.py

The original test applied Dirac's criterion — an UNDIRECTED theorem — to a
directed control-flow graph, and compared the SUM of in-degree and out-degree to
the n/2 threshold. The directed condition (Ghouila-Houri) constrains the two
degrees separately.

This script does not re-assert that the bug exists; the regression tests do
that. It answers the question that actually matters: **on CFG-shaped graphs, how
often did the old test return the wrong answer, and in which direction?**

The failure direction is what makes it serious. ``lift_to_hamiltonian`` runs only
when a graph is found non-Hamiltonian, so a false positive skips the lift and
leaves runtime deviation with no principal curve to measure against. False
positives make the detector fail OPEN.

Graphs are generated to resemble real control flow: a single entry block,
conditional branches, loop back-edges, and — critically — multiple ``return``
sites, which produce multiple sinks. Ground truth is exhaustive search, so the
vertex count is kept small enough for that to be exact.
"""

from __future__ import annotations

import random
import sys
from itertools import permutations
from pathlib import Path
from typing import Dict, List, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from symphonic_cipher.topological_cfi import (  # noqa: E402
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
    HamiltonianTester,
)

SEED = 20260727
MAX_VERTICES = 9  # exhaustive ground truth is 9! = 362,880 permutations


def old_dirac_verdict(n: int, edges: List[Tuple[int, int]]) -> bool:
    """Reproduce the ORIGINAL test exactly: summed in+out degree vs n/2."""
    if n < 3:
        return True
    total: Dict[int, int] = {v: 0 for v in range(n)}
    for source, target in set(edges):
        total[source] += 1
        total[target] += 1
    return all(total[v] >= n / 2 for v in range(n))


def ground_truth(n: int, edges: List[Tuple[int, int]]) -> bool:
    """Exhaustive Hamiltonian-path search."""
    adjacency: Dict[int, Set[int]] = {i: set() for i in range(n)}
    for source, target in edges:
        adjacency[source].add(target)
    return any(all(perm[i + 1] in adjacency[perm[i]] for i in range(n - 1)) for perm in permutations(range(n)))


def new_verdict(n: int, edges: List[Tuple[int, int]]) -> Tuple[bool, str]:
    cfg = ControlFlowGraph()
    for i in range(n):
        cfg.add_vertex(BasicBlock(id=i, instructions=[f"b{i}"], entry_point=i, exit_point=i))
    for source, target in edges:
        cfg.add_edge(CFGEdge(source=source, target=target, edge_type="jump"))
    return HamiltonianTester(cfg).is_hamiltonian()


def make_cfg(rng: random.Random) -> Tuple[int, List[Tuple[int, int]]]:
    """Generate a graph shaped like real control flow."""
    n = rng.randint(4, MAX_VERTICES)
    edges: List[Tuple[int, int]] = []

    # Spine: entry block falls through toward the exits.
    for i in range(n - 1):
        edges.append((i, i + 1))

    # Conditional branches: skip forward over a block.
    for i in range(n - 2):
        if rng.random() < 0.35:
            target = rng.randint(i + 2, n - 1)
            edges.append((i, target))

    # Loop back-edges.
    for _ in range(rng.randint(0, 2)):
        source = rng.randint(1, n - 1)
        target = rng.randint(0, source - 1)
        edges.append((source, target))

    # Multiple return sites -> multiple sinks. This is the realistic case that
    # the old test mishandled: any function with two `return` statements.
    if rng.random() < 0.5:
        extra_exit = rng.randint(1, n - 2)
        edges = [(a, b) for a, b in edges if a != extra_exit]
        for src in range(n):
            if src != extra_exit and rng.random() < 0.4:
                edges.append((src, extra_exit))

    return n, sorted(set(edges))


def main() -> int:
    rng = random.Random(SEED)
    stats = {
        "total": 0,
        "old_correct": 0,
        "new_correct": 0,
        "old_false_pos": 0,  # claimed Hamiltonian, is not -> SKIPS THE LIFT
        "old_false_neg": 0,  # claimed not, actually is -> wasteful but safe
        "new_false_pos": 0,
        "new_false_neg": 0,
        "multi_sink": 0,
    }
    reasons: Dict[str, int] = {}

    for _ in range(2000):
        n, edges = make_cfg(rng)
        truth = ground_truth(n, edges)
        old = old_dirac_verdict(n, edges)
        new, reason = new_verdict(n, edges)

        stats["total"] += 1
        reasons[reason] = reasons.get(reason, 0) + 1

        outdeg = {v: 0 for v in range(n)}
        for a, _b in edges:
            outdeg[a] += 1
        if sum(1 for v in outdeg if outdeg[v] == 0) > 1:
            stats["multi_sink"] += 1

        if old == truth:
            stats["old_correct"] += 1
        elif old and not truth:
            stats["old_false_pos"] += 1
        else:
            stats["old_false_neg"] += 1

        if new == truth:
            stats["new_correct"] += 1
        elif new and not truth:
            stats["new_false_pos"] += 1
        else:
            stats["new_false_neg"] += 1

    t = stats["total"]
    print("=" * 70)
    print(f"HAMILTONICITY CORPUS AUDIT   n={t} CFG-shaped digraphs, seed {SEED}")
    print("=" * 70)
    print(
        f"  graphs with >1 sink (multi-return functions): {stats['multi_sink']:5d}  "
        f"({100*stats['multi_sink']/t:.1f}%)\n"
    )
    print(f"  {'':22} {'correct':>9} {'FALSE POS':>11} {'false neg':>10}")
    print(
        f"  {'OLD (summed Dirac)':22} {stats['old_correct']:8d}  {stats['old_false_pos']:10d} "
        f"{stats['old_false_neg']:10d}"
    )
    print(
        f"  {'NEW (directed)':22} {stats['new_correct']:8d}  {stats['new_false_pos']:10d} "
        f"{stats['new_false_neg']:10d}"
    )
    print()
    print(f"  OLD accuracy {100*stats['old_correct']/t:5.1f}%     " f"NEW accuracy {100*stats['new_correct']/t:5.1f}%")
    print()
    print("  FALSE POSITIVES are the dangerous class: the lift is skipped, no")
    print("  principal curve exists, and deviation has no baseline -> fails OPEN.")
    print(
        f"    old: {stats['old_false_pos']:4d} ({100*stats['old_false_pos']/t:.1f}%)   "
        f"new: {stats['new_false_pos']:4d} ({100*stats['new_false_pos']/t:.1f}%)"
    )
    print()
    print("  NEW verdict reasons:")
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"    {reason:34} {count:5d}  ({100*count/t:.1f}%)")

    ok = stats["new_false_pos"] == 0
    print()
    print(
        "  RESULT:",
        "no false positives in the new test" if ok else f"*** {stats['new_false_pos']} FALSE POSITIVES REMAIN ***",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
