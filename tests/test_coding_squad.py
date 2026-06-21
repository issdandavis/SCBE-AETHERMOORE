"""Tests for coding_squad -- the clone-trooper/Polly-Pad role squad over the coding board (option C).

Proves: roles carry goals + role-scoped gate sub-alphabets; geometric buddy-pairs cover the whole roster
(hyperbolic proximity); the squad solves the board to the energy-0 ground state and records the
coordination (pairs, region coverage, RECON's targets); deterministic.
"""

from __future__ import annotations

import numpy as np

from python.scbe.coding_board import Board, Operator, region_must_agree
from python.scbe.coding_board_gates import CHECK, TRANSFORM, gate_names
from python.scbe.coding_squad import (
    SQUAD,
    Role,
    cover_regions,
    demo,
    geometric_pairs,
    robust_triangulate,
    squad_basis,
    squad_coverage,
    solve_with_squad,
    triangulate,
)


# ---- roles carry goals + role-scoped sub-alphabets (the Polly-Pad loadout) ---------------------
def test_roles_have_goals_and_scoped_alphabets():
    by_name = {r.name: r for r in SQUAD}
    assert set(["ARCHITECT", "RECON", "CODER", "CHECK", "OPTIMIZER"]).issubset(by_name)
    assert all(r.goal for r in SQUAD)
    assert by_name["CODER"].gate_role == TRANSFORM
    assert by_name["CHECK"].gate_role == CHECK
    assert set(by_name["CODER"].legal_operations()) == set(gate_names(TRANSFORM))
    assert by_name["ARCHITECT"].legal_operations() == ()  # a non-coding (coordination) role


# ---- geometric buddy-pairs cover the whole roster ---------------------------------------------
def test_geometric_pairs_cover_every_role():
    pairs = geometric_pairs(SQUAD)
    named = set()
    for a, b, dist in pairs:
        named.add(a)
        if b is not None:
            named.add(b)
        assert dist >= 0.0  # a real hyperbolic distance
    assert named == {r.name for r in SQUAD}  # everyone is on a team (or solos)


# ---- the squad solves the board + records the coordination ------------------------------------
def test_squad_solves_board_and_records_coverage():
    ops = [Operator("o0", gate_names(TRANSFORM), region="r"), Operator("o1", gate_names(TRANSFORM), region="r")]
    board = Board(ops, [region_must_agree])
    res = solve_with_squad(board)
    assert res.solved and res.energy == 0
    assert res.assignment["o0"] == res.assignment["o1"]  # interface matches
    assert set(res.targets) == {"o0", "o1"}  # RECON found the unknowns
    assert "r" in res.coverage  # the region is covered by a buddy team
    assert res.roster["CODER"].endswith("ops")  # the loadout sizes are recorded


def test_recon_targets_exclude_knowns():
    ops = [
        Operator("o0", gate_names(TRANSFORM), region="r", fixed="id"),
        Operator("o1", gate_names(TRANSFORM), region="r"),
    ]
    res = solve_with_squad(Board(ops, []))
    assert res.targets == ["o1"]  # the fixed (known) operator is not a target


def test_cover_regions_with_no_regions_is_one_zone():
    ops = [Operator("o0", gate_names(TRANSFORM)), Operator("o1", gate_names(TRANSFORM))]
    cov = cover_regions(Board(ops, []), geometric_pairs(SQUAD))
    assert list(cov.keys()) == ["<whole-board>"]


def test_squad_is_deterministic():
    ops = [Operator("o0", gate_names(TRANSFORM), region="r"), Operator("o1", gate_names(TRANSFORM), region="r")]
    board = Board(ops, [region_must_agree])
    a = solve_with_squad(board)
    b = solve_with_squad(board)
    assert a.pairs == b.pairs and a.coverage == b.coverage and a.assignment == b.assignment


# ---- multidimensional triangulation: differentiation is load-bearing, measured -------------------
def _axis_roles(n, dim):
    # n roles whose profiles are the first n coordinate axes of `dim`-space -> a maximally diverse squad
    out = []
    for i in range(n):
        p = [0.0] * dim
        p[i] = 1.0
        out.append(Role("R%d" % i, "axis %d" % i, None, tuple(p)))
    return out


def test_clone_squad_is_rank_deficient_and_blind():
    # the Bad-Batch claim: a squad of identical clones cannot triangulate. Five copies of one role span a
    # single line -> rank 1, blind in the other dims. Differentiation is what buys resolving power.
    clones = [SQUAD[0]] * 5
    cov = squad_coverage(clones)
    assert cov.rank == 1
    assert not cov.full_rank
    assert len(cov.blind_directions) == cov.dim - 1  # blind everywhere but the clone's one direction


