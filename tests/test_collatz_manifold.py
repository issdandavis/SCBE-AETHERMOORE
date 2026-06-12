"""Tests for collatz_manifold — the null-tested Collatz routing topology.

Locks the four real findings: live drain verification (in range only), the spike
hazard (manifold amplifies, never damps), the exact log(n) energy ledger that funds
the odd chambers, table-free parity routing, and the Euclidean-crowding /
hyperbolic-fit geometry numbers.
"""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "research"))

import collatz_manifold as cm  # noqa: E402


def test_drain_verified_in_range():
    a = cm.audit_range(20_000)
    assert a["all_drain"] and a["range_verified"] == 20_000


def test_famous_spike_27_reaches_9232():
    assert max(cm.trajectory(27)) == 9232  # amplification x342 — manufactured, not damped


def test_energy_ledger_closes_at_exactly_log_n():
    # releases - odd-chamber costs = log n: the arithmetic identity that funds the
    # shuttles. Exact in the reals; float residual must be tiny.
    for n in (7, 27, 97, 703, 12345):
        e = cm.energy_ledger(n)
        assert e["ledger_residual"] < 1e-9, e
        assert abs(e["net"] - math.log(n)) < 1e-4


def test_inverse_children_invert_the_forward_map():
    for m in (1, 4, 5, 16, 22, 40):
        for c in cm.inverse_children(m):
            assert cm.step(c) == m  # the O(1) parity rule recovers the parent


def test_routing_is_table_free_across_the_tree():
    ro = cm.routing_table_cost(20)
    assert ro["local_rule_recovers_parent_everywhere"]
    assert ro["tree_nodes"] > 100


def test_tree_crowds_euclid_but_fits_hyperbolic():
    g = cm.embedding_capacity(35)
    assert g["euclid_crowds_at_depth"] is not None and g["euclid_crowds_at_depth"] <= 30
    assert g["hyperbolic_holds_all_depths"]
    assert 1.1 < g["ring_growth_rate"] < 1.5  # geometric growth — the crowding cause