def test_differentiated_squad_spans_more_and_full_rank_when_dim_matched():
    # a diverse squad resolves one dimension per independent member; matching member count to dim -> full rank
    roles = _axis_roles(4, 4)
    cov = squad_coverage(roles)
    assert cov.rank == 4 and cov.full_rank and cov.blind_directions == ()
    assert cov.dilution == 1.0  # orthonormal axes -> perfectly conditioned (dilution 1)


def test_target_in_span_is_recovered_blind_component_is_lost():
    # localize a target the squad CAN see (in its span) -> exact; a target along a BLIND direction -> the
    # squad reads all zeros and recovers nothing (the coverage gap is real, not hand-waved).
    roles = _axis_roles(3, 4)  # sees dims 0,1,2 ; dim 3 is blind
    B = squad_basis(roles)
    seen_target = np.array([2.0, -1.0, 0.5, 0.0])  # lies in the span (no dim-3 component)
    tri = triangulate(roles, (B @ seen_target).tolist())
    assert tri.reading_residual < 1e-9
    assert np.allclose(np.array(tri.target_estimate)[:3], seen_target[:3], atol=1e-9)

    blind_target = np.array([0.0, 0.0, 0.0, 9.0])  # entirely in the blind dim 3
    tri_blind = triangulate(roles, (B @ blind_target).tolist())
    assert np.allclose(B @ blind_target, 0.0)  # the squad literally reads nothing
    assert np.linalg.norm(tri_blind.target_estimate) < 1e-9  # ...so it recovers nothing -- the gap


def test_near_collinear_full_rank_squad_has_high_dilution():
    # differentiation is a matter of degree: two nearly-parallel members are technically independent (full
    # rank) but poorly conditioned -> a large dilution of precision (a sloppy fix), unlike orthogonal axes.
    eps = 1e-3
    roles = [
        Role("A", "", None, (1.0, 0.0)),
        Role("B", "", None, (1.0, eps)),  # almost the same direction as A
    ]
    cov = squad_coverage(roles)
    assert cov.full_rank  # technically independent
    assert cov.dilution > 100.0  # ...but weak differentiation -> high dilution (poor triangulation geometry)


# a 5-member squad in 3-D: rank 3 with a TWO-member margin (n = rank + 2), so dropping the traitor still
# leaves an overdetermined (residual-meaningful) fit -- the redundancy needed to IDENTIFY a bad bearing.
def _redundant_squad():
    return _axis_roles(3, 3) + [
        Role("D1", "diag", None, (1.0, 1.0, 1.0)),
        Role("D2", "diag2", None, (1.0, 2.0, 3.0)),
    ]


def test_robust_triangulate_survives_one_traitor():
    # a differentiated squad with redundancy localizes even when one member reports a corrupted bearing:
    # the least-trimmed fuse drops the worst member and recovers the target; plain lstsq is pulled off.
    roles = _redundant_squad()
    B = squad_basis(roles)
    target = np.array([1.0, 2.0, 3.0])
    readings = (B @ target).tolist()
    readings[1] += 50.0  # member R1 is a traitor (corrupted reading)

    plain = triangulate(roles, readings)
    robust, dropped = robust_triangulate(roles, readings)
    assert dropped == "R1"  # identified the traitor by leave-one-out residual
    assert np.linalg.norm(np.array(robust.target_estimate) - target) < 1e-9  # recovered the true target
    assert np.linalg.norm(np.array(plain.target_estimate) - target) > 1.0  # the naive fuse was pulled off


def test_robust_triangulate_no_traitor_keeps_everyone():
    # with clean readings there is no traitor to drop -> robust returns the full-squad fit, drops nobody
    roles = _redundant_squad()
    B = squad_basis(roles)
    target = np.array([1.0, 2.0, 3.0])
    robust, dropped = robust_triangulate(roles, (B @ target).tolist())
    assert dropped is None
    assert np.linalg.norm(np.array(robust.target_estimate) - target) < 1e-9


def test_robust_triangulate_needs_a_two_member_margin_to_identify():
    # honesty bound: with only rank+1 members, dropping any one leaves an EXACT fit (residual 0) so the
    # traitor cannot be told apart -> robust declines to drop (returns the full, traitor-tainted fit).
    roles = _axis_roles(3, 3) + [Role("D", "diag", None, (1.0, 1.0, 1.0))]  # n = rank + 1 only
    B = squad_basis(roles)
    readings = (B @ np.array([1.0, 2.0, 3.0])).tolist()
    readings[1] += 50.0
    _robust, dropped = robust_triangulate(roles, readings)
    assert dropped is None  # cannot isolate a bad bearing without the 2-member margin


def test_triangulation_demo_all_true():
    d = demo()
    assert all(v for k, v in d.items() if not k.startswith("_"))
